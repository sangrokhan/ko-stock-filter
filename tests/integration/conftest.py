"""
Integration test fixtures and configuration.

This module provides fixtures for integration testing with Docker Compose,
database setup, service communication, and sample data.
"""

import os
import time
from typing import Generator, Dict, Any
from datetime import datetime, timedelta

import pytest
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from shared.database.models import Base, Stock, StockPrice, TechnicalIndicator, FundamentalIndicator
from shared.database.models import Trade, Portfolio, Watchlist, CompositeScore, StabilityScore


# Test database configuration
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://test_user:test_password@localhost:5433/stock_trading_test"
)

# Test service URLs
TEST_SERVICE_URLS = {
    "data_collector": os.getenv("TEST_DATA_COLLECTOR_URL", "http://localhost:8101"),
    "indicator_calculator": os.getenv("TEST_INDICATOR_CALCULATOR_URL", "http://localhost:8102"),
    "stock_screener": os.getenv("TEST_STOCK_SCREENER_URL", "http://localhost:8103"),
    "trading_engine": os.getenv("TEST_TRADING_ENGINE_URL", "http://localhost:8104"),
    "risk_manager": os.getenv("TEST_RISK_MANAGER_URL", "http://localhost:8105"),
}


@pytest.fixture(scope="session")
def integration_db_engine():
    """
    Create a database engine for integration tests.
    Uses the actual PostgreSQL test database from Docker Compose.
    """
    engine = create_engine(
        TEST_DB_URL,
        poolclass=NullPool,  # Don't pool connections in tests
        echo=False,
    )

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Clean up
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def integration_db_session(integration_db_engine) -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.
    Automatically rolls back changes after each test.
    """
    connection = integration_db_engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def clean_database(integration_db_session):
    """
    Ensure database is clean before each test.
    Truncates all tables in the correct order to respect foreign keys.
    """
    session = integration_db_session

    # Order matters due to foreign key constraints
    tables = [
        "watchlist_history",
        "watchlist",
        "portfolio_risk_metrics",
        "portfolio",
        "trade",
        "composite_score",
        "stability_score",
        "fundamental_indicator",
        "technical_indicator",
        "stock_price",
        "stock",
    ]

    for table in tables:
        session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))

    session.commit()

    return session


@pytest.fixture(scope="session")
def wait_for_services():
    """
    Wait for all test services to be ready.
    Polls health endpoints until all services are available.
    """
    max_attempts = 30
    retry_delay = 2

    print("\nWaiting for test services to be ready...")

    for service_name, base_url in TEST_SERVICE_URLS.items():
        health_url = f"{base_url}/health"

        for attempt in range(max_attempts):
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    print(f"✓ {service_name} is ready")
                    break
            except requests.exceptions.RequestException:
                pass

            if attempt == max_attempts - 1:
                raise TimeoutError(
                    f"Service {service_name} did not become ready after {max_attempts * retry_delay} seconds"
                )

            time.sleep(retry_delay)

    print("All services are ready!\n")
    return TEST_SERVICE_URLS


@pytest.fixture
def service_urls(wait_for_services) -> Dict[str, str]:
    """Provide test service URLs."""
    return TEST_SERVICE_URLS


@pytest.fixture
def sample_stocks(integration_db_session) -> list[Stock]:
    """
    Create sample stock data for testing.
    Returns a list of Stock objects.
    """
    stocks = [
        Stock(
            ticker="005930",
            name="삼성전자",
            market="KOSPI",
            sector="전기전자",
            market_cap=400000000000000,  # 400 trillion KRW
        ),
        Stock(
            ticker="000660",
            name="SK하이닉스",
            market="KOSPI",
            sector="전기전자",
            market_cap=80000000000000,  # 80 trillion KRW
        ),
        Stock(
            ticker="035420",
            name="NAVER",
            market="KOSPI",
            sector="서비스업",
            market_cap=30000000000000,  # 30 trillion KRW
        ),
        Stock(
            ticker="005380",
            name="현대차",
            market="KOSPI",
            sector="운수장비",
            market_cap=40000000000000,  # 40 trillion KRW
        ),
        Stock(
            ticker="051910",
            name="LG화학",
            market="KOSPI",
            sector="화학",
            market_cap=35000000000000,  # 35 trillion KRW
        ),
    ]

    for stock in stocks:
        integration_db_session.add(stock)

    integration_db_session.commit()

    # Refresh to get IDs
    for stock in stocks:
        integration_db_session.refresh(stock)

    return stocks


@pytest.fixture
def sample_stock_prices(integration_db_session, sample_stocks) -> list[StockPrice]:
    """
    Create sample stock price data for testing.
    Generates 30 days of OHLCV data for each stock.
    """
    prices = []
    base_date = datetime.now().date() - timedelta(days=30)

    for stock in sample_stocks:
        base_price = 50000 if stock.ticker == "005930" else 100000

        for day_offset in range(30):
            date = base_date + timedelta(days=day_offset)

            # Simple price variation
            variation = 1.0 + (day_offset % 5 - 2) * 0.02
            open_price = base_price * variation
            close_price = base_price * variation * 1.01
            high_price = max(open_price, close_price) * 1.02
            low_price = min(open_price, close_price) * 0.98
            volume = 1000000 + (day_offset * 10000)

            price = StockPrice(
                stock_id=stock.id,
                date=date,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
            )
            prices.append(price)
            integration_db_session.add(price)

    integration_db_session.commit()

    return prices


@pytest.fixture
def sample_technical_indicators(integration_db_session, sample_stocks) -> list[TechnicalIndicator]:
    """
    Create sample technical indicator data for testing.
    """
    indicators = []
    date = datetime.now().date()

    for stock in sample_stocks:
        indicator = TechnicalIndicator(
            stock_id=stock.id,
            date=date,
            rsi_14=55.5,
            rsi_9=58.2,
            macd=1.5,
            macd_signal=1.2,
            macd_histogram=0.3,
            sma_20=50000,
            sma_50=49500,
            sma_200=48000,
            ema_12=50200,
            ema_26=49800,
            bollinger_upper=52000,
            bollinger_middle=50000,
            bollinger_lower=48000,
            stochastic_k=65.0,
            stochastic_d=62.5,
            adx=25.0,
            obv=5000000,
            atr=2500,
        )
        indicators.append(indicator)
        integration_db_session.add(indicator)

    integration_db_session.commit()

    return indicators


@pytest.fixture
def sample_fundamental_indicators(integration_db_session, sample_stocks) -> list[FundamentalIndicator]:
    """
    Create sample fundamental indicator data for testing.
    """
    indicators = []
    date = datetime.now().date()

    for stock in sample_stocks:
        indicator = FundamentalIndicator(
            stock_id=stock.id,
            date=date,
            per=12.5,
            pbr=1.8,
            psr=2.1,
            roe=15.2,
            roa=8.5,
            debt_ratio=45.0,
            current_ratio=1.8,
            operating_margin=12.5,
            net_margin=8.3,
            revenue_growth=8.5,
            earnings_growth=12.0,
            dividend_yield=2.5,
        )
        indicators.append(indicator)
        integration_db_session.add(indicator)

    integration_db_session.commit()

    return indicators


@pytest.fixture
def sample_portfolio(integration_db_session, sample_stocks) -> list[Portfolio]:
    """
    Create sample portfolio data for testing.
    """
    positions = []
    user_id = "test_user_123"

    # Add 2 positions
    for i, stock in enumerate(sample_stocks[:2]):
        position = Portfolio(
            user_id=user_id,
            stock_id=stock.id,
            quantity=100 + (i * 50),
            average_buy_price=50000 + (i * 10000),
            current_price=55000 + (i * 10000),
            stop_loss_price=45000 + (i * 10000),
            take_profit_price=65000 + (i * 10000),
        )
        positions.append(position)
        integration_db_session.add(position)

    integration_db_session.commit()

    return positions


@pytest.fixture
def sample_watchlist(integration_db_session, sample_stocks) -> list[Watchlist]:
    """
    Create sample watchlist data for testing.
    """
    items = []
    user_id = "test_user_123"

    for stock in sample_stocks:
        item = Watchlist(
            user_id=user_id,
            stock_id=stock.id,
            target_price=60000,
            current_price=50000,
            price_change_percent=2.5,
            score=75.0,
            notes=f"Watching {stock.name}",
        )
        items.append(item)
        integration_db_session.add(item)

    integration_db_session.commit()

    return items


@pytest.fixture
def api_client():
    """
    Provide a requests session configured for API testing.
    """
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
    })

    yield session

    session.close()


@pytest.fixture
def test_user_id() -> str:
    """Provide a consistent test user ID."""
    return "test_user_123"


@pytest.fixture
def test_timeout() -> int:
    """Provide a reasonable timeout for API requests."""
    return 30  # seconds
