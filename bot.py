"""
T-League Bot - Главный файл запуска (Обновлённая версия 1.1.0)
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.engine import init_db
from middlewares.maintenance import MaintenanceMiddleware

# Импорт хендлеров
from handlers import user, admin, matches

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных инициализирована")
    
    # Уведомление администраторов о запуске
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"✅ <b>{config.PROJECT_NAME} Bot запущен!</b>\n"
                f"Версия: {config.BOT_VERSION}\n\n"
                f"🆕 Обновления:\n"
                f"• Inline главное меню\n"
                f"• Красивые таблицы\n"
                f"• Жеребьёвка турниров\n"
                f"• Дедлайны по МСК\n"
                f"• Поиск игроков\n"
                f"• Групповой + плей-офф формат",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    logger.info("Бот запущен и готов к работе!")

async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("Бот останавливается...")
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⚠️ <b>{config.PROJECT_NAME} Bot остановлен</b>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
    
    logger.info("Бот остановлен")

async def main():
    """Основная функция запуска бота"""
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ ОШИБКА: Токен бота не установлен!")
        logger.error("Откройте config.py и укажите токен в BOT_TOKEN")
        return
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Подключение middleware
    dp.message.middleware(MaintenanceMiddleware())
    dp.callback_query.middleware(MaintenanceMiddleware())
    
    # Регистрация роутеров
    dp.include_router(user.router)
    dp.include_router(matches.router)
    dp.include_router(admin.router)
    
    # Регистрация startup/shutdown хуков
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запуск polling
    try:
        logger.info("Запуск бота...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")