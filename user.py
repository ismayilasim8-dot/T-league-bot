"""
T-League Bot — User handlers (FULL REWRITE)
"""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.engine import async_session_maker
from database.models import User, Tournament

from keyboards.user_kb import (
    get_main_menu,
    get_about_project_keyboard,
    get_tournaments_keyboard,
    get_tournament_detail_keyboard,
    get_rating_keyboard,
    get_profile_keyboard,
    get_records_keyboard,
    get_tournament_records_keyboard,
    get_search_cancel_keyboard,
    get_back_button
)
from keyboards.admin_kb import get_admin_main_menu

from services.tournament import TournamentService
from services.rating import RatingService
from services.records import RecordsService
from services.schedule import ScheduleService

from states.states import PlayerSearch
from config import config

router = Router()

# ======================================================
# START / MAIN MENU
# ======================================================

@router.message(CommandStart())
async def start_cmd(message: Message):
    async with async_session_maker() as session:
        user = await session.get(User, message.from_user.id)

        if not user:
            user = User(
                id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                is_admin=message.from_user.id in config.ADMIN_IDS
            )
            session.add(user)
            await session.commit()

        text = (
            f"👋 <b>{user.full_name}</b>\n\n"
            f"🏆 <b>{config.PROJECT_NAME}</b>\n"
            f"{config.PROJECT_DESCRIPTION}"
        )

        kb = get_admin_main_menu() if user.is_admin else get_main_menu()
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    async with async_session_maker() as session:
        user = await session.get(User, callback.from_user.id)
        kb = get_admin_main_menu() if user.is_admin else get_main_menu()

    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()

# ======================================================
# TOURNAMENTS
# ======================================================

@router.callback_query(F.data == "tournaments")
async def tournaments(callback: CallbackQuery):
    async with async_session_maker() as session:
        tournaments = await TournamentService.get_all_tournaments(session)

    text = "🏆 <b>Турниры</b>\n\n"
    text += "Выберите турнир:" if tournaments else "Турниров пока нет"

    await callback.message.edit_text(
        text,
        reply_markup=get_tournaments_keyboard(tournaments),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tournament_"))
async def tournament_detail(callback: CallbackQuery):
    tournament_id = int(callback.data.split("_")[1])

    async with async_session_maker() as session:
        tournament = await TournamentService.get_tournament(session, tournament_id)
        if not tournament:
            await callback.answer("Турнир не найден", show_alert=True)
            return

        is_participant = await TournamentService.is_participant(
            session, tournament_id, callback.from_user.id
        )

        participants = await TournamentService.get_participants(session, tournament_id)

    text = (
        f"🏆 <b>{tournament.name}</b>\n\n"
        f"{tournament.description or 'Нет описания'}\n\n"
        f"👥 Участников: {len(participants)}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_tournament_detail_keyboard(
            tournament_id,
            is_participant,
            tournament.registration_open,
            tournament.status
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("register_tournament_"))
async def register_tournament(callback: CallbackQuery):
    tournament_id = int(callback.data.split("_")[2])

    if not callback.from_user.username:
        await callback.answer("Нужен username!", show_alert=True)
        return

    async with async_session_maker() as session:
        ok = await TournamentService.register_participant(
            session, tournament_id, callback.from_user.id
        )

    await callback.answer(
        "✅ Вы зарегистрированы" if ok else "❌ Регистрация закрыта",
        show_alert=True
    )


@router.callback_query(F.data.startswith("tournament_table_"))
async def tournament_table(callback: CallbackQuery):
    tid = int(callback.data.split("_")[2])

    async with async_session_maker() as session:
        table = await TournamentService.get_tournament_table(session, tid)
        text = await TournamentService.format_tournament_table(table)

    await callback.message.edit_text(
        text,
        reply_markup=get_back_button(f"tournament_{tid}"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tournament_schedule_"))
async def tournament_schedule(callback: CallbackQuery):
    tid = int(callback.data.split("_")[2])

    async with async_session_maker() as session:
        matches = await ScheduleService.get_tournament_matches(session, tid)
        text = await ScheduleService.format_schedule(matches)

    await callback.message.edit_text(
        text,
        reply_markup=get_back_button(f"tournament_{tid}"),
        parse_mode="HTML"
    )
    await callback.answer()

# ======================================================
# RATING
# ======================================================

@router.callback_query(F.data.in_(["rating", "rating_top10"]))
async def rating(callback: CallbackQuery):
    async with async_session_maker() as session:
        players = await RatingService.get_top_players(session, 10)
        text = await RatingService.format_rating_table(players)

    await callback.message.edit_text(
        text,
        reply_markup=get_rating_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "rating_full")
async def rating_full(callback: CallbackQuery):
    async with async_session_maker() as session:
        players = await RatingService.get_all_players_ranked(session)
        text = await RatingService.format_rating_table(players)

    await callback.message.edit_text(
        text,
        reply_markup=get_back_button("rating"),
        parse_mode="HTML"
    )
    await callback.answer()

# ======================================================
# PROFILE
# ======================================================

@router.callback_query(F.data == "my_profile")
async def my_profile(callback: CallbackQuery):
    await show_profile(callback, callback.from_user.id)


@router.callback_query(F.data.startswith("profile_"))
async def other_profile(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await show_profile(callback, user_id)


async def show_profile(callback: CallbackQuery, user_id: int):
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.answer("Профиль не найден", show_alert=True)
            return

    winrate = (user.wins / user.matches_played * 100) if user.matches_played else 0

    text = (
        f"👤 <b>{user.full_name}</b>\n"
        f"@{user.username or '—'}\n\n"
        f"🏆 Рейтинг: {user.rating}\n"
        f"⚔️ Матчи: {user.matches_played}\n"
        f"📈 Winrate: {winrate:.1f}%"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_profile_keyboard(user_id),
        parse_mode="HTML"
    )
    await callback.answer()

# ======================================================
# ABOUT / RECORDS / SEARCH
# ======================================================

@router.callback_query(F.data == "about_project")
async def about(callback: CallbackQuery):
    await callback.message.edit_text(
        f"ℹ️ <b>{config.PROJECT_NAME}</b>\n\n{config.PROJECT_DESCRIPTION}",
        reply_markup=get_about_project_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "records_menu")
async def records(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏅 <b>Рекорды</b>",
        reply_markup=get_records_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "search_player")
async def search_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PlayerSearch.username)
    await callback.message.edit_text(
        "🔍 Введите username:",
        reply_markup=get_search_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(PlayerSearch.username)
async def search_process(message: Message, state: FSMContext):
    username = message.text.strip().lstrip("@")

    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.username.ilike(f"%{username}%"))
        )
        users = result.scalars().all()

    if not users:
        await message.answer("❌ Не найдено")
    else:
        for user in users[:5]:
            await message.answer(
                f"{user.full_name} (@{user.username})",
                reply_markup=get_profile_keyboard(user.id)
            )

    await state.clear()