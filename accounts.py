"""Хендлеры системы продажи аккаунтов eFootball"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from database.engine import async_session_maker
from database.models import AccountListing, User, AccountStatus
from services.accounts import AccountsService
from services.roles import RolesService
from config import config
from states.states import AccountCreate, AccountModerate

router = Router()

# ГЛАВНОЕ МЕНЮ
@router.callback_query(F.data == "marketplace")
async def show_marketplace_menu(callback: CallbackQuery):
    """Меню маркетплейса"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Купить аккаунт", callback_data="buy_account")
    kb.button(text="💰 Продать аккаунт", callback_data="sell_account")
    kb.button(text="📋 Мои заявки", callback_data="my_listings")
    kb.button(text="◀️ В главное меню", callback_data="main_menu")
    kb.adjust(2, 1, 1)
    
    await callback.message.edit_text(
        "🏪 <b>Маркетплейс аккаунтов</b>\n\n"
        "Покупка и продажа аккаунтов eFootball Mobile",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )

# ПРОДАЖА
@router.callback_query(F.data == "sell_account")
async def start_sell(callback: CallbackQuery, state: FSMContext):
    """Начало создания заявки"""
    await state.set_state(AccountCreate.team_strength)
    await callback.message.answer(
        "💰 <b>Продажа аккаунта</b>\n\n"
        "Введите совокупность силы команды:",
        parse_mode="HTML"
    )

@router.message(AccountCreate.team_strength)
async def acc_team_strength(m: Message, state: FSMContext):
    try:
        strength = int(m.text)
        await state.update_data(team_strength=strength)
        await state.set_state(AccountCreate.legendary_players)
        await m.answer("⭐ Перечислите легенд через запятую:")
    except:
        await m.answer("❌ Введите число:")

@router.message(AccountCreate.legendary_players)
async def acc_legends(m: Message, state: FSMContext):
    await state.update_data(legendary_players=m.text)
    await state.set_state(AccountCreate.gp_points)
    await m.answer("💎 Введите количество GP:")

@router.message(AccountCreate.gp_points)
async def acc_gp(m: Message, state: FSMContext):
    try:
        gp = int(m.text.replace(",", "").replace(" ", ""))
        await state.update_data(gp_points=gp)
        await state.set_state(AccountCreate.efootball_points)
        await m.answer("🎁 Введите eFootball Points:")
    except:
        await m.answer("❌ Введите число:")

@router.message(AccountCreate.efootball_points)
async def acc_efp(m: Message, state: FSMContext):
    try:
        efp = int(m.text.replace(",", "").replace(" ", ""))
        await state.update_data(efootball_points=efp)
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ С почтой", callback_data="email_yes")
        kb.button(text="❌ Без почты", callback_data="email_no")
        kb.adjust(2)
        
        await m.answer("📧 С выдачей почты?", reply_markup=kb.as_markup())
        await state.set_state(AccountCreate.with_email)
    except:
        await m.answer("❌ Введите число:")

@router.callback_query(AccountCreate.with_email)
async def acc_email(callback: CallbackQuery, state: FSMContext):
    with_email = callback.data == "email_yes"
    await state.update_data(with_email=with_email)
    await state.set_state(AccountCreate.price)
    await callback.message.answer("💵 Введите цену (без комиссии 50₽):")

@router.message(AccountCreate.price)
async def acc_price(m: Message, state: FSMContext):
    try:
        price = int(m.text)
        await state.update_data(price=price)
        await state.set_state(AccountCreate.description)
        await m.answer("📝 Описание (или - чтобы пропустить):")
    except:
        await m.answer("❌ Введите число:")

@router.message(AccountCreate.description)
async def acc_desc(m: Message, state: FSMContext):
    desc = None if m.text == "-" else m.text
    await state.update_data(description=desc)
    await state.set_state(AccountCreate.photos)
    await m.answer("📸 Отправьте до 5 фото (когда закончите, отправьте /done):")

@router.message(AccountCreate.photos, F.photo)
async def acc_photos(m: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    
    if len(photos) < 5:
        photos.append(m.photo[-1].file_id)
        await state.update_data(photos=photos)
        await m.answer(f"✅ Фото {len(photos)}/5 добавлено")
    else:
        await m.answer("❌ Максимум 5 фото")

@router.message(AccountCreate.photos, F.text == "/done")
async def acc_done(m: Message, state: FSMContext, bot):
    data = await state.get_data()
    
    async with async_session_maker() as session:
        listing = await AccountsService.create_listing(
            session, m.from_user.id,
            data['team_strength'], data['legendary_players'],
            data['gp_points'], data['efootball_points'],
            data['with_email'], data['price'],
            data.get('description', ''), data.get('photos', [])
        )
        
        # Уведомление админам
        for admin_id in config.ADMIN_IDS:
            try:
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                kb = InlineKeyboardBuilder()
                kb.button(text="✅ Одобрить", callback_data=f"approve_listing_{listing.id}")
                kb.button(text="❌ Отклонить", callback_data=f"reject_listing_{listing.id}")
                kb.adjust(2)
                
                await bot.send_message(
                    admin_id,
                    f"🆕 Новая заявка на продажу #{listing.id}\n"
                    f"Сила: {listing.team_strength}\n"
                    f"Цена: {listing.price}₽",
                    reply_markup=kb.as_markup()
                )
            except:
                pass
    
    await m.answer(
        "✅ Заявка отправлена!\n\n"
        f"Ожидайте одобрения от @{config.MANAGER_URL.split('/')[-1]}"
    )
    await state.clear()

# ПОКУПКА
@router.callback_query(F.data == "buy_account")
async def buy_accounts(callback: CallbackQuery):
    async with async_session_maker() as session:
        listings = await AccountsService.get_approved_listings(session)
        
        if not listings:
            await callback.answer("Нет доступных аккаунтов", show_alert=True)
            return
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        for listing in listings[:10]:
            kb.button(
                text=f"⚽ {listing.team_strength} - {listing.price}₽",
                callback_data=f"view_listing_{listing.id}"
            )
        kb.button(text="◀️ Назад", callback_data="marketplace")
        kb.adjust(1)
        
        await callback.message.edit_text(
            "🛒 <b>Доступные аккаунты</b>",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("view_listing_"))
async def view_listing(callback: CallbackQuery, bot):
    listing_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(AccountListing).where(AccountListing.id == listing_id)
        )
        listing = result.scalar_one_or_none()
        
        if not listing:
            await callback.answer("Заявка не найдена", show_alert=True)
            return
        
        text = AccountsService.format_listing_full(listing)
        
        import json
        photos = json.loads(listing.photos) if listing.photos else []
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        kb.button(text="💬 Связаться", url=config.MANAGER_URL)
        kb.button(text="◀️ К списку", callback_data="buy_account")
        kb.adjust(1)
        
        if photos:
            from aiogram.types import InputMediaPhoto
            media = [InputMediaPhoto(media=photos[0], caption=text, parse_mode="HTML")]
            for photo in photos[1:5]:
                media.append(InputMediaPhoto(media=photo))
            
            await callback.message.answer_media_group(media)
            await callback.message.answer("👆 Детали аккаунта", reply_markup=kb.as_markup())
        else:
            await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

# МОДЕРАЦИЯ
@router.callback_query(F.data.startswith("approve_listing_"))
async def approve_listing(callback: CallbackQuery):
    listing_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == callback.from_user.id))
        user = result.scalar_one()
        
        if not RolesService.has_permission(user.admin_role, 'approve_listings'):
            await callback.answer("❌ Нет прав", show_alert=True)
            return
        
        success = await AccountsService.approve_listing(session, listing_id, callback.from_user.id)
        
        if success:
            await callback.message.edit_text("✅ Заявка одобрена")
        else:
            await callback.answer("Ошибка", show_alert=True)

@router.callback_query(F.data.startswith("reject_listing_"))
async def reject_listing_start(callback: CallbackQuery, state: FSMContext):
    listing_id = int(callback.data.split("_")[2])
    await state.update_data(listing_id=listing_id)
    await state.set_state(AccountModerate.rejection_reason)
    await callback.message.answer("✍️ Введите причину отклонения:")

@router.message(AccountModerate.rejection_reason)
async def reject_listing_finish(m: Message, state: FSMContext):
    data = await state.get_data()
    listing_id = data['listing_id']
    
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == m.from_user.id))
        user = result.scalar_one()
        
        await AccountsService.reject_listing(session, listing_id, m.from_user.id, m.text)
    
    await m.answer("✅ Заявка отклонена")
    await state.clear()