"""
T-League Bot - Хендлеры работы с матчами
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from database.models import Match, MatchStatus, User
from database.engine import async_session_maker
from services.schedule import ScheduleService
from services.rating import RatingService
from services.tournament import TournamentService
from services.notifications import NotificationService
from keyboards.user_kb import get_round_selection_keyboard, get_back_button
from states.states import MatchReport
from datetime import datetime

router = Router()

# ================== ВНЕСЕНИЕ РЕЗУЛЬТАТА ==================

@router.callback_query(F.data.startswith("report_match_"))
async def start_match_report(callback: CallbackQuery):
    """Начало процесса внесения результата - выбор тура"""
    tournament_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    async with async_session_maker() as session:
        # Получение туров с установленным дедлайном
        rounds = await ScheduleService.get_rounds_with_deadline(session, tournament_id)
        
        if not rounds:
            await callback.answer(
                "В этом турнире пока нет туров с установленным дедлайном.",
                show_alert=True
            )
            return
        
        text = (
            "⚔️ <b>Внести результат</b>\n\n"
            "Выберите тур, в котором хотите внести результат:"
        )
        
        keyboard = get_round_selection_keyboard(tournament_id, rounds)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

@router.callback_query(F.data.startswith("select_round_"))
async def select_round_for_report(callback: CallbackQuery, state: FSMContext):
    """Выбран тур для внесения результата"""
    parts = callback.data.split("_")
    tournament_id = int(parts[2])
    round_number = int(parts[3])
    user_id = callback.from_user.id
    
    async with async_session_maker() as session:
        # Поиск матча пользователя в этом туре
        match = await ScheduleService.get_user_matches_in_round(
            session, user_id, tournament_id, round_number
        )
        
        if not match:
            await callback.answer(
                "У вас нет матча в этом туре или результат уже внесён.",
                show_alert=True
            )
            return
        
        # Получение информации о сопернике
        opponent_id = match.player2_id if match.player1_id == user_id else match.player1_id
        opponent_result = await session.execute(
            select(User).where(User.id == opponent_id)
        )
        opponent = opponent_result.scalar_one()
        opponent_name = f"@{opponent.username}" if opponent.username else opponent.full_name
        
        # Дедлайн
        deadline_msk = ScheduleService.utc_to_msk(match.deadline)
        deadline_str = deadline_msk.strftime("%d.%m.%Y %H:%M")
        
        text = (
            f"⚔️ <b>Тур {round_number}</b>\n\n"
            f"Ваш соперник: {opponent_name}\n"
            f"⏰ Дедлайн: {deadline_str} МСК\n\n"
            f"Введите счёт матча в формате:\n"
            f"<code>ВашиГолы:ГолыСоперника</code>\n\n"
            f"Например: <code>3:2</code>"
        )
        
        # Сохраняем ID матча в состояние
        await state.update_data(match_id=match.id)
        await state.set_state(MatchReport.enter_score)
        
        await callback.message.edit_text(text, parse_mode="HTML")
        await callback.answer()

@router.message(MatchReport.enter_score)
async def enter_match_score(message: Message, state: FSMContext, bot):
    """Ввод счёта матча"""
    try:
        # Парсинг счёта
        score_parts = message.text.strip().split(":")
        if len(score_parts) != 2:
            raise ValueError
        
        score1 = int(score_parts[0])
        score2 = int(score_parts[1])
        
        if score1 < 0 or score2 < 0:
            raise ValueError
        
        data = await state.get_data()
        match_id = data.get("match_id")
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(Match).where(Match.id == match_id)
            )
            match = result.scalar_one()
            
            # Определение, кто играл первым
            if match.player1_id == message.from_user.id:
                match.player1_score = score1
                match.player2_score = score2
                opponent_id = match.player2_id
            else:
                match.player1_score = score2
                match.player2_score = score1
                opponent_id = match.player1_id
            
            match.status = MatchStatus.PENDING
            match.reported_by = message.from_user.id
            match.played_at = datetime.utcnow()
            
            await session.commit()
            
            # Уведомление сопернику
            await NotificationService.notify_match_confirmation_request(
                bot, session, match, opponent_id
            )
        
        await message.answer(
            "✅ Результат внесён!\n"
            "Ожидайте подтверждения от соперника.",
            parse_mode="HTML"
        )
        await state.clear()
        
    except (ValueError, IndexError):
        await message.answer(
            "❌ Неверный формат счёта!\n"
            "Используйте формат: <code>Ваши:Соперника</code>\n"
            "Например: <code>3:2</code>",
            parse_mode="HTML"
        )

# ================== ПОДТВЕРЖДЕНИЕ РЕЗУЛЬТАТА ==================

@router.callback_query(F.data.startswith("confirm_match_"))
async def confirm_match_result(callback: CallbackQuery, bot):
    """Подтверждение результата матча"""
    match_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(Match).where(Match.id == match_id)
        )
        match = result.scalar_one_or_none()
        
        if not match or match.status != MatchStatus.PENDING:
            await callback.answer("Матч не найден или уже обработан.", show_alert=True)
            return
        
        # Подтверждение матча
        match.status = MatchStatus.CONFIRMED
        match.confirmed_at = datetime.utcnow()
        
        # Обновление статистики турнира
        if match.player1_score > match.player2_score:
            await TournamentService.update_participant_stats(
                session, match.tournament_id, match.player1_id,
                "win", match.player1_score, match.player2_score
            )
            await TournamentService.update_participant_stats(
                session, match.tournament_id, match.player2_id,
                "loss", match.player2_score, match.player1_score
            )
        elif match.player1_score < match.player2_score:
            await TournamentService.update_participant_stats(
                session, match.tournament_id, match.player1_id,
                "loss", match.player1_score, match.player2_score
            )
            await TournamentService.update_participant_stats(
                session, match.tournament_id, match.player2_id,
                "win", match.player2_score, match.player1_score
            )
        else:
            await TournamentService.update_participant_stats(
                session, match.tournament_id, match.player1_id,
                "draw", match.player1_score, match.player2_score
            )
            await TournamentService.update_participant_stats(
                session, match.tournament_id, match.player2_id,
                "draw", match.player2_score, match.player1_score
            )
        
        # Обновление рейтинга
        await RatingService.update_match_stats(session, match)
        
        await session.commit()
        
        # Уведомления
        await NotificationService.notify_match_confirmed(bot, session, match)
        
        await callback.message.edit_text(
            "✅ <b>Результат подтверждён!</b>\n\n"
            f"Счёт: {match.player1_score}:{match.player2_score}\n"
            "Рейтинг обновлён.",
            parse_mode="HTML"
        )
        await callback.answer("Результат подтверждён!", show_alert=True)

@router.callback_query(F.data.startswith("dispute_match_"))
async def dispute_match_result(callback: CallbackQuery, bot):
    """Оспаривание результата матча"""
    match_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(Match).where(Match.id == match_id)
        )
        match = result.scalar_one_or_none()
        
        if not match or match.status != MatchStatus.PENDING:
            await callback.answer("Матч не найден или уже обработан.", show_alert=True)
            return
        
        # Оспаривание
        match.status = MatchStatus.DISPUTED
        await session.commit()
        
        # Уведомление администраторов
        from config import config
        await NotificationService.notify_match_disputed(
            bot, session, match, config.ADMIN_IDS
        )
        
        await callback.message.edit_text(
            "⚠️ <b>Результат оспорен</b>\n\n"
            "Администратор рассмотрит вашу жалобу.",
            parse_mode="HTML"
        )
        await callback.answer("Результат оспорен. Администратор будет уведомлён.", show_alert=True)

# ================== ИСТОРИЯ МАТЧЕЙ ==================

@router.callback_query(F.data.startswith("profile_history_"))
async def show_match_history(callback: CallbackQuery):
    """История матчей пользователя"""
    user_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        matches = await ScheduleService.get_user_matches(
            session, user_id, status=MatchStatus.CONFIRMED
        )
        
        if not matches:
            text = "📜 <b>История матчей</b>\n\nУ этого игрока пока нет завершённых матчей."
        else:
            text = "📜 <b>История матчей</b>\n\n"
            
            for match in matches[:15]:  # Последние 15 матчей
                opponent_id = match.player2_id if match.player1_id == user_id else match.player1_id
                opponent_result = await session.execute(
                    select(User).where(User.id == opponent_id)
                )
                opponent = opponent_result.scalar_one()
                opponent_name = f"@{opponent.username}" if opponent.username else opponent.full_name
                
                # Определение результата
                if match.player1_id == user_id:
                    my_score = match.player1_score
                    opp_score = match.player2_score
                else:
                    my_score = match.player2_score
                    opp_score = match.player1_score
                
                if my_score > opp_score:
                    result_emoji = "✅"
                elif my_score < opp_score:
                    result_emoji = "❌"
                else:
                    result_emoji = "➖"
                
                date_str = match.confirmed_at.strftime("%d.%m")
                text += f"{result_emoji} vs {opponent_name} - {my_score}:{opp_score} ({date_str})\n"
        
        keyboard = get_back_button(f"profile_{user_id}")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

@router.callback_query(F.data.startswith("profile_stats_"))
async def show_profile_stats(callback: CallbackQuery):
    """Подробная статистика пользователя"""
    user_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one()
        
        winrate = 0
        if user.matches_played > 0:
            winrate = (user.wins / user.matches_played) * 100
        
        text = (
            f"📊 <b>Статистика игрока</b>\n\n"
            f"<b>{user.full_name}</b>\n\n"
            f"🏆 Рейтинг: <b>{user.rating}</b>\n\n"
            f"<b>Матчи:</b>\n"
            f"├ Всего: {user.matches_played}\n"
            f"├ Победы: {user.wins}\n"
            f"├ Ничьи: {user.draws}\n"
            f"└ Поражения: {user.losses}\n\n"
            f"📈 Winrate: {winrate:.1f}%\n"
        )
        
        if user.current_streak > 0:
            text += f"🔥 Серия побед: {user.current_streak}\n"
        elif user.current_streak < 0:
            text += f"❄️ Серия поражений: {abs(user.current_streak)}\n"
        
        keyboard = get_back_button(f"profile_{user_id}")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()