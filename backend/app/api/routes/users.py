"""User account endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.exceptions import AppError
from ...core.security import get_password_hash
from ...db import models, schemas
from ...db.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=201,
)
def register_user(
    body: schemas.UserCreate,
    db: Session = Depends(get_db),
) -> models.User:
    """Register a new user with a bcrypt-hashed password."""
    existing = db.scalar(select(models.User).where(models.User.email == body.email))
    if existing is not None:
        raise AppError(
            "A user with this email already exists.",
            status_code=409,
            code="email_taken",
        )

    user = models.User(
        email=body.email,
        hashed_password=get_password_hash(body.password),
        wallet_address=body.wallet_address,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
