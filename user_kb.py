"""
T-League Bot - Клавиатуры пользователя
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config

def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню пользователя (inline)"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🏆 Турниры", callback_data="tournaments")
    kb.button(text="📊 Рейтинг игроков", callback_data="rating")
    kb.button(text="🛒 Маркетплейс", callback_data="marketplace")
    kb.button(text="🔍 Поиск игрока", callback_data="search_player")
    kb.button(text="🏅 Рекорды", callback_data="records_menu")
    kb.button(text="👤 Мой профиль", callback_data="my_profile")
    kb.button(text="ℹ️ О проекте", callback_data="about_project")
    kb.adjust(2, 1, 2, 2)
    return kb.as_markup()

def get_about_project_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела 'О проекте'"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Канал проекта", url=config.CHANNEL_URL)
    kb.button(text="👨‍💼 Менеджер", url=config.MANAGER_URL)
    kb.button(text="💬 Чат игроков", url=config.CHAT_URL)
    kb.button(text="📋 Правила", url=config.RULES_URL)
    kb.button(text="◀️ В главное меню", callback_data="main_menu")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

def get_tournaments_keyboard(tournaments: list) -> InlineKeyboardMarkup:
    """Клавиатура списка турниров"""
    kb = InlineKeyboardBuilder()
    
    for tournament in tournaments:
        status_emoji = "🟢" if tournament.status == "active" else "🔴" if tournament.status == "finished" else "🟡"
        kb.button(
            text=f"{status_emoji} {tournament.name}",
            callback_data=f"tournament_{tournament.id}"
        )
    
    if not tournaments:
        kb.button(text="Турниров пока нет", callback_data="no_action")
    
    kb.button(text="🔄 Обновить", callback_data="tournaments")
    kb.button(text="◀️ В главное меню", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def get_tournament_detail_keyboard(tournament_id: int, is_participant: bool, registration_open: bool, status: str) -> InlineKeyboardMarkup:
    """Клавиатура детального просмотра турнира"""
    kb = InlineKeyboardBuilder()
    
    kb.button(text="👥 Участники", callback_data=f"tournament_participants_{tournament_id}")
    kb.button(text="📊 Таблица", callback_data=f"tournament_table_{tournament_id}")
    kb.button(text="📅 Расписание", callback_data=f"tournament_schedule_{tournament_id}")
    
    # Кнопка регистрации/внесения результата
    if status == "registration":
        if is_participant:
            kb.button(text="✅ Вы зарегистрированы", callback_data="no_action")
        elif registration_open:
            kb.button(text="📝 Зарегистрироваться", callback_data=f"register_tournament_{tournament_id}")
        else:
            kb.button(text="🔒 Регистрация закрыта", callback_data="no_action")
    elif status == "active" and is_participant:
        kb.button(text="⚔️ Внести результат", callback_data=f"report_match_{tournament_id}")
    
    kb.button(text="◀️ К турнирам", callback_data="tournaments")
    kb.adjust(2, 1, 1, 1)
    return kb.as_markup()

def get_match_confirmation_keyboard(match_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения результата матча"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"confirm_match_{match_id}")
    kb.button(text="❌ Оспорить", callback_data=f"dispute_match_{match_id}")
    kb.adjust(2)
    return kb.as_markup()

def get_rating_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура рейтинга"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔝 Топ-10", callback_data="rating_top10")
    kb.button(text="📊 Полный рейтинг", callback_data="rating_full")
    kb.button(text="🔄 Обновить", callback_data="rating")
    kb.button(text="◀️ В главное меню", callback_data="main_menu")
    kb.adjust(2, 1, 1)
    return kb.as_markup()

def get_profile_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура профиля"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📜 История матчей", callback_data=f"profile_history_{user_id}")
    kb.button(text="📊 Статистика", callback_data=f"profile_stats_{user_id}")
    kb.button(text="🔄 Обновить", callback_data=f"profile_{user_id}")
    kb.button(text="◀️ В главное меню", callback_data="main_menu")
    kb.adjust(2, 1, 1)
    return kb.as_markup()

def get_records_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура меню рекордов"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🏆 Рекорды турниров", callback_data="records_tournaments")
    kb.button(text="◀️ В главное меню", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def get_tournament_records_keyboard(tournaments: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора турнира для рекордов"""
    kb = InlineKeyboardBuilder()
    
    for tournament in tournaments:
        kb.button(
            text=f"🏆 {tournament.name}",
            callback_data=f"records_tournament_{tournament.id}"
        )
    
    kb.button(text="◀️ Назад", callback_data="records_menu")
    kb.adjust(1)
    return kb.as_markup()

def get_back_button(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Простая кнопка 'Назад'"""
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data=callback_data)
    return kb.as_markup()

def get_round_selection_keyboard(tournament_id: int, rounds: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора тура для внесения результата"""
    kb = InlineKeyboardBuilder()
    
    for round_num in rounds:
        kb.button(
            text=f"Тур {round_num}",
            callback_data=f"select_round_{tournament_id}_{round_num}"
        )
    
    kb.button(text="❌ Отмена", callback_data=f"tournament_{tournament_id}")
    kb.adjust(2)
    return kb.as_markup()

def get_search_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены поиска"""
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="main_menu")
    return kb.as_markup()