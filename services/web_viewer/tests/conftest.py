"""
Pytest configuration and fixtures for web_viewer tests.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.database.models import Base, Stock, StockPrice
from services.web_viewer.main import app, get_db


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(test_engine):
    """Create a test client with dependency override."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_stocks(test_db):
    """Create sample stock data for testing."""
    stocks = [
        Stock(
            ticker="005930",
            name_kr="삼성전자",
            name_en="Samsung Electronics",
            market="KOSPI",
            sector="전기전자",
            is_active=True
        ),
        Stock(
            ticker="000660",
            name_kr="SK하이닉스",
            name_en="SK Hynix",
            market="KOSPI",
            sector="반도체",
            is_active=True
        ),
        Stock(
            ticker="035420",
            name_kr="NAVER",
            name_en="NAVER Corporation",
            market="KOSPI",
            sector="인터넷",
            is_active=True
        ),
        Stock(
            ticker="999999",
            name_kr="비활성종목",
            name_en="Inactive Stock",
            market="KOSDAQ",
            sector="기타",
            is_active=False
        ),
    ]

    for stock in stocks:
        test_db.add(stock)
    test_db.commit()

    # Refresh to get IDs
    for stock in stocks:
        test_db.refresh(stock)

    return stocks


@pytest.fixture
def sample_prices(test_db, sample_stocks):
    """Create sample price data for testing."""
    samsung = sample_stocks[0]  # 005930

    base_date = datetime(2024, 1, 1)
    prices = []

    # Create 150 days of price data for pagination testing
    for i in range(150):
        date = base_date + timedelta(days=i)
        price = StockPrice(
            stock_id=samsung.id,
            date=date,
            open=Decimal("70000") + Decimal(i * 100),
            high=Decimal("71000") + Decimal(i * 100),
            low=Decimal("69000") + Decimal(i * 100),
            close=Decimal("70500") + Decimal(i * 100),
            volume=15000000 + (i * 10000),
            adjusted_close=Decimal("70500") + Decimal(i * 100),
            change_pct=0.5 + (i * 0.01)
        )
        prices.append(price)
        test_db.add(price)

    test_db.commit()
    return prices


@pytest.fixture
def empty_stock(test_db):
    """Create a stock with no price data."""
    stock = Stock(
        ticker="111111",
        name_kr="데이터없는종목",
        name_en="No Data Stock",
        market="KOSDAQ",
        sector="테스트",
        is_active=True
    )
    test_db.add(stock)
    test_db.commit()
    test_db.refresh(stock)
    return stock
