"""
Database session management for data collector service.
"""
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

# Add shared directory to path to import models and config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database.models import Base
from shared.configs.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Session:
    """
    Context manager for database sessions.

    Yields:
        Database session

    Example:
        with get_db_session() as db:
            stocks = db.query(Stock).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_db() -> Session:
    """
    Get a database session (for dependency injection).

    Returns:
        Database session

    Example:
        db = get_db()
        try:
            stocks = db.query(Stock).all()
            db.commit()
        finally:
            db.close()
    """
    return SessionLocal()
