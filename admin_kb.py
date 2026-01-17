"""
T-League Bot - Клавиатуры администратора
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_main_menu() -> InlineKeyboardMarkup:
    """Главное меню администратора (inline)"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🏆 Турниры", callback_data="tournaments")
    kb.button(text="📊 Рейтинг игроков", callback_data="rating")
    kb.button(text="🔍 Поиск игрока", callback_data="search_player")
    kb.button(text="🏅 Рекорды", callback_data="records_menu")
    kb.button(text="👤 Мой профиль", callback_data="my_profile")
    kb.button(text="⚙️ Админ-панель", callback_data="admin_panel")
    kb.button(text="ℹ️ О проекте", callback_data="about_project")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()

def get_admin_panel_keyboard(maintenance_mode: bool = False) -> InlineKeyboardMarkup:
    """Панель администратора"""
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать турнир", callback_data="admin_create_tournament")
    kb.button(text="⚙️ Управление турнирами", callback_data="admin_manage_tournaments")
    kb.button(text="📢 Массовая рассылка", callback_data="admin_broadcast")
    kb.button(text="🔄 Пересчёт рейтингов", callback_data="admin_recalculate_ratings")
    kb.button(text="🔄 Пересчёт рекордов", callback_data="admin_recalculate_records")
    kb.button(text="📊 Экспорт данных", callback_data="admin_export")
    
    # Кнопка техобслуживания
    maintenance_text = "🔓 Выключить ТО" if maintenance_mode else "🔒 Включить ТО"
    kb.button(text=maintenance_text, callback_data="admin_toggle_maintenance")
    
    kb.button(text="📝 Логи действий", callback_data="admin_logs")
    kb.button(text="◀️ В главное меню", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def get_tournament_management_keyboard(tournaments: list) -> InlineKeyboardMarkup:
    """Управление турнирами"""
    kb = InlineKeyboardBuilder()
    
    for tournament in tournaments:
        status_emoji = {
            "registration": "🟡",
            "active": "🟢",
            "finished": "🔴"
        }.get(tournament.status, "⚪")
        
        kb.button(
            text=f"{status_emoji} {tournament.name}",
            callback_data=f"admin_tournament_{tournament.id}"
        )
    
    kb.button(text="◀️ К админ-панели", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

def get_tournament_admin_keyboard(tournament_id: int, status: str, registration_open: bool, draw_completed: bool) -> InlineKeyboardMarkup:
    """Управление конкретным турниром"""
    kb = InlineKeyboardBuilder()
    
    if status == "registration":
        # Регистрация - управление регистрацией и жеребьёвка
        reg_text = "🔒 Закрыть регистрацию" if registration_open else "🔓 Открыть регистрацию"
        kb.button(text=reg_text, callback_data=f"admin_toggle_reg_{tournament_id}")
        
        if not draw_completed:
            kb.button(text="🎲 Провести жеребьёвку", callback_data=f"admin_draw_{tournament_id}")
        else:
            kb.button(text="✅ Жеребьёвка проведена", callback_data="no_action")
            kb.button(text="🚀 Запустить турнир", callback_data=f"admin_start_tournament_{tournament_id}")
            
    elif status == "active":
        kb.button(text="⏰ Установить дедлайн", callback_data=f"admin_set_deadline_{tournament_id}")
        kb.button(text="✅ Завершить турнир", callback_data=f"admin_finish_tournament_{tournament_id}")
    
    kb.button(text="👥 Участники", callback_data=f"admin_participants_{tournament_id}")
    kb.button(text="📊 Таблица", callback_data=f"tournament_table_{tournament_id}")
    kb.button(text="📅 Расписание", callback_data=f"tournament_schedule_{tournament_id}")
    kb.button(text="🗑️ Удалить турнир", callback_data=f"admin_delete_tournament_{tournament_id}")
    kb.button(text="◀️ К турнирам", callback_data="admin_manage_tournaments")
    kb.adjust(1)
    return kb.as_markup()

def get_tournament_format_keyboard() -> InlineKeyboardMarkup:
    """Выбор формата турнира"""
    kb = InlineKeyboardBuilder()
    kb.button(text="⚽ Круговой турнир", callback_data="format_round_robin")
    kb.button(text="🏆 Плей-офф", callback_data="format_playoff")
    kb.button(text="🎲 Швейцарская система", callback_data="format_swiss")
    kb.button(text="🔥 Групповой + плей-офф", callback_data="format_group_playoff")
    kb.button(text="❌ Отмена", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение рассылки"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Отправить всем", callback_data="broadcast_confirm")
    kb.button(text="❌ Отмена", callback_data="admin_panel")
    kb.adjust(2)
    return kb.as_markup()

def get_export_keyboard() -> InlineKeyboardMarkup:
    """Экспорт данных"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Экспорт рейтинга", callback_data="export_rating")
    kb.button(text="🏆 Экспорт турниров", callback_data="export_tournaments")
    kb.button(text="👥 Экспорт участников", callback_data="export_users")
    kb.button(text="⚔️ Экспорт матчей", callback_data="export_matches")
    kb.button(text="◀️ К админ-панели", callback_data="admin_panel")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

def get_confirmation_keyboard(action: str, item_id: int = None) -> InlineKeyboardMarkup:
    """Универсальная клавиатура подтверждения"""
    kb = InlineKeyboardBuilder()
    
    callback_yes = f"confirm_{action}"
    callback_no = f"cancel_{action}"
    
    if item_id:
        callback_yes += f"_{item_id}"
        callback_no += f"_{item_id}"
    
    kb.button(text="✅ Подтвердить", callback_data=callback_yes)
    kb.button(text="❌ Отмена", callback_data=callback_no)
    kb.adjust(2)
    return kb.as_markup()

def get_round_selection_for_deadline(tournament_id: int, rounds: list) -> InlineKeyboardMarkup:
    """Выбор тура для установки дедлайна"""
    kb = InlineKeyboardBuilder()
    
    for round_info in rounds:
        round_num = round_info['round_number']
        has_deadline = round_info['has_deadline']
        
        if has_deadline:
            kb.button(
                text=f"✅ Тур {round_num} (установлен)",
                callback_data=f"admin_deadline_{tournament_id}_{round_num}"
            )
        else:
            kb.button(
                text=f"⏰ Тур {round_num}",
                callback_data=f"admin_deadline_{tournament_id}_{round_num}"
            )
    
    kb.button(text="❌ Отмена", callback_data=f"admin_tournament_{tournament_id}")
    kb.adjust(2)
    return kb.as_markup()