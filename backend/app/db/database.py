"""SQLAlchemy 2.0 database connection configuration (PostgreSQL)."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..core.config import get_settings

settings = get_settings()

# `create_engine` is lazy: no connection is opened until first use, so the
# application can still boot in mock mode without a running PostgreSQL.
# `connect_timeout` makes `init_db()` fail fast when the database is offline
# instead of blocking startup on a long TCP connect.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all registered tables (idempotent)."""
    # Import models so they register their tables with Base.metadata.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
