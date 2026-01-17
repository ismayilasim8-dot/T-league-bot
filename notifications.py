"""
T-League Bot - Сервис уведомлений
"""
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Match, User, MatchStatus
from datetime import datetime, timedelta
from config import config
from typing import List

class NotificationService:
    """Сервис управления уведомлениями"""
    
    @staticmethod
    async def notify_match_created(
        bot: Bot,
        session: AsyncSession,
        match: Match
    ):
        """Уведомление игроков о создании матча"""
        # Получение информации об игроках
        result = await session.execute(
            select(User).where(User.id.in_([match.player1_id, match.player2_id]))
        )
        players = result.scalars().all()
        
        for player in players:
            opponent_id = match.player2_id if player.id == match.player1_id else match.player1_id
            opponent_result = await session.execute(
                select(User).where(User.id == opponent_id)
            )
            opponent = opponent_result.scalar_one()
            
            opponent_name = opponent.username if opponent.username else opponent.full_name
            deadline_str = match.deadline.strftime("%d.%m.%Y %H:%M")
            
            message = (
                f"⚔️ <b>Новый матч!</b>\n\n"
                f"Вам назначен матч против <b>{opponent_name}</b>\n"
                f"⏰ Дедлайн: {deadline_str}\n\n"
                f"Не забудьте внести результат до истечения дедлайна!"
            )
            
            try:
                await bot.send_message(player.id, message, parse_mode="HTML")
            except Exception as e:
                # Логирование ошибки
                print(f"Failed to send notification to {player.id}: {e}")
    
    @staticmethod
    async def notify_deadline_approaching(
        bot: Bot,
        session: AsyncSession,
        match: Match,
        hours_left: int
    ):
        """Уведомление о приближающемся дедлайне"""
        result = await session.execute(
            select(User).where(User.id.in_([match.player1_id, match.player2_id]))
        )
        players = result.scalars().all()
        
        for player in players:
            opponent_id = match.player2_id if player.id == match.player1_id else match.player1_id
            opponent_result = await session.execute(
                select(User).where(User.id == opponent_id)
            )
            opponent = opponent_result.scalar_one()
            
            opponent_name = opponent.username if opponent.username else opponent.full_name
            deadline_str = match.deadline.strftime("%d.%m.%Y %H:%M")
            
            message = (
                f"⏰ <b>Внимание! Дедлайн близко</b>\n\n"
                f"До окончания матча против <b>{opponent_name}</b> "
                f"осталось <b>{hours_left} часов</b>!\n\n"
                f"⏰ Дедлайн: {deadline_str}\n"
                f"Внесите результат, иначе будет засчитано техническое поражение."
            )
            
            try:
                await bot.send_message(player.id, message, parse_mode="HTML")
            except Exception as e:
                print(f"Failed to send deadline warning to {player.id}: {e}")
    
    @staticmethod
    async def notify_match_confirmation_request(
        bot: Bot,
        session: AsyncSession,
        match: Match,
        opponent_id: int
    ):
        """Уведомление о запросе подтверждения результата"""
        result = await session.execute(
            select(User).where(User.id.in_([match.reported_by, opponent_id]))
        )
        users = {u.id: u for u in result.scalars().all()}
        
        reporter = users[match.reported_by]
        opponent = users[opponent_id]
        
        reporter_name = reporter.username if reporter.username else reporter.full_name
        
        message = (
            f"📝 <b>Подтверждение результата</b>\n\n"
            f"<b>{reporter_name}</b> внёс результат матча:\n"
            f"<b>{match.player1_score}:{match.player2_score}</b>\n\n"
            f"Подтвердите результат или оспорьте его."
        )
        
        try:
            from keyboards.user_kb import get_match_confirmation_keyboard
            await bot.send_message(
                opponent_id,
                message,
                parse_mode="HTML",
                reply_markup=get_match_confirmation_keyboard(match.id)
            )
        except Exception as e:
            print(f"Failed to send confirmation request to {opponent_id}: {e}")
    
    @staticmethod
    async def notify_match_confirmed(
        bot: Bot,
        session: AsyncSession,
        match: Match
    ):
        """Уведомление об подтверждении матча"""
        result = await session.execute(
            select(User).where(User.id.in_([match.player1_id, match.player2_id]))
        )
        players = result.scalars().all()
        
        for player in players:
            message = (
                f"✅ <b>Матч подтверждён!</b>\n\n"
                f"Результат: <b>{match.player1_score}:{match.player2_score}</b>\n"
                f"Рейтинг обновлён."
            )
            
            try:
                await bot.send_message(player.id, message, parse_mode="HTML")
            except Exception as e:
                print(f"Failed to send confirmation to {player.id}: {e}")
    
    @staticmethod
    async def notify_match_disputed(
        bot: Bot,
        session: AsyncSession,
        match: Match,
        admin_ids: List[int]
    ):
        """Уведомление администраторов об оспаривании результата"""
        result = await session.execute(
            select(User).where(User.id.in_([match.player1_id, match.player2_id]))
        )
        users = {u.id: u for u in result.scalars().all()}
        
        p1_name = users[match.player1_id].username or users[match.player1_id].full_name
        p2_name = users[match.player2_id].username or users[match.player2_id].full_name
        
        message = (
            f"⚠️ <b>Результат оспорен!</b>\n\n"
            f"Матч: <b>{p1_name}</b> vs <b>{p2_name}</b>\n"
            f"Счёт: {match.player1_score}:{match.player2_score}\n\n"
            f"Требуется вмешательство администратора."
        )
        
        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, message, parse_mode="HTML")
            except Exception as e:
                print(f"Failed to send dispute notification to admin {admin_id}: {e}")
    
    @staticmethod
    async def broadcast_message(
        bot: Bot,
        session: AsyncSession,
        message_text: str,
        exclude_admins: bool = False
    ) -> tuple:
        """Массовая рассылка сообщения всем пользователям"""
        query = select(User)
        if exclude_admins:
            query = query.where(User.is_admin == False)
        
        result = await session.execute(query)
        users = result.scalars().all()
        
        success_count = 0
        fail_count = 0
        
        for user in users:
            try:
                await bot.send_message(user.id, message_text, parse_mode="HTML")
                success_count += 1
            except Exception:
                fail_count += 1
        
        return success_count, fail_count
    
    @staticmethod
    async def check_and_send_deadline_warnings(
        bot: Bot,
        session: AsyncSession
    ):
        """
        Проверка и отправка предупреждений о дедлайне
        (вызывается периодически из фонового задания)
        """
        now = datetime.utcnow()
        warning_time = now + timedelta(hours=config.DEADLINE_WARNING_HOURS)
        
        # Получение матчей с приближающимся дедлайном
        result = await session.execute(
            select(Match).where(
                Match.status == MatchStatus.SCHEDULED,
                Match.deadline <= warning_time,
                Match.deadline > now
            )
        )
        matches = result.scalars().all()
        
        for match in matches:
            hours_left = int((match.deadline - now).total_seconds() / 3600)
            await NotificationService.notify_deadline_approaching(
                bot, session, match, hours_left
            )