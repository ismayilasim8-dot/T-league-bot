"""
T-League Bot - Система продажи аккаунтов eFootball
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import AccountListing, User, AccountStatus, ModeratorAction
from typing import List, Optional
import json

COMMISSION_FEE = 50  # Комиссия за сделку в рублях

class AccountsService:
    """Сервис управления продажей аккаунтов"""
    
    @staticmethod
    async def create_listing(
        session: AsyncSession,
        seller_id: int,
        team_strength: int,
        legendary_players: str,
        gp_points: int,
        efootball_points: int,
        with_email: bool,
        price: int,
        description: str,
        photos: List[str]
    ) -> Optional[AccountListing]:
        """Создание заявки на продажу"""
        listing = AccountListing(
            seller_id=seller_id,
            team_strength=team_strength,
            legendary_players=legendary_players,
            gp_points=gp_points,
            efootball_points=efootball_points,
            with_email=with_email,
            price=price,
            description=description,
            photos=json.dumps(photos),
            status=AccountStatus.PENDING
        )
        session.add(listing)
        await session.commit()
        await session.refresh(listing)
        return listing
    
    @staticmethod
    async def get_pending_listings(session: AsyncSession) -> List[AccountListing]:
        """Получение заявок на модерации"""
        result = await session.execute(
            select(AccountListing)
            .where(AccountListing.status == AccountStatus.PENDING)
            .order_by(AccountListing.created_at)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_approved_listings(session: AsyncSession) -> List[AccountListing]:
        """Получение одобренных заявок"""
        result = await session.execute(
            select(AccountListing)
            .where(AccountListing.status == AccountStatus.APPROVED)
            .order_by(AccountListing.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def approve_listing(
        session: AsyncSession,
        listing_id: int,
        moderator_id: int
    ) -> bool:
        """Одобрение заявки"""
        from datetime import datetime
        
        result = await session.execute(
            select(AccountListing).where(AccountListing.id == listing_id)
        )
        listing = result.scalar_one_or_none()
        
        if not listing:
            return False
        
        listing.status = AccountStatus.APPROVED
        listing.reviewed_by = moderator_id
        listing.reviewed_at = datetime.utcnow()
        
        # Логирование действия
        action = ModeratorAction(
            moderator_id=moderator_id,
            action_type="approve_listing",
            target_id=listing_id,
            details=f"Одобрена заявка на продажу (цена: {listing.price}₽)"
        )
        session.add(action)
        
        await session.commit()
        return True
    
    @staticmethod
    async def reject_listing(
        session: AsyncSession,
        listing_id: int,
        moderator_id: int,
        reason: str
    ) -> bool:
        """Отклонение заявки"""
        from datetime import datetime
        
        result = await session.execute(
            select(AccountListing).where(AccountListing.id == listing_id)
        )
        listing = result.scalar_one_or_none()
        
        if not listing:
            return False
        
        listing.status = AccountStatus.REJECTED
        listing.reviewed_by = moderator_id
        listing.reviewed_at = datetime.utcnow()
        listing.rejection_reason = reason
        
        action = ModeratorAction(
            moderator_id=moderator_id,
            action_type="reject_listing",
            target_id=listing_id,
            details=f"Отклонена заявка: {reason}"
        )
        session.add(action)
        
        await session.commit()
        return True
    
    @staticmethod
    async def get_listing_with_seller(
        session: AsyncSession,
        listing_id: int
    ) -> Optional[tuple]:
        """Получение заявки с информацией о продавце"""
        result = await session.execute(
            select(AccountListing, User)
            .join(User, AccountListing.seller_id == User.id)
            .where(AccountListing.id == listing_id)
        )
        return result.first()
    
    @staticmethod
    def format_listing_preview(listing: AccountListing) -> str:
        """Краткое форматирование заявки для списка"""
        email_status = "✅ С почтой" if listing.with_email else "❌ Без почты"
        return (
            f"⚽ Сила: {listing.team_strength}\n"
            f"💰 Цена: {listing.price}₽ (+{COMMISSION_FEE}₽ комиссия)\n"
            f"{email_status}"
        )
    
    @staticmethod
    def format_listing_full(listing: AccountListing, show_seller: bool = False) -> str:
        """Полное форматирование заявки"""
        photos_list = json.loads(listing.photos) if listing.photos else []
        email_status = "✅ С выдачей почты" if listing.with_email else "❌ Без выдачи почты"
        
        text = (
            f"⚽ <b>Аккаунт eFootball Mobile</b>\n\n"
            f"🎯 Совокупность силы: <b>{listing.team_strength}</b>\n"
            f"⭐ Легенды: {listing.legendary_players}\n"
            f"💎 GP: {listing.gp_points:,}\n"
            f"🎁 eFootball Points: {listing.efootball_points:,}\n"
            f"{email_status}\n\n"
            f"💰 <b>Цена: {listing.price}₽</b>\n"
            f"💳 Комиссия гаранта: +{COMMISSION_FEE}₽\n"
            f"💵 Итого: {listing.price + COMMISSION_FEE}₽\n\n"
        )
        
        if listing.description:
            text += f"📝 Описание: {listing.description}\n\n"
        
        if show_seller:
            text += f"👤 Продавец: ID {listing.seller_id}\n"
        
        text += f"📸 Фотографий: {len(photos_list)}"
        
        return text