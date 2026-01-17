"""
T-League Bot - Рекорды турнира
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database.models import TournamentRecord, TournamentParticipant, Match, MatchStatus, User
from typing import Dict

class RecordsService:
    """Сервис управления рекордами турнира"""
    
    @staticmethod
    async def calculate_tournament_records(session: AsyncSession, tournament_id: int):
        """
        Расчёт всех рекордов турнира после его завершения
        """
        # Удаление старых рекордов турнира
        await session.execute(
            delete(TournamentRecord).where(TournamentRecord.tournament_id == tournament_id)
        )
        
        # Получение всех участников турнира
        result = await session.execute(
            select(TournamentParticipant, User)
            .join(User, TournamentParticipant.user_id == User.id)
            .where(TournamentParticipant.tournament_id == tournament_id)
        )
        participants_data = result.all()
        
        if not participants_data:
            return
        
        # Рекорд: Самый результативный игрок
        top_scorer = max(participants_data, key=lambda x: x[0].goals_for)
        if top_scorer[0].goals_for > 0:
            record = TournamentRecord(
                tournament_id=tournament_id,
                record_type="top_scorer",
                user_id=top_scorer[0].user_id,
                value=float(top_scorer[0].goals_for),
                description=f"Забил {top_scorer[0].goals_for} голов"
            )
            session.add(record)
        
        # Рекорд: Лучшая защита
        best_defense = min(participants_data, key=lambda x: x[0].goals_against)
        if best_defense[0].matches_played > 0:
            record = TournamentRecord(
                tournament_id=tournament_id,
                record_type="best_defense",
                user_id=best_defense[0].user_id,
                value=float(best_defense[0].goals_against),
                description=f"Пропустил {best_defense[0].goals_against} голов"
            )
            session.add(record)
        
        # Рекорд: Лучший winrate
        for participant, user in participants_data:
            if participant.matches_played >= 3:  # Минимум 3 матча
                winrate = (participant.wins / participant.matches_played) * 100
                participant.winrate = winrate
        
        best_winrate_data = max(
            [(p, u) for p, u in participants_data if p.matches_played >= 3],
            key=lambda x: (x[0].wins / x[0].matches_played) if x[0].matches_played > 0 else 0,
            default=None
        )
        
        if best_winrate_data:
            participant, user = best_winrate_data
            winrate = (participant.wins / participant.matches_played) * 100
            record = TournamentRecord(
                tournament_id=tournament_id,
                record_type="best_winrate",
                user_id=participant.user_id,
                value=winrate,
                description=f"{participant.wins} побед из {participant.matches_played} матчей ({winrate:.1f}%)"
            )
            session.add(record)
        
        # Рекорд: Больше всего ничьих
        most_draws = max(participants_data, key=lambda x: x[0].draws)
        if most_draws[0].draws > 0:
            record = TournamentRecord(
                tournament_id=tournament_id,
                record_type="most_draws",
                user_id=most_draws[0].user_id,
                value=float(most_draws[0].draws),
                description=f"Сыграл вничью {most_draws[0].draws} раз"
            )
            session.add(record)
        
        # Рекорд: Самое крупное поражение
        await RecordsService._calculate_biggest_defeat(session, tournament_id)
        
        # Рекорд: Лучшая серия побед
        await RecordsService._calculate_best_win_streak(session, tournament_id)
        
        await session.commit()
    
    @staticmethod
    async def _calculate_biggest_defeat(session: AsyncSession, tournament_id: int):
        """Расчёт самого крупного поражения"""
        result = await session.execute(
            select(Match)
            .where(
                Match.tournament_id == tournament_id,
                Match.status == MatchStatus.CONFIRMED
            )
        )
        matches = result.scalars().all()
        
        biggest_defeat = None
        max_diff = 0
        loser_id = None
        
        for match in matches:
            diff = abs(match.player1_score - match.player2_score)
            if diff > max_diff:
                max_diff = diff
                biggest_defeat = match
                loser_id = match.player2_id if match.player1_score > match.player2_score else match.player1_id
        
        if biggest_defeat and max_diff > 0:
            record = TournamentRecord(
                tournament_id=tournament_id,
                record_type="biggest_defeat",
                user_id=loser_id,
                value=float(max_diff),
                description=f"Проиграл со счётом {biggest_defeat.player1_score}:{biggest_defeat.player2_score}"
            )
            session.add(record)
    
    @staticmethod
    async def _calculate_best_win_streak(session: AsyncSession, tournament_id: int):
        """Расчёт лучшей серии побед"""
        # Получение всех матчей турнира в хронологическом порядке
        result = await session.execute(
            select(Match)
            .where(
                Match.tournament_id == tournament_id,
                Match.status == MatchStatus.CONFIRMED
            )
            .order_by(Match.confirmed_at)
        )
        matches = result.scalars().all()
        
        # Отслеживание серий для каждого игрока
        streaks: Dict[int, int] = {}
        best_streak_user = None
        best_streak_value = 0
        
        for match in matches:
            winner_id = None
            if match.player1_score > match.player2_score:
                winner_id = match.player1_id
                loser_id = match.player2_id
            elif match.player2_score > match.player1_score:
                winner_id = match.player2_id
                loser_id = match.player1_id
            
            if winner_id:
                streaks[winner_id] = streaks.get(winner_id, 0) + 1
                streaks[loser_id] = 0
                
                if streaks[winner_id] > best_streak_value:
                    best_streak_value = streaks[winner_id]
                    best_streak_user = winner_id
        
        if best_streak_user and best_streak_value >= 2:
            record = TournamentRecord(
                tournament_id=tournament_id,
                record_type="best_win_streak",
                user_id=best_streak_user,
                value=float(best_streak_value),
                description=f"Серия из {best_streak_value} побед подряд"
            )
            session.add(record)
    
    @staticmethod
    async def get_tournament_records(session: AsyncSession, tournament_id: int) -> list:
        """Получение рекордов турнира"""
        result = await session.execute(
            select(TournamentRecord, User)
            .join(User, TournamentRecord.user_id == User.id)
            .where(TournamentRecord.tournament_id == tournament_id)
            .order_by(TournamentRecord.created_at)
        )
        return result.all()
    
    @staticmethod
    async def format_records(records: list) -> str:
        """Форматирование рекордов для отображения"""
        if not records:
            return "🏅 <b>Рекорды турнира</b>\n\nРекорды ещё не сформированы."
        
        text = "🏅 <b>Рекорды турнира</b>\n\n"
        
        record_names = {
            "top_scorer": "⚽ Самый результативный",
            "best_defense": "🛡️ Лучшая защита",
            "best_winrate": "📈 Лучший winrate",
            "most_draws": "🤝 Больше всего ничьих",
            "biggest_defeat": "💥 Самое крупное поражение",
            "best_win_streak": "🔥 Лучшая серия побед"
        }
        
        for record, user in records:
            record_name = record_names.get(record.record_type, record.record_type)
            username = user.username if user.username else user.full_name
            
            text += (
                f"{record_name}\n"
                f"👤 <b>{username}</b>\n"
                f"📊 {record.description}\n\n"
            )
        
        return text