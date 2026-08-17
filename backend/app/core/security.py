"""Password hashing utilities using passlib (bcrypt)."""
from __future__ import annotations

from passlib.context import CryptContext

# `deprecated="auto"` transparently upgrades hashes on verify when the default
# scheme changes, keeping stored credentials secure over time.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
