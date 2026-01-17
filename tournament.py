"""
T-League Bot - Логика турниров (ИСПРАВЛЕННАЯ ВЕРСИЯ v1.1.2)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from database.models import (
    Tournament, TournamentParticipant, Match, User, 
    TournamentStatus, TournamentFormat, MatchStatus,
    TournamentRecord
)
from datetime import datetime
from typing import List, Optional
import random

class TournamentService:
    """Сервис управления турнирами"""
    
    @staticmethod
    async def create_tournament(
        session: AsyncSession,
        name: str,
        description: str,
        format: TournamentFormat,
        max_participants: Optional[int] = None
    ) -> Tournament:
        """Создание нового турнира (регистрация закрыта по умолчанию)"""
        tournament = Tournament(
            name=name,
            description=description,
            format=format,
            max_participants=max_participants,
            status=TournamentStatus.REGISTRATION,
            registration_open=False
        )
        session.add(tournament)
        await session.commit()
        await session.refresh(tournament)
        return tournament
    
    @staticmethod
    async def toggle_registration(session: AsyncSession, tournament_id: int) -> bool:
        """Переключение статуса регистрации"""
        result = await session.execute(
            select(Tournament).where(Tournament.id == tournament_id)
        )
        tournament = result.scalar_one_or_none()
        
        if not tournament or tournament.status != TournamentStatus.REGISTRATION:
            return False
        
        tournament.registration_open = not tournament.registration_open
        await session.commit()
        return True
    
    @staticmethod
    async def conduct_draw_with_meetings(
        session: AsyncSession,
        tournament_id: int,
        meetings_count: int = 1
    ) -> bool:
        """
        Жеребьёвка с указанием количества встреч
        meetings_count: 1 или 2 (сколько раз играют друг с другом)
        """
        result = await session.execute(
            select(Tournament).where(Tournament.id == tournament_id)
        )
        tournament = result.scalar_one_or_none()
        
        if not tournament or tournament.status != TournamentStatus.REGISTRATION:
            return False
        
        participants_result = await session.execute(
            select(TournamentParticipant)
            .where(TournamentParticipant.tournament_id == tournament_id)
        )
        participants = participants_result.scalars().all()
        
        if len(participants) < 2:
            return False
        
        if tournament.format == TournamentFormat.ROUND_ROBIN:
            await TournamentService._generate_round_robin_meetings(
                session, tournament, participants, meetings_count
            )
        elif tournament.format == TournamentFormat.GROUP_PLAYOFF:
            await TournamentService._generate_round_robin_meetings(
                session, tournament, participants, meetings_count
            )
        elif tournament.format == TournamentFormat.PLAYOFF:
            await TournamentService._generate_playoff_bracket(
                session, tournament, participants
            )
        
        tournament.draw_completed = True
        await session.commit()
        return True
    
    @staticmethod
    async def conduct_draw(session: AsyncSession, tournament_id: int) -> bool:
        """Жеребьёвка с одной встречей (по умолчанию)"""
        return await TournamentService.conduct_draw_with_meetings(
            session, tournament_id, meetings_count=1
        )
    
    @staticmethod
    async def _generate_round_robin_meetings(
        session: AsyncSession,
        tournament: Tournament,
        participants: List[TournamentParticipant],
        meetings_count: int
    ):
        """Генерация матчей с учётом количества встреч"""
        player_ids = [p.user_id for p in participants]
        n = len(player_ids)
        
        if n % 2 == 1:
            player_ids.append(None)
            n += 1
        
        round_num = 0
        for meeting in range(meetings_count):
            for r in range(n - 1):
                round_num += 1
                matches_per_round = n // 2
                
                for match_num in range(matches_per_round):
                    home_idx = match_num
                    away_idx = n - 1 - match_num
                    
                    home_id = player_ids[home_idx]
                    away_id = player_ids[away_idx]
                    
                    if home_id is None or away_id is None:
                        continue
                    
                    match = Match(
                        tournament_id=tournament.id,
                        round_number=round_num,
                        player1_id=home_id,
                        player2_id=away_id,
                        status=MatchStatus.SCHEDULED,
                        deadline_set=False
                    )
                    session.add(match)
                
                player_ids = [player_ids[0]] + [player_ids[-1]] + player_ids[1:-1]
        
        tournament.total_rounds = round_num
        await session.commit()
    
    @staticmethod
    async def _generate_playoff_bracket(
        session: AsyncSession,
        tournament: Tournament,
        participants: List[TournamentParticipant]
    ):
        """Генерация сетки плей-офф"""
        import math
        n = len(participants)
        
        # Ближайшая степень двойки
        bracket_size = 2 ** math.ceil(math.log2(n))
        
        # Перемешиваем участников
        player_ids = [p.user_id for p in participants]
        random.shuffle(player_ids)
        
        # Добавляем "bye" (пустые слоты)
        while len(player_ids) < bracket_size:
            player_ids.append(None)
        
        # Генерация первого раунда
        round_num = 1
        pairs = []
        
        for i in range(0, len(player_ids), 2):
            p1 = player_ids[i]
            p2 = player_ids[i + 1] if i + 1 < len(player_ids) else None
            
            if p1 and p2:
                match = Match(
                    tournament_id=tournament.id,
                    round_number=round_num,
                    player1_id=p1,
                    player2_id=p2,
                    status=MatchStatus.SCHEDULED,
                    deadline_set=False
                )
                session.add(match)
        
        # Расчёт общего количества раундов
        total_rounds = int(math.log2(bracket_size))
        tournament.total_rounds = total_rounds
        await session.commit()
    
    @staticmethod
    async def get_tournament(session: AsyncSession, tournament_id: int) -> Optional[Tournament]:
        """Получение турнира по ID"""
        result = await session.execute(
            select(Tournament).where(Tournament.id == tournament_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_tournaments(session: AsyncSession) -> List[Tournament]:
        """Получение всех турниров"""
        result = await session.execute(
            select(Tournament).order_by(Tournament.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_active_tournaments(session: AsyncSession) -> List[Tournament]:
        """Получение активных турниров"""
        result = await session.execute(
            select(Tournament)
            .where(Tournament.status.in_([TournamentStatus.REGISTRATION, TournamentStatus.ACTIVE]))
            .order_by(Tournament.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def register_participant(
        session: AsyncSession,
        tournament_id: int,
        user_id: int
    ) -> bool:
        """Регистрация участника на турнир"""
        tournament = await TournamentService.get_tournament(session, tournament_id)
        if not tournament or tournament.status != TournamentStatus.REGISTRATION or not tournament.registration_open:
            return False
        
        if tournament.max_participants:
            result = await session.execute(
                select(TournamentParticipant)
                .where(TournamentParticipant.tournament_id == tournament_id)
            )
            count = len(result.scalars().all())
            if count >= tournament.max_participants:
                return False
        
        result = await session.execute(
            select(TournamentParticipant).where(
                TournamentParticipant.tournament_id == tournament_id,
                TournamentParticipant.user_id == user_id
            )
        )
        if result.scalar_one_or_none():
            return False
        
        participant = TournamentParticipant(
            tournament_id=tournament_id,
            user_id=user_id
        )
        session.add(participant)
        await session.commit()
        return True
    
    @staticmethod
    async def is_participant(
        session: AsyncSession,
        tournament_id: int,
        user_id: int
    ) -> bool:
        """Проверка, является ли пользователь участником турнира"""
        result = await session.execute(
            select(TournamentParticipant).where(
                TournamentParticipant.tournament_id == tournament_id,
                TournamentParticipant.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def start_tournament(session: AsyncSession, tournament_id: int) -> bool:
        """Запуск турнира (после жеребьёвки)"""
        tournament = await TournamentService.get_tournament(session, tournament_id)
        if not tournament or tournament.status != TournamentStatus.REGISTRATION or not tournament.draw_completed:
            return False
        
        await session.execute(
            update(Tournament)
            .where(Tournament.id == tournament_id)
            .values(
                status=TournamentStatus.ACTIVE,
                started_at=datetime.utcnow()
            )
        )
        await session.commit()
        return True
    
    @staticmethod
    async def finish_tournament(session: AsyncSession, tournament_id: int) -> bool:
        """Завершение турнира"""
        tournament = await TournamentService.get_tournament(session, tournament_id)
        if not tournament or tournament.status != TournamentStatus.ACTIVE:
            return False
        
        await session.execute(
            update(Tournament)
            .where(Tournament.id == tournament_id)
            .values(
                status=TournamentStatus.FINISHED,
                finished_at=datetime.utcnow()
            )
        )
        await session.commit()
        return True
    
    @staticmethod
    async def delete_tournament(session: AsyncSession, tournament_id: int) -> bool:
        """Удаление турнира со всеми связанными данными"""
        try:
            await session.execute(
                delete(Match).where(Match.tournament_id == tournament_id)
            )
            await session.execute(
                delete(TournamentParticipant).where(
                    TournamentParticipant.tournament_id == tournament_id
                )
            )
            await session.execute(
                delete(TournamentRecord).where(
                    TournamentRecord.tournament_id == tournament_id
                )
            )
            await session.execute(
                delete(Tournament).where(Tournament.id == tournament_id)
            )
            
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            print(f"Error deleting tournament: {e}")
            return False
    
    @staticmethod
    async def get_tournament_table(session: AsyncSession, tournament_id: int) -> List[tuple]:
        """Получение турнирной таблицы"""
        result = await session.execute(
            select(TournamentParticipant, User)
            .join(User, TournamentParticipant.user_id == User.id)
            .where(TournamentParticipant.tournament_id == tournament_id)
            .order_by(
                TournamentParticipant.points.desc(),
                (TournamentParticipant.goals_for - TournamentParticipant.goals_against).desc(),
                TournamentParticipant.goals_for.desc()
            )
        )
        return result.all()
    
    @staticmethod
    async def format_tournament_table(table_data: List[tuple]) -> str:
        """КОМПАКТНОЕ форматирование турнирной таблицы"""
        if not table_data:
            return "📊 <b>Турнирная таблица</b>\n\nУчастников пока нет."
        
        text = "📊 <b>Турнирная таблица</b>\n\n"
        text += "<pre>"
        text += "№  Игрок       М  О  Г  Р\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        for i, (participant, user) in enumerate(table_data, 1):
            if user.username:
                name = f"@{user.username}"[:10]
            else:
                name = user.full_name[:10]
            name = name.ljust(10)
            
            goal_diff = participant.goals_for - participant.goals_against
            diff_str = f"+{goal_diff}" if goal_diff > 0 else str(goal_diff)
            
            pos = str(i).rjust(2)
            matches = str(participant.matches_played).rjust(2)
            points = str(participant.points).rjust(2)
            goals = f"{participant.goals_for}:{participant.goals_against}".ljust(5)
            diff = diff_str.rjust(3)
            
            text += f"{pos} {name} {matches} {points} {goals} {diff}\n"
        
        text += "</pre>\n"
        text += "<i>М-матчи О-очки Г-голы Р-разница</i>"
        
        return text
    
    @staticmethod
    async def get_participants(
        session: AsyncSession,
        tournament_id: int
    ) -> List[tuple]:
        """Получение списка участников турнира"""
        result = await session.execute(
            select(TournamentParticipant, User)
            .join(User, TournamentParticipant.user_id == User.id)
            .where(TournamentParticipant.tournament_id == tournament_id)
            .order_by(TournamentParticipant.registered_at)
        )
        return result.all()
    
    @staticmethod
    async def update_participant_stats(
        session: AsyncSession,
        tournament_id: int,
        user_id: int,
        result: str,
        goals_for: int,
        goals_against: int
    ):
        """Обновление статистики участника турнира"""
        result_participant = await session.execute(
            select(TournamentParticipant).where(
                TournamentParticipant.tournament_id == tournament_id,
                TournamentParticipant.user_id == user_id
            )
        )
        participant = result_participant.scalar_one()
        
        participant.matches_played += 1
        participant.goals_for += goals_for
        participant.goals_against += goals_against
        
        if result == "win":
            participant.wins += 1
            participant.points += 3
        elif result == "draw":
            participant.draws += 1
            participant.points += 1
        else:
            participant.losses += 1
        
        await session.commit()