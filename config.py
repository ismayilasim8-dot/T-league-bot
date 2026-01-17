"""
T-League Bot - Конфигурация
"""
from dataclasses import dataclass, field
from typing import List

@dataclass
class Config:
    """Конфигурация бота"""

    # Токен бота (получить у @BotFather)
    BOT_TOKEN: str = "8302116674:AAFA7QbBRVo0r8u-F2mfNIRmxFVsXp8E7n8"

    # ID администраторов (список Telegram ID)
    ADMIN_IDS: List[int] = field(default_factory=lambda: [7252997554])  # Замените на свои ID

    # Секретный код для тестеров
    TESTER_ACCESS_CODE: str = "test2025"

    # База данных
    DB_PATH: str = "database/t_league.db"
    DATABASE_URL: str = "sqlite+aiosqlite:///database/t_league.db"

    # Версия бота
    BOT_VERSION: str = "1.1.0"

    # Информация о проекте
    PROJECT_NAME: str = "T-League"
    PROJECT_DESCRIPTION: str = (
        "🏆 Виртуальный турнир с автоматическим управлением матчами, "
        "рейтингами и статистикой.\n\n"
        "Участвуйте в турнирах, отслеживайте свой прогресс и "
        "соревнуйтесь за звание лучшего игрока!"
    )

    # Ссылки проекта
    CHANNEL_URL: str = "https://t.me/tleagueefootball"
    MANAGER_URL: str = "https://t.me/tleaguerobot"
    CHAT_URL: str = "https://t.me/your_chat"
    RULES_URL: str = "https://t.me/your_rules"

    # Рейтинговая система
    RATING_WIN: int = 3
    RATING_DRAW: int = 1
    RATING_LOSS: int = -5
    INITIAL_RATING: int = 100

    # Настройки уведомлений
    DEADLINE_WARNING_HOURS: int = 24  # За сколько часов предупреждать о дедлайне

    # Часовой пояс МСК (UTC+3)
    MSK_TIMEZONE_OFFSET: int = 3


# Создание экземпляра конфигурации
config = Config()