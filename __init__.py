"""
Создайте следующие __init__.py файлы в соответствующих директориях:
"""

# ==================== database/__init__.py ====================
"""T-League Bot - Database package"""

from database.engine import init_db, get_session, async_session_maker
from database.models import (
    Base, User, Tournament, TournamentParticipant, Match,
    TournamentRecord, SystemSettings, AdminLog, TesterAccessLog,
    TournamentStatus, TournamentFormat, MatchStatus
)

__all__ = [
    'init_db',
    'get_session',
    'async_session_maker',
    'Base',
    'User',
    'Tournament',
    'TournamentParticipant',
    'Match',
    'TournamentRecord',
    'SystemSettings',
    'AdminLog',
    'TesterAccessLog',
    'TournamentStatus',
    'TournamentFormat',
    'MatchStatus',
]


# ==================== handlers/__init__.py ====================
"""T-League Bot - Handlers package"""

# Пустой файл - импорты делаются в bot.py

__all__ = []


# ==================== keyboards/__init__.py ====================
"""T-League Bot - Keyboards package"""

# Пустой файл - импорты делаются напрямую

__all__ = []


# ==================== middlewares/__init__.py ====================
"""T-League Bot - Middlewares package"""

from middlewares.maintenance import MaintenanceMiddleware

__all__ = ['MaintenanceMiddleware']


# ==================== services/__init__.py ====================
"""T-League Bot - Services package"""

# Пустой файл - импорты делаются напрямую

__all__ = []


# ==================== states/__init__.py ====================
"""T-League Bot - FSM States package"""

from states.states import (
    TournamentCreation,
    MatchReport,
    AdminBroadcast,
    TesterAccess,
    DeadlineSettings,
    RatingRecalculation,
    PlayerSearch
)

__all__ = [
    'TournamentCreation',
    'MatchReport',
    'AdminBroadcast',
    'TesterAccess',
    'DeadlineSettings',
    'RatingRecalculation',
    'PlayerSearch',
]


# ==================== utils/__init__.py ====================
"""T-League Bot - Utilities package"""

# Пустой файл - импорты делаются напрямую

__all__ = []