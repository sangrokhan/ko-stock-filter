"""
Database connection management.
"""
from typing import Generator, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from shared.configs.config import get_settings

settings = get_settings()


def get_engine(database_url: Optional[str] = None) -> Engine:
    """
    Get or create database engine.

    Args:
        database_url: Database URL (uses settings if None)

    Returns:
        SQLAlchemy engine
    """
    url = database_url or settings.database_url
    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.debug
    )


def get_session(engine: Engine) -> Session:
    """
    Get database session from engine.

    Args:
        engine: SQLAlchemy engine

    Returns:
        Database session
    """
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionFactory()


# Default database engine
engine = get_engine()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    from shared.database.models import Base
    Base.metadata.create_all(bind=engine)
