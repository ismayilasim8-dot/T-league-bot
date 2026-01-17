"""
T-League Bot - Расписание матчей
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import Match, Tournament, User, MatchStatus
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from config import config

class ScheduleService:
    """Сервис управления расписанием матчей"""
    
    @staticmethod
    def utc_to_msk(utc_time: datetime) -> datetime:
        """Конвертация UTC в МСК"""
        return utc_time + timedelta(hours=config.MSK_TIMEZONE_OFFSET)
    
    @staticmethod
    def msk_to_utc(msk_time: datetime) -> datetime:
        """Конвертация МСК в UTC"""
        return msk_time - timedelta(hours=config.MSK_TIMEZONE_OFFSET)
    
    @staticmethod
    async def get_rounds_info(session: AsyncSession, tournament_id: int) -> List[Dict]:
        """
        Получение информации о турах турнира
        Возвращает список словарей с информацией о каждом туре
        """
        result = await session.execute(
            select(Match.round_number, Match.deadline_set)
            .where(Match.tournament_id == tournament_id)
            .distinct()
            .order_by(Match.round_number)
        )
        
        rounds_data = {}
        for round_num, deadline_set in result.all():
            if round_num not in rounds_data:
                rounds_data[round_num] = False
            if deadline_set:
                rounds_data[round_num] = True
        
        return [
            {'round_number': r, 'has_deadline': has_dl}
            for r, has_dl in rounds_data.items()
        ]
    
    @staticmethod
    async def get_rounds_with_deadline(session: AsyncSession, tournament_id: int) -> List[int]:
        """Получение списка туров с установленным дедлайном"""
        result = await session.execute(
            select(Match.round_number)
            .where(
                Match.tournament_id == tournament_id,
                Match.deadline_set == True
            )
            .distinct()
            .order_by(Match.round_number)
        )
        return [r[0] for r in result.all()]
    
    @staticmethod
    async def set_deadline_for_round(
        session: AsyncSession,
        tournament_id: int,
        round_number: int,
        deadline_msk: datetime
    ) -> int:
        """
        Установка дедлайна для всех матчей тура
        deadline_msk - время по МСК
        Возвращает количество обновлённых матчей
        """
        # Конвертация в UTC для хранения в БД
        deadline_utc = ScheduleService.msk_to_utc(deadline_msk)
        
        result = await session.execute(
            select(Match).where(
                Match.tournament_id == tournament_id,
                Match.round_number == round_number
            )
        )
        matches = result.scalars().all()
        
        count = 0
        for match in matches:
            match.deadline = deadline_utc
            match.deadline_set = True
            count += 1
        
        await session.commit()
        return count
    
    @staticmethod
    async def get_tournament_matches(
        session: AsyncSession,
        tournament_id: int,
        round_number: Optional[int] = None
    ) -> List[tuple]:
        """Получение матчей турнира с игроками"""
        query = (
            select(Match)
            .where(Match.tournament_id == tournament_id)
        )
        
        if round_number:
            query = query.where(Match.round_number == round_number)
        
        query = query.order_by(Match.round_number, Match.created_at)
        
        result = await session.execute(query)
        matches = result.scalars().all()
        
        # Получаем информацию об игроках
        matches_with_players = []
        for match in matches:
            p1_result = await session.execute(select(User).where(User.id == match.player1_id))
            p2_result = await session.execute(select(User).where(User.id == match.player2_id))
            
            player1 = p1_result.scalar_one()
            player2 = p2_result.scalar_one()
            
            matches_with_players.append((match, player1, player2))
        
        return matches_with_players
    
    @staticmethod
    async def get_user_matches_in_round(
        session: AsyncSession,
        user_id: int,
        tournament_id: int,
        round_number: int
    ) -> Optional[Match]:
        """Получение матча пользователя в конкретном туре"""
        result = await session.execute(
            select(Match).where(
                Match.tournament_id == tournament_id,
                Match.round_number == round_number,
                ((Match.player1_id == user_id) | (Match.player2_id == user_id)),
                Match.status == MatchStatus.SCHEDULED,
                Match.deadline_set == True
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_matches(
        session: AsyncSession,
        user_id: int,
        tournament_id: Optional[int] = None,
        status: Optional[MatchStatus] = None
    ) -> List[Match]:
        """Получение матчей пользователя"""
        query = select(Match).where(
            (Match.player1_id == user_id) | (Match.player2_id == user_id)
        )
        
        if tournament_id:
            query = query.where(Match.tournament_id == tournament_id)
        
        if status:
            query = query.where(Match.status == status)
        
        query = query.order_by(Match.round_number.desc())
        
        result = await session.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def format_schedule(matches_data: List[tuple]) -> str:
        """Форматирование расписания матчей с username"""
        if not matches_data:
            return "📅 <b>Расписание матчей</b>\n\nМатчей пока нет."
        
        text = "📅 <b>Расписание матчей</b>\n\n"
        
        current_round = None
        for match, player1, player2 in matches_data:
            # Заголовок раунда
            if current_round != match.round_number:
                current_round = match.round_number
                text += f"<b>═══ Тур {current_round} ═══</b>\n\n"
            
            # Статус матча
            status_emoji = {
                MatchStatus.SCHEDULED: "⏳",
                MatchStatus.PENDING: "⌛",
                MatchStatus.CONFIRMED: "✅",
                MatchStatus.DISPUTED: "⚠️",
                MatchStatus.TECHNICAL: "🚫"
            }.get(match.status, "❓")
            
            # Имена игроков с username
            p1_name = f"@{player1.username}" if player1.username else player1.full_name
            p2_name = f"@{player2.username}" if player2.username else player2.full_name
            
            # Счёт
            score_text = ""
            if match.status in [MatchStatus.CONFIRMED, MatchStatus.PENDING, MatchStatus.DISPUTED]:
                score_text = f" <b>{match.player1_score}:{match.player2_score}</b>"
            
            # Дедлайн
            deadline_text = ""
            if match.deadline_set and match.deadline:
                deadline_msk = ScheduleService.utc_to_msk(match.deadline)
                deadline_text = f"\n⏰ Дедлайн: {deadline_msk.strftime('%d.%m.%Y %H:%M')} МСК"
            elif not match.deadline_set:
                deadline_text = "\n⏰ Дедлайн не установлен"
            
            text += (
                f"{status_emoji} {p1_name} <b>vs</b> {p2_name}{score_text}"
                f"{deadline_text}\n\n"
            )
        
        return text
    
    @staticmethod
    async def check_expired_matches(session: AsyncSession):
        """
        Проверка просроченных матчей и автоматическое техническое поражение
        """
        now = datetime.utcnow()
        
        result = await session.execute(
            select(Match).where(
                Match.status == MatchStatus.SCHEDULED,
                Match.deadline_set == True,
                Match.deadline < now
            )
        )
        expired_matches = result.scalars().all()
        
        for match in expired_matches:
            match.status = MatchStatus.TECHNICAL
            match.player1_score = 0
            match.player2_score = 0
            match.played_at = now
            match.confirmed_at = now
        
        await session.commit()
        return expired_matches