"""
T-League Bot - Модели базы данных
"""
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    BigInteger, String, Integer, Boolean, DateTime,
    ForeignKey, Text, Float, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# =====================
# ENUM КЛАССЫ
# =====================

class AdminRole(str, Enum):
    """Роли администраторов"""
    MODERATOR = "moderator"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"
    CO_OWNER = "co_owner"
    OWNER = "owner"


class AccountStatus(str, Enum):
    """Статусы заявки на продажу"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SOLD = "sold"


class TournamentStatus(str, Enum):
    REGISTRATION = "registration"
    ACTIVE = "active"
    FINISHED = "finished"


class TournamentFormat(str, Enum):
    ROUND_ROBIN = "round_robin"
    PLAYOFF = "playoff"
    SWISS = "swiss"
    GROUP_PLAYOFF = "group_playoff"


class MatchStatus(str, Enum):
    SCHEDULED = "scheduled"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    TECHNICAL = "technical"


# =====================
# BASE
# =====================

class Base(DeclarativeBase):
    pass


# =====================
# USER
# =====================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    rating: Mapped[int] = mapped_column(Integer, default=100)
    matches_played: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_tester: Mapped[bool] = mapped_column(Boolean, default=False)

    admin_role: Mapped[Optional[str]] = mapped_column(SQLEnum(AdminRole), nullable=True)
    granted_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    role_granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tournaments = relationship("TournamentParticipant", back_populates="user")
    home_matches = relationship("Match", foreign_keys="Match.player1_id", back_populates="player1")
    away_matches = relationship("Match", foreign_keys="Match.player2_id", back_populates="player2")

    # 🔴 ИСПРАВЛЕНИЕ ЗДЕСЬ
    accounts_for_sale = relationship(
        "AccountListing",
        back_populates="seller",
        foreign_keys="AccountListing.seller_id"
    )


# =====================
# SYSTEM
# =====================

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# =====================
# TOURNAMENT
# =====================

class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    format: Mapped[str] = mapped_column(SQLEnum(TournamentFormat))
    status: Mapped[str] = mapped_column(SQLEnum(TournamentStatus), default=TournamentStatus.REGISTRATION)
    registration_open: Mapped[bool] = mapped_column(Boolean, default=False)
    max_participants: Mapped[Optional[int]] = mapped_column(Integer)
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    total_rounds: Mapped[int] = mapped_column(Integer, default=0)
    draw_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    participants = relationship("TournamentParticipant", back_populates="tournament")
    matches = relationship("Match", back_populates="tournament")
    records = relationship("TournamentRecord", back_populates="tournament")


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))

    points: Mapped[int] = mapped_column(Integer, default=0)
    matches_played: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    goals_for: Mapped[int] = mapped_column(Integer, default=0)
    goals_against: Mapped[int] = mapped_column(Integer, default=0)

    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tournament = relationship("Tournament", back_populates="participants")
    user = relationship("User", back_populates="tournaments")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    round_number: Mapped[int] = mapped_column(Integer)

    player1_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    player2_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))

    player1_score: Mapped[Optional[int]] = mapped_column(Integer)
    player2_score: Mapped[Optional[int]] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(SQLEnum(MatchStatus), default=MatchStatus.SCHEDULED)

    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    deadline_set: Mapped[bool] = mapped_column(Boolean, default=False)

    played_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    reported_by: Mapped[Optional[int]] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tournament = relationship("Tournament", back_populates="matches")
    player1 = relationship("User", foreign_keys=[player1_id], back_populates="home_matches")
    player2 = relationship("User", foreign_keys=[player2_id], back_populates="away_matches")


class TournamentRecord(Base):
    __tablename__ = "tournament_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    record_type: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    value: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tournament = relationship("Tournament", back_populates="records")
    user = relationship("User")


# =====================
# LOGS
# =====================

class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(255))
    details: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    admin = relationship("User")


class TesterAccessLog(Base):
    __tablename__ = "tester_access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    code_used: Mapped[str] = mapped_column(String(100))
    success: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# =====================
# MARKETPLACE
# =====================

class AccountListing(Base):
    __tablename__ = "account_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))

    team_strength: Mapped[int] = mapped_column(Integer)
    legendary_players: Mapped[str] = mapped_column(Text)
    gp_points: Mapped[int] = mapped_column(Integer)
    efootball_points: Mapped[int] = mapped_column(Integer)
    with_email: Mapped[bool] = mapped_column(Boolean)
    price: Mapped[int] = mapped_column(Integer)

    description: Mapped[Optional[str]] = mapped_column(Text)
    photos: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(SQLEnum(AccountStatus), default=AccountStatus.PENDING)

    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    sold_to: Mapped[Optional[int]] = mapped_column(BigInteger)
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    seller = relationship("User", foreign_keys=[seller_id], back_populates="accounts_for_sale")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class ModeratorAction(Base):
    __tablename__ = "moderator_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    moderator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    action_type: Mapped[str] = mapped_column(String(100))
    target_id: Mapped[Optional[int]] = mapped_column(Integer)
    details: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    moderator = relationship("User")