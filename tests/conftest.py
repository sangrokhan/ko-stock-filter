"""
Pytest configuration and fixtures.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.database.models import (
    Base, Stock, StockPrice, TechnicalIndicator, FundamentalIndicator,
    CompositeScore, StabilityScore, Trade, Portfolio
)


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    # Drop all tables first to avoid conflicts
    Base.metadata.drop_all(bind=engine, checkfirst=True)
    # Now create all tables
    Base.metadata.create_all(bind=engine, checkfirst=True)
    yield engine
    Base.metadata.drop_all(bind=engine, checkfirst=True)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = SessionLocal()
    yield session

    # Clean up all data after each test
    session.rollback()  # Rollback any uncommitted changes
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
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


@pytest.fixture
def sample_stock(test_db_session):
    """Create a sample stock in the database."""
    stock = Stock(
        ticker='005930',
        name_kr='삼성전자',
        name_en='Samsung Electronics',
        market='KOSPI',
        sector='Technology',
        industry='Semiconductors',
        market_cap=500000000000000,
        listed_shares=5969782550,
        is_active=True
    )
    test_db_session.add(stock)
    test_db_session.commit()
    return stock


@pytest.fixture
def sample_stock_prices(test_db_session, sample_stock):
    """Create sample price data in the database."""
    prices = []
    base_date = datetime.now() - timedelta(days=30)
    base_price = 70000

    for i in range(30):
        price = StockPrice(
            stock_id=sample_stock.id,
            date=base_date + timedelta(days=i),
            open=Decimal(str(base_price + i * 100)),
            high=Decimal(str(base_price + i * 100 + 1000)),
            low=Decimal(str(base_price + i * 100 - 1000)),
            close=Decimal(str(base_price + i * 100)),
            volume=10000000 + i * 100000,
            trading_value=700000000000 + i * 1000000000,
            adjusted_close=Decimal(str(base_price + i * 100)),
            change_pct=0.5
        )
        prices.append(price)
        test_db_session.add(price)

    test_db_session.commit()
    return prices


@pytest.fixture
def sample_fundamental_data():
    """Sample fundamental data for testing."""
    return {
        'per': 12.5,
        'pbr': 1.8,
        'eps': 5600,
        'bps': 58000,
        'roe': 15.0,
        'roa': 10.0,
        'debt_ratio': 35.0,
        'debt_to_equity': 0.5,
        'current_ratio': 2.0,
        'revenue': 280000000000000,
        'operating_profit': 45000000000000,
        'net_income': 33500000000000,
        'operating_margin': 16.0,
        'net_margin': 12.0,
        'revenue_growth': 12.0,
        'earnings_growth': 15.0,
        'dividend_yield': 2.5
    }


@pytest.fixture
def sample_technical_data():
    """Sample technical indicator data for testing."""
    return {
        'sma_20': 68000.0,
        'sma_50': 65000.0,
        'sma_200': 62000.0,
        'ema_12': 69000.0,
        'ema_26': 66000.0,
        'rsi_14': 55.0,
        'rsi_9': 58.0,
        'macd': 150.0,
        'macd_signal': 120.0,
        'macd_histogram': 30.0,
        'bollinger_upper': 75000.0,
        'bollinger_middle': 70000.0,
        'bollinger_lower': 65000.0,
        'obv': 150000000,
        'volume_ma_20': 11000000,
        'atr': 1500.0,
        'stochastic_k': 60.0,
        'stochastic_d': 55.0
    }


@pytest.fixture
def sample_price_dataframe():
    """Sample price DataFrame for testing (pandas format)."""
    dates = pd.date_range(end=datetime.now(), periods=250, freq='D')
    base_price = 50000
    prices = []
    volumes = []

    for i in range(250):
        trend = i * 100
        noise = np.random.normal(0, 1000)
        price = base_price + trend + noise
        prices.append(price)
        volumes.append(np.random.randint(1000000, 5000000))

    df = pd.DataFrame({
        'date': dates,
        'open': [p * 0.99 for p in prices],
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': volumes,
    })

    df.set_index('date', inplace=True)
    return df


@pytest.fixture
def mock_fdr_data():
    """Mock FinanceDataReader data."""
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    data = {
        'Date': dates,
        'Open': [70000 + i * 100 for i in range(30)],
        'High': [71000 + i * 100 for i in range(30)],
        'Low': [69000 + i * 100 for i in range(30)],
        'Close': [70000 + i * 100 for i in range(30)],
        'Volume': [10000000 + i * 100000 for i in range(30)],
        'Adj Close': [70000 + i * 100 for i in range(30)]
    }
    df = pd.DataFrame(data)
    df.set_index('Date', inplace=True)
    return df


@pytest.fixture
def mock_pykrx_fundamental():
    """Mock pykrx fundamental data."""
    return pd.DataFrame({
        'BPS': [58000],
        'PER': [12.5],
        'PBR': [1.8],
        'EPS': [5600],
        'DIV': [2.5],
        'DPS': [1400]
    }, index=['005930'])


@pytest.fixture
def mock_pykrx_market_cap():
    """Mock pykrx market cap data."""
    return pd.DataFrame({
        '시가총액': [500000000000000],
        '상장주식수': [5969782550]
    }, index=['005930'])
