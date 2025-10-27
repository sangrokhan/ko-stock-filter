"""
Pytest configuration and fixtures.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.database.models import Base


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing."""
    return {
        "ticker": "005930",  # Samsung Electronics
        "name_kr": "삼성전자",
        "name_en": "Samsung Electronics",
        "market": "KOSPI",
        "sector": "Technology",
        "industry": "Semiconductors",
    }


@pytest.fixture
def sample_price_data():
    """Sample price data for testing."""
    return [
        {"open": 70000, "high": 71000, "low": 69500, "close": 70500, "volume": 10000000},
        {"open": 70500, "high": 71500, "low": 70000, "close": 71000, "volume": 11000000},
        {"open": 71000, "high": 72000, "low": 70500, "close": 71500, "volume": 12000000},
    ]
