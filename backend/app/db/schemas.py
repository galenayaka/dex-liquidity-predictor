"""Pydantic schemas for account creation and login responses."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload validated on account registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    wallet_address: str | None = Field(default=None, max_length=42)


class UserResponse(BaseModel):
    """User representation returned by the API (never includes the hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    wallet_address: str | None
    is_active: bool
    created_at: datetime
