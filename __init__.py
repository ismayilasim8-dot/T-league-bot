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

from handlers import user, admin, matches

__all__ = ['user', 'admin', 'matches']


# ==================== keyboards/__init__.py ====================
"""T-League Bot - Keyboards package"""

from keyboards import user_kb, admin_kb

__all__ = ['user_kb', 'admin_kb']


# ==================== middlewares/__init__.py ====================
"""T-League Bot - Middlewares package"""

from middlewares.maintenance import MaintenanceMiddleware

__all__ = ['MaintenanceMiddleware']


# ==================== services/__init__.py ====================
"""T-League Bot - Services package"""

from services.tournament import TournamentService
from services.rating import RatingService
from services.records import RecordsService
from services.schedule import ScheduleService
from services.notifications import NotificationService

__all__ = [
    'TournamentService',
    'RatingService',
    'RecordsService',
    'ScheduleService',
    'NotificationService',
]


# ==================== states/__init__.py ====================
"""T-League Bot - FSM States package"""

from states.states import (
    TournamentCreation,
    MatchReport,
    AdminBroadcast,
    TesterAccess,
    TournamentSettings,
    RatingRecalculation
)

__all__ = [
    'TournamentCreation',
    'MatchReport',
    'AdminBroadcast',
    'TesterAccess',
    'TournamentSettings',
    'RatingRecalculation',
]


# ==================== utils/__init__.py ====================
"""T-League Bot - Utilities package"""

from utils.helpers import format_datetime, validate_score

__all__ = ['format_datetime', 'validate_score']