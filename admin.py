"""
T-League Bot - Хендлеры администратора (НОВАЯ ВЕРСИЯ)
ВАЖНО: Этот файл ПОЛНОСТЬЮ заменяет старый handlers/admin.py
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update
from database.models import (
    User, Tournament, SystemSettings, AdminLog, 
    TournamentFormat, TournamentStatus
)
from database.engine import async_session_maker
from keyboards.admin_kb import (
    get_admin_panel_keyboard, get_tournament_management_keyboard,
    get_tournament_admin_keyboard, get_tournament_format_keyboard,
    get_broadcast_confirm_keyboard, get_export_keyboard,
    get_confirmation_keyboard, get_round_selection_for_deadline
)
from services.tournament import TournamentService
from services.rating import RatingService
from services.records import RecordsService
from services.schedule import ScheduleService
from services.notifications import NotificationService
from states.states import (
    TournamentCreation, AdminBroadcast, 
    DeadlineSettings, RatingRecalculation
)
from config import config
from datetime import datetime
import csv
import io

router = Router()

# Фильтр для проверки прав администратора
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

# ================== ЛОГИРОВАНИЕ ==================

async def log_admin_action(admin_id: int, action: str, details: str = None):
    """Логирование действия администратора"""
    async with async_session_maker() as session:
        log = AdminLog(
            admin_id=admin_id,
            action=action,
            details=details
        )
        session.add(log)
        await session.commit()

# ================== АДМИН-ПАНЕЛЬ ==================

@router.callback_query(F.data == "admin_panel")
async def show_admin_panel_callback(callback: CallbackQuery):
    """Админ-панель через callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == "maintenance_mode")
        )
        setting = result.scalar_one()
        maintenance_mode = setting.value == "true"
    
    text = (
        "⚙️ <b>Панель администратора</b>\n\n"
        "Выберите действие:"
    )
    
    keyboard = get_admin_panel_keyboard(maintenance_mode)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ================== ТЕХОБСЛУЖИВАНИЕ ==================

@router.callback_query(F.data == "admin_toggle_maintenance")
async def toggle_maintenance(callback: CallbackQuery):
    """Включение/выключение режима техобслуживания"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == "maintenance_mode")
        )
        setting = result.scalar_one()
        
        # Переключение
        new_value = "false" if setting.value == "true" else "true"
        setting.value = new_value
        setting.updated_at = datetime.utcnow()
        await session.commit()
        
        # Логирование
        action = "Включение техобслуживания" if new_value == "true" else "Выключение техобслуживания"
        await log_admin_action(callback.from_user.id, action)
    
    status = "включено" if new_value == "true" else "выключено"
    await callback.answer(f"✅ Техобслуживание {status}!", show_alert=True)
    
    # Обновление клавиатуры
    maintenance_mode = new_value == "true"
    keyboard = get_admin_panel_keyboard(maintenance_mode)
    await callback.message.edit_reply_markup(reply_markup=keyboard)

# ================== СОЗДАНИЕ ТУРНИРА ==================

@router.callback_query(F.data == "admin_create_tournament")
async def start_tournament_creation(callback: CallbackQuery, state: FSMContext):
    """Начало создания турнира"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await state.set_state(TournamentCreation.name)
    await callback.message.answer(
        "➕ <b>Создание турнира</b>\n\n"
        "Введите название турнира:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(TournamentCreation.name)
async def tournament_name_entered(message: Message, state: FSMContext):
    """Ввод названия турнира"""
    await state.update_data(name=message.text)
    await state.set_state(TournamentCreation.description)
    await message.answer(
        "📝 Введите описание турнира\n"
        "(или отправьте '-' чтобы пропустить):"
    )

@router.message(TournamentCreation.description)
async def tournament_description_entered(message: Message, state: FSMContext):
    """Ввод описания турнира"""
    description = None if message.text == "-" else message.text
    await state.update_data(description=description)
    await state.set_state(TournamentCreation.format)
    
    keyboard = get_tournament_format_keyboard()
    await message.answer(
        "🎯 Выберите формат турнира:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("format_"))
async def tournament_format_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор формата турнира"""
    format_name = callback.data.split("_", 1)[1]
    
    format_map = {
        "round_robin": TournamentFormat.ROUND_ROBIN,
        "playoff": TournamentFormat.PLAYOFF,
        "swiss": TournamentFormat.SWISS,
        "group_playoff": TournamentFormat.GROUP_PLAYOFF
    }
    
    tournament_format = format_map.get(format_name, TournamentFormat.ROUND_ROBIN)
    await state.update_data(format=tournament_format)
    await state.set_state(TournamentCreation.max_participants)
    
    await callback.message.answer(
        "👥 Введите максимальное количество участников\n"
        "(или отправьте '-' для неограниченного):"
    )
    await callback.answer()

@router.message(TournamentCreation.max_participants)
async def tournament_max_participants_entered(message: Message, state: FSMContext):
    """Ввод максимального количества участников"""
    max_participants = None
    
    if message.text != "-":
        try:
            max_participants = int(message.text)
            if max_participants < 2:
                await message.answer("❌ Минимум 2 участника. Попробуйте снова:")
                return
        except ValueError:
            await message.answer("❌ Введите число или '-'. Попробуйте снова:")
            return
    
    # Создание турнира
    data = await state.get_data()
    
    async with async_session_maker() as session:
        tournament = await TournamentService.create_tournament(
            session,
            name=data['name'],
            description=data.get('description'),
            format=data['format'],
            max_participants=max_participants
        )
        
        # Логирование
        await log_admin_action(
            message.from_user.id,
            "Создание турнира",
            f"Турнир: {tournament.name} (ID: {tournament.id})"
        )
    
    format_names = {
        TournamentFormat.ROUND_ROBIN: "Круговой",
        TournamentFormat.PLAYOFF: "Плей-офф",
        TournamentFormat.SWISS: "Швейцарская",
        TournamentFormat.GROUP_PLAYOFF: "Групповой + плей-офф"
    }
    
    await message.answer(
        f"✅ <b>Турнир создан!</b>\n\n"
        f"🏆 Название: {tournament.name}\n"
        f"📊 Формат: {format_names.get(tournament.format)}\n"
        f"👥 Макс. участников: {max_participants or 'Не ограничено'}\n"
        f"🔒 Регистрация: Закрыта (откройте в управлении)\n\n"
        f"ID турнира: {tournament.id}",
        parse_mode="HTML"
    )
    
    await state.clear()

# ================== УПРАВЛЕНИЕ ТУРНИРАМИ ==================

@router.callback_query(F.data == "admin_manage_tournaments")
async def show_tournament_management(callback: CallbackQuery):
    """Управление турнирами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with async_session_maker() as session:
        tournaments = await TournamentService.get_all_tournaments(session)
    
    text = "⚙️ <b>Управление турнирами</b>\n\nВыберите турнир:"
    keyboard = get_tournament_management_keyboard(tournaments)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin_tournament_"))
async def show_tournament_admin(callback: CallbackQuery):
    """Управление конкретным турниром"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    tournament_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        tournament = await TournamentService.get_tournament(session, tournament_id)
        
        if not tournament:
            await callback.answer("Турнир не найден", show_alert=True)
            return
        
        participants = await TournamentService.get_participants(session, tournament_id)
        
        reg_status = "Открыта" if tournament.registration_open else "Закрыта"
        draw_status = "Проведена" if tournament.draw_completed else "Не проведена"
        
        text = (
            f"⚙️ <b>{tournament.name}</b>\n\n"
            f"📊 Статус: {tournament.status}\n"
            f"🔓 Регистрация: {reg_status}\n"
            f"🎲 Жеребьёвка: {draw_status}\n"
            f"👥 Участников: {len(participants)}\n"
        )
        
        if tournament.total_rounds > 0:
            text += f"🔄 Всего туров: {tournament.total_rounds}\n"
        
        text += "\nВыберите действие:"
        
        keyboard = get_tournament_admin_keyboard(
            tournament_id, tournament.status, 
            tournament.registration_open, tournament.draw_completed
        )
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

# ================== РЕГИСТРАЦИЯ ==================

@router.callback_query(F.data.startswith("admin_toggle_reg_"))
async def toggle_registration(callback: CallbackQuery):
    """Открыть/закрыть регистрацию"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    tournament_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        success = await TournamentService.toggle_registration(session, tournament_id)
        
        if success:
            tournament = await TournamentService.get_tournament(session, tournament_id)
            status = "открыта" if tournament.registration_open else "закрыта"
            
            await log_admin_action(
                callback.from_user.id,
                f"Регистрация {status}",
                f"Турнир ID: {tournament_id}"
            )
            
            await callback.answer(f"✅ Регистрация {status}!", show_alert=True)
            # Обновляем информацию о турнире
            await show_tournament_admin(callback)
        else:
            await callback.answer("❌ Не удалось изменить статус регистрации.", show_alert=True)

# ================== ЖЕРЕБЬЁВКА ==================

@router.callback_query(F.data.startswith("admin_draw_"))
async def conduct_draw(callback: CallbackQuery, bot):
    """Провести жеребьёвку турнира"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    tournament_id = int(callback.data.split("_")[2])
    
    await callback.message.edit_text("🎲 Проведение жеребьёвки...", parse_mode="HTML")
    
    async with async_session_maker() as session:
        participants = await TournamentService.get_participants(session, tournament_id)
        
        if len(participants) < 2:
            await callback.message.edit_text(
                "❌ <b>Недостаточно участников!</b>\n\n"
                "Для проведения жеребьёвки нужно минимум 2 участника.",
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        success = await TournamentService.conduct_draw(session, tournament_id)
        
        if success:
            tournament = await TournamentService.get_tournament(session, tournament_id)
            
            await log_admin_action(
                callback.from_user.id,
                "Проведение жеребьёвки",
                f"Турнир ID: {tournament_id}, Туров: {tournament.total_rounds}"
            )
            
            await callback.message.edit_text(
                f"✅ <b>Жеребьёвка проведена!</b>\n\n"
                f"👥 Участников: {len(participants)}\n"
                f"🔄 Создано туров: {tournament.total_rounds}\n\n"
                f"Теперь вы можете запустить турнир.",
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "❌ Не удалось провести жеребьёвку.",
                parse_mode="HTML"
            )
    
    await callback.answer()

# ================== ЗАПУСК И ЗАВЕРШЕНИЕ ТУРНИРА ==================

@router.callback_query(F.data.startswith("admin_start_tournament_"))
async def start_tournament_admin(callback: CallbackQuery):
    """Запуск турнира"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    tournament_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        success = await TournamentService.start_tournament(session, tournament_id)
        
        if success:
            await log_admin_action(
                callback.from_user.id,
                "Запуск турнира",
                f"Турнир ID: {tournament_id}"
            )
            await callback.answer("✅ Турнир запущен!", show_alert=True)
            await show_tournament_admin(callback)
        else:
            await callback.answer(
                "❌ Не удалось запустить турнир. Проверьте, проведена ли жеребьёвка.",
                show_alert=True
            )

@router.callback_query(F.data.startswith("admin_finish_tournament_"))
async def finish_tournament_admin(callback: CallbackQuery, bot):
    """Завершение турнира"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    tournament_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        success = await TournamentService.finish_tournament(session, tournament_id)
        
        if success:
            # Расчёт рекордов
            await RecordsService.calculate_tournament_records(session, tournament_id)
            
            await log_admin_action(
                callback.from_user.id,
                "Завершение турнира",
                f"Турнир ID: {tournament_id}"
            )
            await callback.answer("✅ Турнир завершён! Рекорды рассчитаны.", show_alert=True)
            await show_tournament_admin(callback)
        else:
            await callback.answer("❌ Не удалось завершить турнир.", show_alert=True)
            """
Продолжение handlers/admin.py - Часть 2
ДОБАВЬТЕ ЭТОТ КОД В КОНЕЦ ФАЙЛА admin.py
"""

# ================== УСТАНОВКА ДЕДЛАЙНА ==================

@router.callback_query(F.data.startswith("admin_set_deadline_"))
async def start_deadline_setting(callback: CallbackQuery):
    """Начало установки дедлайна - выбор тура"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    tournament_id = int(callback.data.split("_")[3])
    
    async with async_session_maker() as session:
        # Получение информации о турах
        rounds_info = await ScheduleService.get_rounds_info(session, tournament_id)
        
        if not rounds_info:
            await callback.answer(
                "В этом турнире пока нет туров.",
                show_alert=True
            )
            return
        
        text = (
            "⏰ <b>Установка дедлайна</b>\n\n"
            "Выберите тур, для которого хотите установить дедлайн:"
        )
        
        keyboard = get_round_selection_for_deadline(tournament_id, rounds_info)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

@router.callback_query(F.data.startswith("admin_deadline_"))
async def select_round_for_deadline(callback: CallbackQuery, state: FSMContext):
    """Выбран тур для установки дедлайна"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    parts = callback.data.split("_")
    tournament_id = int(parts[2])
    round_number = int(parts[3])
    
    # Сохраняем в состояние
    await state.update_data(
        tournament_id=tournament_id,
        round_number=round_number
    )
    await state.set_state(DeadlineSettings.enter_time)
    
    text = (
        f"⏰ <b>Установка дедлайна для тура {round_number}</b>\n\n"
        "Введите дедлайн в формате <b>МСК</b>:\n"
        "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
        "Например: <code>31.12.2025 23:59</code>\n\n"
        "<i>Время указывается по Московскому часовому поясу (МСК, UTC+3)</i>"
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

@router.message(DeadlineSettings.enter_time)
async def set_deadline_time(message: Message, state: FSMContext, bot):
    """Установка времени дедлайна"""
    try:
        # Парсинг времени МСК
        deadline_msk = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        
        # Проверка, что время в будущем
        now_msk = ScheduleService.utc_to_msk(datetime.utcnow())
        if deadline_msk <= now_msk:
            await message.answer(
                "❌ Дедлайн должен быть в будущем!\n"
                "Попробуйте снова:"
            )
            return
        
        data = await state.get_data()
        tournament_id = data['tournament_id']
        round_number = data['round_number']
        
        async with async_session_maker() as session:
            # Установка дедлайна
            count = await ScheduleService.set_deadline_for_round(
                session, tournament_id, round_number, deadline_msk
            )
            
            if count > 0:
                # Получение участников тура для уведомления
                matches_data = await ScheduleService.get_tournament_matches(
                    session, tournament_id, round_number
                )
                
                # Отправка уведомлений
                notified = set()
                for match, player1, player2 in matches_data:
                    for player in [player1, player2]:
                        if player.id not in notified:
                            try:
                                await bot.send_message(
                                    player.id,
                                    f"⏰ <b>Установлен дедлайн!</b>\n\n"
                                    f"Тур {round_number}\n"
                                    f"📅 До: {deadline_msk.strftime('%d.%m.%Y %H:%M')} МСК\n\n"
                                    f"Не забудьте сыграть матч и внести результат!",
                                    parse_mode="HTML"
                                )
                                notified.add(player.id)
                            except:
                                pass
                
                await log_admin_action(
                    message.from_user.id,
                    "Установка дедлайна",
                    f"Турнир ID: {tournament_id}, Тур: {round_number}, До: {deadline_msk.strftime('%d.%m.%Y %H:%M')} МСК"
                )
                
                await message.answer(
                    f"✅ <b>Дедлайн установлен!</b>\n\n"
                    f"🔄 Тур: {round_number}\n"
                    f"⏰ До: {deadline_msk.strftime('%d.%m.%Y %H:%M')} МСК\n"
                    f"⚔️ Матчей: {count}\n"
                    f"📢 Уведомлено участников: {len(notified)}",
                    parse_mode="HTML"
                )
            else:
                await message.answer("❌ Не удалось установить дедлайн.")
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты/времени!\n"
            "Используйте: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
            "Например: <code>31.12.2025 23:59</code>\n\n"
            "Попробуйте снова:",
            parse_mode="HTML"
        )

# ================== МАССОВАЯ РАССЫЛКА ==================

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начало массовой рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await state.set_state(AdminBroadcast.message)
    await callback.message.answer(
        "📢 <b>Массовая рассылка</b>\n\n"
        "Введите сообщение для отправки всем пользователям:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminBroadcast.message)
async def broadcast_message_entered(message: Message, state: FSMContext):
    """Ввод сообщения для рассылки"""
    await state.update_data(message_text=message.text)
    await state.set_state(AdminBroadcast.confirm)
    
    keyboard = get_broadcast_confirm_keyboard()
    await message.answer(
        f"📢 <b>Подтверждение рассылки</b>\n\n"
        f"Сообщение:\n{message.text}\n\n"
        "Отправить всем пользователям?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot):
    """Подтверждение и выполнение рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    data = await state.get_data()
    message_text = data['message_text']
    
    await callback.message.edit_text("📢 Рассылка началась...", parse_mode="HTML")
    
    async with async_session_maker() as session:
        success, fail = await NotificationService.broadcast_message(
            bot, session, message_text
        )
    
    await log_admin_action(
        callback.from_user.id,
        "Массовая рассылка",
        f"Успешно: {success}, Неудачно: {fail}"
    )
    
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Отправлено: {success}\n"
        f"Не отправлено: {fail}",
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer()

# ================== ПЕРЕСЧЁТ РЕЙТИНГОВ ==================

@router.callback_query(F.data == "admin_recalculate_ratings")
async def start_rating_recalculation(callback: CallbackQuery, state: FSMContext):
    """Начало пересчёта рейтингов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await state.set_state(RatingRecalculation.confirm)
    
    keyboard = get_confirmation_keyboard("recalc_ratings")
    await callback.message.answer(
        "🔄 <b>Пересчёт рейтингов</b>\n\n"
        "⚠️ Это действие пересчитает все рейтинги на основе подтверждённых матчей.\n"
        "Текущие рейтинги будут сброшены.\n\n"
        "Продолжить?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_recalc_ratings")
async def confirm_rating_recalculation(callback: CallbackQuery, state: FSMContext):
    """Подтверждение пересчёта рейтингов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await callback.message.edit_text("🔄 Пересчёт рейтингов...", parse_mode="HTML")
    
    async with async_session_maker() as session:
        await RatingService.recalculate_all_ratings(session)
    
    await log_admin_action(
        callback.from_user.id,
        "Пересчёт рейтингов",
        "Все рейтинги пересчитаны"
    )
    
    await callback.message.edit_text(
        "✅ <b>Рейтинги пересчитаны!</b>\n\n"
        "Все рейтинги обновлены на основе подтверждённых матчей.",
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_recalc_ratings")
async def cancel_rating_recalculation(callback: CallbackQuery, state: FSMContext):
    """Отмена пересчёта рейтингов"""
    await callback.message.delete()
    await callback.answer("Отменено")
    await state.clear()

# ================== ПЕРЕСЧЁТ РЕКОРДОВ ==================

@router.callback_query(F.data == "admin_recalculate_records")
async def recalculate_all_records(callback: CallbackQuery):
    """Пересчёт рекордов всех завершённых турниров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await callback.message.edit_text("🔄 Пересчёт рекордов...", parse_mode="HTML")
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(Tournament).where(Tournament.status == TournamentStatus.FINISHED)
        )
        tournaments = result.scalars().all()
        
        count = 0
        for tournament in tournaments:
            await RecordsService.calculate_tournament_records(session, tournament.id)
            count += 1
    
    await log_admin_action(
        callback.from_user.id,
        "Пересчёт рекордов",
        f"Пересчитано турниров: {count}"
    )
    
    await callback.message.edit_text(
        f"✅ <b>Рекорды пересчитаны!</b>\n\n"
        f"Обработано турниров: {count}",
        parse_mode="HTML"
    )
    await callback.answer()

# ================== ЭКСПОРТ ДАННЫХ ==================

@router.callback_query(F.data == "admin_export")
async def show_export_menu(callback: CallbackQuery):
    """Меню экспорта"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    text = "📊 <b>Экспорт данных</b>\n\nВыберите тип данных для экспорта:"
    keyboard = get_export_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "export_rating")
async def export_rating(callback: CallbackQuery):
    """Экспорт рейтинга в CSV"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await callback.answer("📊 Формирование файла...", show_alert=False)
    
    async with async_session_maker() as session:
        players = await RatingService.get_all_players_ranked(session)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Позиция', 'ID', 'Username', 'Имя', 'Рейтинг',
            'Матчи', 'Победы', 'Ничьи', 'Поражения', 'Winrate', 'Серия'
        ])
        
        for i, player in enumerate(players, 1):
            winrate = (player.wins / player.matches_played * 100) if player.matches_played > 0 else 0
            writer.writerow([
                i,
                player.id,
                player.username or '',
                player.full_name,
                player.rating,
                player.matches_played,
                player.wins,
                player.draws,
                player.losses,
                f"{winrate:.1f}%",
                player.current_streak
            ])
        
        output.seek(0)
        file_content = output.getvalue().encode('utf-8-sig')
        
        from aiogram.types import BufferedInputFile
        file = BufferedInputFile(file_content, filename="rating_export.csv")
        
        await callback.message.answer_document(
            file,
            caption="📊 Экспорт рейтинга игроков"
        )
        
        await log_admin_action(
            callback.from_user.id,
            "Экспорт рейтинга",
            f"Экспортировано игроков: {len(players)}"
        )
    
    await callback.answer("✅ Файл отправлен!")

# ================== ЛОГИ ==================

@router.callback_query(F.data == "admin_logs")
async def show_admin_logs(callback: CallbackQuery):
    """Просмотр логов действий администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(AdminLog, User)
            .join(User, AdminLog.admin_id == User.id)
            .order_by(AdminLog.created_at.desc())
            .limit(20)
        )
        logs = result.all()
        
        if not logs:
            text = "📝 <b>Логи действий</b>\n\nЛогов пока нет."
        else:
            text = "📝 <b>Последние 20 действий</b>\n\n"
            
            for log, admin in logs:
                admin_name = admin.username or admin.full_name
                date_str = log.created_at.strftime("%d.%m %H:%M")
                
                text += f"• {date_str} | {admin_name}\n  {log.action}\n"
                if log.details:
                    text += f"  {log.details}\n"
                text += "\n"
        
        from keyboards.user_kb import get_back_button
        keyboard = get_back_button("admin_panel")
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

# ================== ПРОСМОТР УЧАСТНИКОВ ==================

@router.callback_query(F.data.startswith("admin_participants_"))
async def show_admin_participants(callback: CallbackQuery):
    """Просмотр участников турнира (для админа)"""
    tournament_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        participants = await TournamentService.get_participants(session, tournament_id)
        
        text = "👥 <b>Участники турнира</b>\n\n"
        
        if not participants:
            text += "Участников пока нет."
        else:
            for i, (participant, user) in enumerate(participants, 1):
                username = f"@{user.username}" if user.username else user.full_name
                text += f"{i}. {username} (ID: {user.id})\n"
        
        from keyboards.user_kb import get_back_button
        keyboard = get_back_button(f"admin_tournament_{tournament_id}")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()