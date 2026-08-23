"""SQLAlchemy ORM models for the SaaS entities."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class PlanType(str, enum.Enum):
    """Available subscription plans."""

    FREE = "Free"
    PRO = "Pro"
    INSTITUTIONAL = "Institutional"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    wallet_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        # MySQL BOOL is TINYINT(1); use a numeric literal for the server default.
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan_type: Mapped[PlanType] = mapped_column(
        Enum(
            PlanType,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            length=20,
        ),
        nullable=False,
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="subscriptions")


class LiquidityMetric(Base):
    """Append-only liquidity / price-impact metric.

    The composite primary key (``time`` + ``pool_address``) keeps every sample
    unique while supporting fast lookups for a pool over a time window.
    """

    __tablename__ = "liquidity_metrics"
    __table_args__ = (
        Index("ix_liquidity_metrics_pool_time", "pool_address", "time"),
    )

    # Time axis; part of the composite PK.
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    pool_address: Mapped[str] = mapped_column(
        String(42), primary_key=True, nullable=False
    )
    token_a_reserve: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_b_reserve: Mapped[float | None] = mapped_column(Float, nullable=True)
    swap_volume: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_drain: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_price_impact: Mapped[float] = mapped_column(Float, nullable=False)
