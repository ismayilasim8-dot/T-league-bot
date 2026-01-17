"""Middleware проверки подписки на канал"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config

class SubscriptionMiddleware(BaseMiddleware):
    """Проверка подписки перед использованием бота"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not config.REQUIRED_CHANNEL:
            return await handler(event, data)
        
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        if not user_id or user_id in config.ADMIN_IDS:
            return await handler(event, data)
        
        bot = data.get("bot")
        try:
            member = await bot.get_chat_member(config.REQUIRED_CHANNEL, user_id)
            if member.status in ["member", "administrator", "creator"]:
                return await handler(event, data)
        except:
            pass
        
        kb = InlineKeyboardBuilder()
        kb.button(text="📢 Подписаться на канал", url=f"https://t.me/{config.REQUIRED_CHANNEL.lstrip('@')}")
        kb.button(text="✅ Проверить подписку", callback_data="check_subscription")
        kb.adjust(1)
        
        text = (
            "📢 <b>Требуется подписка</b>\n\n"
            f"Для использования бота подпишитесь на канал:\n"
            f"{config.REQUIRED_CHANNEL}\n\n"
            "После подписки нажмите 'Проверить подписку'"
        )
        
        if isinstance(event, Message):
            await event.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
        elif isinstance(event, CallbackQuery):
            await event.answer("Требуется подписка на канал", show_alert=True)
        
        return