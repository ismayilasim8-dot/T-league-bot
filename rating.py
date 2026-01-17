"""
T-League Bot - Рейтинговая система
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import User, Match, MatchStatus
from config import config

class RatingService:
    """Сервис управления рейтингом"""
    
    @staticmethod
    async def update_user_rating(session: AsyncSession, user_id: int, points: int):
        """Обновление рейтинга пользователя"""
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(rating=User.rating + points)
        )
    
    @staticmethod
    async def update_match_stats(session: AsyncSession, match: Match):
        """
        Обновление статистики после матча и рейтинга игроков
        """
        if match.status != MatchStatus.CONFIRMED:
            return
        
        player1_id = match.player1_id
        player2_id = match.player2_id
        score1 = match.player1_score
        score2 = match.player2_score
        
        # Определение результата
        if score1 > score2:
            # Победа игрока 1
            await RatingService._update_player_after_match(
                session, player1_id, "win", score1, score2
            )
            await RatingService._update_player_after_match(
                session, player2_id, "loss", score2, score1
            )
        elif score1 < score2:
            # Победа игрока 2
            await RatingService._update_player_after_match(
                session, player1_id, "loss", score1, score2
            )
            await RatingService._update_player_after_match(
                session, player2_id, "win", score2, score1
            )
        else:
            # Ничья
            await RatingService._update_player_after_match(
                session, player1_id, "draw", score1, score2
            )
            await RatingService._update_player_after_match(
                session, player2_id, "draw", score2, score1
            )
    
    @staticmethod
    async def _update_player_after_match(
        session: AsyncSession,
        user_id: int,
        result: str,
        goals_for: int,
        goals_against: int
    ):
        """Обновление статистики игрока после матча"""
        result_user = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result_user.scalar_one()
        
        # Обновление счётчиков
        user.matches_played += 1
        
        if result == "win":
            user.wins += 1
            user.rating += config.RATING_WIN
            # Обновление серии
            if user.current_streak >= 0:
                user.current_streak += 1
            else:
                user.current_streak = 1
        elif result == "loss":
            user.losses += 1
            user.rating += config.RATING_LOSS  # -5
            # Обновление серии
            if user.current_streak <= 0:
                user.current_streak -= 1
            else:
                user.current_streak = -1
        else:  # draw
            user.draws += 1
            user.rating += config.RATING_DRAW
            user.current_streak = 0
        
        await session.commit()
    
    @staticmethod
    async def calculate_winrate(user: User) -> float:
        """Расчёт winrate"""
        if user.matches_played == 0:
            return 0.0
        return (user.wins / user.matches_played) * 100
    
    @staticmethod
    async def get_top_players(session: AsyncSession, limit: int = 10) -> list:
        """Получение топ игроков по рейтингу"""
        result = await session.execute(
            select(User)
            .where(User.matches_played > 0)
            .order_by(User.rating.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_all_players_ranked(session: AsyncSession) -> list:
        """Получение всех игроков с рейтингом"""
        result = await session.execute(
            select(User)
            .where(User.matches_played > 0)
            .order_by(User.rating.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def format_rating_table(players: list, show_position: bool = True) -> str:
        """Форматирование таблицы рейтинга"""
        if not players:
            return "📊 <b>Рейтинг пока пуст</b>\n\nСыграйте матчи, чтобы появиться в рейтинге!"
        
        text = "📊 <b>Рейтинг игроков</b>\n\n"
        
        for i, player in enumerate(players, 1):
            # Расчёт winrate
            winrate = 0
            if player.matches_played > 0:
                winrate = (player.wins / player.matches_played) * 100
            
            # Серия
            streak_text = ""
            if player.current_streak > 0:
                streak_text = f"🔥 {player.current_streak}W"
            elif player.current_streak < 0:
                streak_text = f"❄️ {abs(player.current_streak)}L"
            else:
                streak_text = "➖"
            
            # Формирование строки
            position = f"{i}. " if show_position else ""
            username = player.username if player.username else player.full_name
            
            text += (
                f"{position}<b>{username}</b>\n"
                f"├ Матчи: {player.matches_played} | "
                f"Рейтинг: {player.rating}\n"
                f"├ W/D/L: {player.wins}/{player.draws}/{player.losses}\n"
                f"├ Winrate: {winrate:.1f}% | Серия: {streak_text}\n"
                f"└─────────────\n"
            )
        
        return text
    
    @staticmethod
    async def recalculate_all_ratings(session: AsyncSession):
        """
        Полный пересчёт всех рейтингов на основе подтверждённых матчей
        """
        # Сброс всех рейтингов и статистики
        await session.execute(
            update(User).values(
                rating=config.INITIAL_RATING,
                matches_played=0,
                wins=0,
                draws=0,
                losses=0,
                current_streak=0
            )
        )
        await session.commit()
        
        # Получение всех подтверждённых матчей в хронологическом порядке
        result = await session.execute(
            select(Match)
            .where(Match.status == MatchStatus.CONFIRMED)
            .order_by(Match.confirmed_at)
        )
        matches = result.scalars().all()
        
        # Пересчёт по каждому матчу
        for match in matches:
            await RatingService.update_match_stats(session, match)