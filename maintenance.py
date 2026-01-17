"""
T-League Bot - Middleware техобслуживания
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import SystemSettings, User
from database.engine import async_session_maker

class MaintenanceMiddleware(BaseMiddleware):
    """
    Middleware для блокировки действий во время техобслуживания.
    Не блокирует администраторов и пользователей с доступом тестера.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id из события
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        if not user_id:
            return await handler(event, data)
        
        # Проверяем статус техобслуживания
        async with async_session_maker() as session:
            # Получаем настройку техобслуживания
            result = await session.execute(
                select(SystemSettings).where(SystemSettings.key == "maintenance_mode")
            )
            maintenance_setting = result.scalar_one_or_none()
            
            # Если техобслуживание не включено, пропускаем
            if not maintenance_setting or maintenance_setting.value != "true":
                return await handler(event, data)
            
            # Проверяем права пользователя
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            # Пропускаем администраторов и тестеров
            if user and (user.is_admin or user.is_tester):
                return await handler(event, data)
        
        # Блокируем обычных пользователей
        maintenance_message = (
            "🔧 <b>Технические работы</b>\n\n"
            "В данный момент проводятся технические работы.\n"
            "Пожалуйста, попробуйте позже.\n\n"
            "Приносим извинения за неудобства."
        )
        
        if isinstance(event, Message):
            await event.answer(maintenance_message, parse_mode="HTML")
        elif isinstance(event, CallbackQuery):
            await event.answer(
                "🔧 Технические работы. Попробуйте позже.",
                show_alert=True
            )
        
        # Не вызываем обработчик
        return