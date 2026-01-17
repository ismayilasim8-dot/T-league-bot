"""
T-League Bot - Система ролей (5 уровней)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import User, AdminRole, ModeratorAction
from typing import Optional
from datetime import datetime

class RolesService:
    """Сервис управления ролями"""
    
    # Уровни доступа (чем выше число, тем выше уровень)
    ROLE_LEVELS = {
        AdminRole.MODERATOR: 1,   # Модератор
        AdminRole.SUPERVISOR: 2,   # Следящий
        AdminRole.ADMIN: 3,        # Администратор
        AdminRole.CO_OWNER: 4,     # Совладелец
        AdminRole.OWNER: 5         # Владелец
    }
    
    @staticmethod
    async def grant_role(
        session: AsyncSession,
        user_id: int,
        role: AdminRole,
        granted_by: int
    ) -> bool:
        """Выдача роли пользователю"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        user.admin_role = role
        user.granted_by = granted_by
        user.role_granted_at = datetime.utcnow()
        user.is_admin = True
        
        await session.commit()
        return True
    
    @staticmethod
    async def revoke_role(
        session: AsyncSession,
        user_id: int
    ) -> bool:
        """Отзыв роли"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        user.admin_role = None
        user.granted_by = None
        user.role_granted_at = None
        user.is_admin = False
        
        await session.commit()
        return True
    
    @staticmethod
    async def get_user_role(session: AsyncSession, user_id: int) -> Optional[AdminRole]:
        """Получение роли пользователя"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return user.admin_role if user else None
    
    @staticmethod
    def can_grant_role(granter_role: AdminRole, target_role: AdminRole) -> bool:
        """Проверка, может ли granter выдать target_role"""
        # Только владелец может выдавать роли
        return granter_role == AdminRole.OWNER
    
    @staticmethod
    def can_manage_user(manager_role: AdminRole, target_role: Optional[AdminRole]) -> bool:
        """Проверка, может ли manager управлять target"""
        if manager_role == AdminRole.OWNER:
            return True
        
        if not target_role:
            return False
        
        manager_level = RolesService.ROLE_LEVELS.get(manager_role, 0)
        target_level = RolesService.ROLE_LEVELS.get(target_role, 0)
        
        return manager_level > target_level
    
    @staticmethod
    def has_permission(role: Optional[AdminRole], permission: str) -> bool:
        """Проверка наличия разрешения"""
        if not role:
            return False
        
        permissions = {
            AdminRole.MODERATOR: {
                'approve_listings',
                'reject_listings', 
                'resolve_disputes',
                'view_disputes'
            },
            AdminRole.SUPERVISOR: {
                'approve_listings',
                'reject_listings',
                'resolve_disputes',
                'view_disputes',
                'view_moderator_logs'
            },
            AdminRole.ADMIN: {
                'approve_listings',
                'reject_listings',
                'resolve_disputes',
                'view_disputes',
                'view_moderator_logs',
                'create_tournament',
                'manage_own_tournaments'
            },
            AdminRole.CO_OWNER: {
                'approve_listings',
                'reject_listings',
                'resolve_disputes',
                'view_disputes',
                'view_moderator_logs',
                'create_tournament',
                'manage_own_tournaments',
                'manage_all_tournaments',
                'broadcast',
                'export_data',
                'recalculate_ratings'
            },
            AdminRole.OWNER: {
                'approve_listings',
                'reject_listings',
                'resolve_disputes',
                'view_disputes',
                'view_moderator_logs',
                'create_tournament',
                'manage_own_tournaments',
                'manage_all_tournaments',
                'broadcast',
                'export_data',
                'recalculate_ratings',
                'grant_roles',
                'revoke_roles',
                'full_access'
            }
        }
        
        return permission in permissions.get(role, set())
    
    @staticmethod
    async def get_moderator_actions(
        session: AsyncSession,
        moderator_id: Optional[int] = None,
        limit: int = 50
    ) -> list:
        """Получение логов действий модераторов"""
        query = select(ModeratorAction, User).join(
            User, ModeratorAction.moderator_id == User.id
        ).order_by(ModeratorAction.created_at.desc())
        
        if moderator_id:
            query = query.where(ModeratorAction.moderator_id == moderator_id)
        
        query = query.limit(limit)
        
        result = await session.execute(query)
        return result.all()
    
    @staticmethod
    def format_role_name(role: AdminRole) -> str:
        """Форматирование названия роли"""
        names = {
            AdminRole.MODERATOR: "👮 Модератор",
            AdminRole.SUPERVISOR: "👁️ Следящий",
            AdminRole.ADMIN: "⚙️ Администратор",
            AdminRole.CO_OWNER: "👑 Совладелец",
            AdminRole.OWNER: "🔱 Владелец"
        }
        return names.get(role, "❓ Неизвестная роль")
    
    @staticmethod
    def format_permissions(role: AdminRole) -> str:
        """Форматирование списка разрешений"""
        descriptions = {
            AdminRole.MODERATOR: (
                "📋 <b>Возможности:</b>\n"
                "• Одобрение/отклонение заявок на продажу\n"
                "• Решение оспоренных матчей\n"
                "• Связь с игроками для уточнения счёта"
            ),
            AdminRole.SUPERVISOR: (
                "📋 <b>Возможности:</b>\n"
                "• Всё от Модератора\n"
                "• Просмотр логов действий модераторов\n"
                "• Контроль работы модераторов"
            ),
            AdminRole.ADMIN: (
                "📋 <b>Возможности:</b>\n"
                "• Всё от Модератора и Следящего\n"
                "• Создание турниров\n"
                "• Управление своими турнирами"
            ),
            AdminRole.CO_OWNER: (
                "📋 <b>Возможности:</b>\n"
                "• Всё от предыдущих уровней\n"
                "• Управление всеми турнирами\n"
                "• Массовые рассылки\n"
                "• Экспорт данных\n"
                "• Пересчёт рейтингов"
            ),
            AdminRole.OWNER: (
                "📋 <b>Возможности:</b>\n"
                "• ПОЛНЫЙ доступ ко всему\n"
                "• Выдача/отзыв ролей\n"
                "• Управление совладельцами\n"
                "• Управление турнирами любого уровня"
            )
        }
        return descriptions.get(role, "Нет описания")