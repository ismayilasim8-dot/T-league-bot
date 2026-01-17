"""
T-League Bot - FSM состояния
"""
from aiogram.fsm.state import State, StatesGroup

class TournamentCreation(StatesGroup):
    """Создание турнира"""
    name = State()
    description = State()
    format = State()
    max_participants = State()

class MatchReport(StatesGroup):
    """Внесение результата матча"""
    enter_score = State()

class AdminBroadcast(StatesGroup):
    """Массовая рассылка"""
    message = State()
    confirm = State()

class TesterAccess(StatesGroup):
    """Доступ для тестеров"""
    enter_code = State()

class DeadlineSettings(StatesGroup):
    """Установка дедлайна"""
    enter_time = State()

class RatingRecalculation(StatesGroup):
    """Пересчёт рейтинга"""
    confirm = State()

class PlayerSearch(StatesGroup):
    """Поиск игрока"""
    username = State()