"""
T-League Bot - Инициализация базы данных
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from config import config
from database.models import Base, SystemSettings

# Создание асинхронного движка
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,  # Установите True для отладки SQL-запросов
)

# Фабрика сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Инициализация базы данных"""
    # Создание директории для БД если её нет
    db_dir = os.path.dirname(config.DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Инициализация системных настроек
    async with async_session_maker() as session:
        # Проверка наличия настройки техобслуживания
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == "maintenance_mode")
        )
        maintenance_setting = result.scalar_one_or_none()
        
        if not maintenance_setting:
            maintenance_setting = SystemSettings(
                key="maintenance_mode",
                value="false"
            )
            session.add(maintenance_setting)
            await session.commit()

async def get_session() -> AsyncSession:
    """Получение сессии базы данных"""
    async with async_session_maker() as session:
        yield session