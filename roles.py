"""Хендлеры управления ролями"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from database.engine import async_session_maker
from database.models import User, AdminRole
from services.roles import RolesService
from states.states import RoleGrant

router = Router()

@router.callback_query(F.data == "manage_roles")
async def show_roles_menu(callback: CallbackQuery):
    """Меню управления ролями (только для владельца)"""
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == callback.from_user.id))
        user = result.scalar_one()
        
        if user.admin_role != AdminRole.OWNER:
            await callback.answer("❌ Только для владельца", show_alert=True)
            return
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Выдать роль", callback_data="grant_role")
    kb.button(text="➖ Отозвать роль", callback_data="revoke_role")
    kb.button(text="👥 Список ролей", callback_data="list_roles")
    kb.button(text="◀️ Админ-панель", callback_data="admin_panel")
    kb.adjust(2, 1, 1)
    
    await callback.message.edit_text(
        "👑 <b>Управление ролями</b>\n\n"
        "Выдача и отзыв прав доступа",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "grant_role")
async def start_grant(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RoleGrant.username)
    await callback.message.answer("👤 Введите @username для выдачи роли:")

@router.message(RoleGrant.username)
async def grant_username(m: Message, state: FSMContext):
    username = m.text.lstrip("@")
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await m.answer("❌ Пользователь не найден")
            return
        
        await state.update_data(target_user_id=user.id, target_username=username)
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        for role in [AdminRole.MODERATOR, AdminRole.SUPERVISOR, AdminRole.ADMIN, AdminRole.CO_OWNER]:
            kb.button(
                text=RolesService.format_role_name(role),
                callback_data=f"select_role_{role.value}"
            )
        kb.button(text="❌ Отмена", callback_data="manage_roles")
        kb.adjust(2)
        
        await m.answer(
            f"Выберите роль для @{username}:",
            reply_markup=kb.as_markup()
        )
        await state.set_state(RoleGrant.role)

@router.callback_query(RoleGrant.role, F.data.startswith("select_role_"))
async def confirm_grant(callback: CallbackQuery, state: FSMContext):
    role_value = callback.data.split("_")[2]
    role = AdminRole(role_value)
    
    data = await state.get_data()
    user_id = data['target_user_id']
    username = data['target_username']
    
    async with async_session_maker() as session:
        await RolesService.grant_role(session, user_id, role, callback.from_user.id)
    
    await callback.message.edit_text(
        f"✅ Роль {RolesService.format_role_name(role)} выдана @{username}"
    )
    await state.clear()

@router.callback_query(F.data == "list_roles")
async def list_roles(callback: CallbackQuery):
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.admin_role.isnot(None))
        )
        users = result.scalars().all()
        
        if not users:
            await callback.answer("Нет выданных ролей", show_alert=True)
            return
        
        text = "👥 <b>Список ролей</b>\n\n"
        for user in users:
            text += f"{RolesService.format_role_name(user.admin_role)}\n"
            text += f"└ @{user.username or user.full_name}\n\n"
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        kb.button(text="◀️ Назад", callback_data="manage_roles")
        
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")