"""
Unit tests for Stock Screener Service.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.models import (
    Base, Stock, StockPrice, FundamentalIndicator, StabilityScore
)
from shared.configs.config import Settings
from services.stock_screener.screening_engine import (
    StockScreeningEngine,
    ScreeningCriteria,
    ScreeningResult
)


@pytest.fixture
def db_session():
    """Create in-memory database session for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        database_url='sqlite:///:memory:',
        max_volatility_pct=40.0,
        max_per=50.0,
        max_pbr=5.0,
        max_debt_ratio_pct=200.0,
        min_avg_volume=100000,
        min_trading_value=100000000.0,
        undervalued_pbr_threshold=1.0,
        per_industry_avg_multiplier=1.0,
        min_price_history_days=60,
        min_volume_history_days=20
    )


@pytest.fixture
def sample_stock(db_session):
    """Create a sample stock for testing."""
    stock = Stock(
        ticker='005930',
        name_kr='삼성전자',
        name_en='Samsung Electronics',
        market='KOSPI',
        sector='Technology',
        industry='Semiconductors',
        market_cap=400000000000000,
        listed_shares=5969782550,
        is_active=True
    )
    db_session.add(stock)
    db_session.commit()
    return stock


@pytest.fixture
def sample_stock_with_data(db_session, sample_stock):
    """Create a sample stock with complete historical data."""
    # Add 90 days of price data
    base_date = datetime.now() - timedelta(days=90)
    for i in range(90):
        price = StockPrice(
            stock_id=sample_stock.id,
            date=base_date + timedelta(days=i),
            open=70000 + (i * 100),
            high=71000 + (i * 100),
            low=69000 + (i * 100),
            close=70000 + (i * 100),
            volume=10000000 + (i * 10000),
            trading_value=700000000000 + (i * 1000000000),
            adjusted_close=70000 + (i * 100),
            change_pct=0.5
        )
        db_session.add(price)

    # Add fundamental data
    fundamental = FundamentalIndicator(
        stock_id=sample_stock.id,
        date=datetime.now(),
        per=12.5,
        pbr=1.2,
        pcr=8.0,
        psr=1.5,
        roe=15.0,
        roa=10.0,
        debt_ratio=50.0,
        debt_to_equity=0.5,
        current_ratio=2.0,
        eps=5600,
        bps=58000,
        revenue=280000000000000,
        operating_profit=45000000000000,
        net_income=33500000000000
    )
    db_session.add(fundamental)

    # Add stability score
    stability = StabilityScore(
        stock_id=sample_stock.id,
        date=datetime.now(),
        price_volatility=0.25,  # 25% annualized
        price_volatility_score=80.0,
        returns_mean=0.001,
        returns_std=0.015,
        beta=1.05,
        beta_score=95.0,
        market_correlation=0.75,
        volume_stability=0.5,
        volume_stability_score=75.0,
        volume_mean=10000000,
        volume_std=5000000,
        earnings_consistency=0.85,
        earnings_consistency_score=85.0,
        debt_stability=0.90,
        debt_stability_score=90.0,
        stability_score=83.0
    )
    db_session.add(stability)

    db_session.commit()
    return sample_stock


@pytest.fixture
def high_volatility_stock(db_session):
    """Create a high volatility stock for testing."""
    stock = Stock(
        ticker='123456',
        name_kr='고변동주식',
        name_en='High Volatility Stock',
        market='KOSDAQ',
        sector='Technology',
        industry='Software',
        market_cap=100000000000,
        is_active=True
    )
    db_session.add(stock)
    db_session.commit()

    # Add price data
    base_date = datetime.now() - timedelta(days=90)
    for i in range(90):
        price = StockPrice(
            stock_id=stock.id,
            date=base_date + timedelta(days=i),
            open=10000,
            high=11000,
            low=9000,
            close=10000,
            volume=500000,
            trading_value=5000000000,
            adjusted_close=10000
        )
        db_session.add(price)

    # High volatility stability score
    stability = StabilityScore(
        stock_id=stock.id,
        date=datetime.now(),
        price_volatility=0.55,  # 55% - exceeds threshold
        price_volatility_score=30.0,
        stability_score=40.0
    )
    db_session.add(stability)

    db_session.commit()
    return stock


@pytest.fixture
def overvalued_stock(db_session):
    """Create an overvalued stock for testing."""
    stock = Stock(
        ticker='234567',
        name_kr='고평가주식',
        name_en='Overvalued Stock',
        market='KOSPI',
        sector='Finance',
        industry='Banking',
        market_cap=500000000000,
        is_active=True
    )
    db_session.add(stock)
    db_session.commit()

    # Add price data
    base_date = datetime.now() - timedelta(days=90)
    for i in range(90):
        price = StockPrice(
            stock_id=stock.id,
            date=base_date + timedelta(days=i),
            open=50000,
            high=51000,
            low=49000,
            close=50000,
            volume=200000,
            trading_value=10000000000,
            adjusted_close=50000
        )
        db_session.add(price)

    # Overvalued fundamental data
    fundamental = FundamentalIndicator(
        stock_id=stock.id,
        date=datetime.now(),
        per=75.0,  # Exceeds threshold of 50
        pbr=8.0,   # Exceeds threshold of 5
        roe=5.0,
        debt_ratio=50.0,
        eps=667,
        bps=6250
    )
    db_session.add(fundamental)

    # Add stability data
    stability = StabilityScore(
        stock_id=stock.id,
        date=datetime.now(),
        price_volatility=0.30,
        stability_score=70.0
    )
    db_session.add(stability)

    db_session.commit()
    return stock


@pytest.fixture
def unstable_company(db_session):
    """Create an unstable company (high debt) for testing."""
    stock = Stock(
        ticker='345678',
        name_kr='고부채기업',
        name_en='High Debt Company',
        market='KOSPI',
        sector='Manufacturing',
        industry='Steel',
        market_cap=200000000000,
        is_active=True
    )
    db_session.add(stock)
    db_session.commit()

    # Add price data
    base_date = datetime.now() - timedelta(days=90)
    for i in range(90):
        price = StockPrice(
            stock_id=stock.id,
            date=base_date + timedelta(days=i),
            open=20000,
            high=21000,
            low=19000,
            close=20000,
            volume=150000,
            trading_value=3000000000,
            adjusted_close=20000
        )
        db_session.add(price)

    # High debt fundamental data
    fundamental = FundamentalIndicator(
        stock_id=stock.id,
        date=datetime.now(),
        per=15.0,
        pbr=0.8,
        roe=3.0,
        debt_ratio=250.0,  # Exceeds threshold of 200%
        debt_to_equity=2.5,
        eps=1333,
        bps=25000
    )
    db_session.add(fundamental)

    # Add stability data
    stability = StabilityScore(
        stock_id=stock.id,
        date=datetime.now(),
        price_volatility=0.35,
        stability_score=60.0
    )
    db_session.add(stability)

    db_session.commit()
    return stock


@pytest.fixture
def low_liquidity_stock(db_session):
    """Create a low liquidity stock for testing."""
    stock = Stock(
        ticker='456789',
        name_kr='저유동성주식',
        name_en='Low Liquidity Stock',
        market='KONEX',
        sector='Services',
        industry='Retail',
        market_cap=50000000000,
        is_active=True
    )
    db_session.add(stock)
    db_session.commit()

    # Add price data with low volume
    base_date = datetime.now() - timedelta(days=90)
    for i in range(90):
        price = StockPrice(
            stock_id=stock.id,
            date=base_date + timedelta(days=i),
            open=5000,
            high=5100,
            low=4900,
            close=5000,
            volume=50000,  # Below minimum threshold
            trading_value=250000000,  # Below minimum threshold
            adjusted_close=5000
        )
        db_session.add(price)

    # Add fundamental data
    fundamental = FundamentalIndicator(
        stock_id=stock.id,
        date=datetime.now(),
        per=10.0,
        pbr=0.9,
        roe=8.0,
        debt_ratio=80.0,
        eps=500,
        bps=5556
    )
    db_session.add(fundamental)

    # Add stability data
    stability = StabilityScore(
        stock_id=stock.id,
        date=datetime.now(),
        price_volatility=0.30,
        stability_score=70.0
    )
    db_session.add(stability)

    db_session.commit()
    return stock


@pytest.fixture
def undervalued_stock(db_session):
    """Create an undervalued stock for testing."""
    stock = Stock(
        ticker='567890',
        name_kr='저평가주식',
        name_en='Undervalued Stock',
        market='KOSPI',
        sector='Technology',
        industry='Semiconductors',
        market_cap=150000000000000,
        is_active=True
    )
    db_session.add(stock)
    db_session.commit()

    # Add price data
    base_date = datetime.now() - timedelta(days=90)
    for i in range(90):
        price = StockPrice(
            stock_id=stock.id,
            date=base_date + timedelta(days=i),
            open=30000,
            high=31000,
            low=29000,
            close=30000,
            volume=5000000,
            trading_value=150000000000,
            adjusted_close=30000
        )
        db_session.add(price)

    # Undervalued fundamental data
    fundamental = FundamentalIndicator(
        stock_id=stock.id,
        date=datetime.now(),
        per=8.0,   # Low PER
        pbr=0.7,   # Below 1.0 threshold
        roe=18.0,
        debt_ratio=30.0,
        eps=3750,
        bps=42857
    )
    db_session.add(fundamental)

    # Add stability data
    stability = StabilityScore(
        stock_id=stock.id,
        date=datetime.now(),
        price_volatility=0.20,
        stability_score=85.0
    )
    db_session.add(stability)

    db_session.commit()
    return stock


class TestStockScreeningEngine:
    """Test cases for StockScreeningEngine."""

    def test_initialization(self, db_session, settings):
        """Test engine initialization."""
        engine = StockScreeningEngine(db_session, settings)
        assert engine.db == db_session
        assert engine.settings == settings

    def test_screen_stocks_default_criteria(
        self, db_session, settings, sample_stock_with_data
    ):
        """Test screening with default criteria."""
        engine = StockScreeningEngine(db_session, settings)
        results = engine.screen_stocks()

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].ticker == '005930'

    def test_filter_high_volatility(
        self, db_session, settings, sample_stock_with_data, high_volatility_stock
    ):
        """Test filtering out high volatility stocks."""
        engine = StockScreeningEngine(db_session, settings)
        criteria = ScreeningCriteria(max_volatility_pct=40.0)
        results = engine.screen_stocks(criteria)

        # Only the low volatility stock should pass
        tickers = [r.ticker for r in results]
        assert '005930' in tickers
        assert '123456' not in tickers

    def test_filter_overvalued(
        self, db_session, settings, sample_stock_with_data, overvalued_stock
    ):
        """Test filtering out overvalued stocks."""
        engine = StockScreeningEngine(db_session, settings)
        criteria = ScreeningCriteria(max_per=50.0, max_pbr=5.0)
        results = engine.screen_stocks(criteria)

        # Only reasonably valued stock should pass
        tickers = [r.ticker for r in results]
        assert '005930' in tickers
        assert '234567' not in tickers

    def test_filter_unstable_companies(
        self, db_session, settings, sample_stock_with_data, unstable_company
    ):
        """Test filtering out unstable companies."""
        engine = StockScreeningEngine(db_session, settings)
        criteria = ScreeningCriteria(max_debt_ratio_pct=200.0)
        results = engine.screen_stocks(criteria)

        # Only stable company should pass
        tickers = [r.ticker for r in results]
        assert '005930' in tickers
        assert '345678' not in tickers

    def test_filter_low_liquidity(
        self, db_session, settings, sample_stock_with_data, low_liquidity_stock
    ):
        """Test filtering out low liquidity stocks."""
        engine = StockScreeningEngine(db_session, settings)
        criteria = ScreeningCriteria(
            min_avg_volume=100000,
            min_trading_value=100000000.0
        )
        results = engine.screen_stocks(criteria)

        # Only liquid stock should pass
        tickers = [r.ticker for r in results]
        assert '005930' in tickers
        assert '456789' not in tickers

    def test_identify_undervalued(
        self, db_session, settings, sample_stock_with_data, undervalued_stock
    ):
        """Test identifying undervalued stocks."""
        engine = StockScreeningEngine(db_session, settings)
        results = engine.identify_undervalued_stocks()

        # Find undervalued stock
        undervalued = [r for r in results if r.is_undervalued]
        assert len(undervalued) > 0

        # Check that undervalued stock is identified
        undervalued_tickers = [r.ticker for r in undervalued]
        assert '567890' in undervalued_tickers

    def test_all_filters_combined(
        self,
        db_session,
        settings,
        sample_stock_with_data,
        high_volatility_stock,
        overvalued_stock,
        unstable_company,
        low_liquidity_stock
    ):
        """Test applying all filters together."""
        engine = StockScreeningEngine(db_session, settings)
        criteria = ScreeningCriteria(
            max_volatility_pct=40.0,
            max_per=50.0,
            max_pbr=5.0,
            max_debt_ratio_pct=200.0,
            min_avg_volume=100000,
            min_trading_value=100000000.0
        )
        results = engine.screen_stocks(criteria)

        # Only the good stock should pass all filters
        assert len(results) == 1
        assert results[0].ticker == '005930'

    def test_market_filter(self, db_session, settings, sample_stock_with_data):
        """Test filtering by market."""
        engine = StockScreeningEngine(db_session, settings)

        # Filter for KOSPI only
        criteria = ScreeningCriteria(markets=['KOSPI'])
        results = engine.screen_stocks(criteria)
        assert all(r.market == 'KOSPI' for r in results)

        # Filter for KOSDAQ only (should return empty)
        criteria = ScreeningCriteria(markets=['KOSDAQ'])
        results = engine.screen_stocks(criteria)
        assert len(results) == 0

    def test_screening_result_structure(
        self, db_session, settings, sample_stock_with_data
    ):
        """Test that screening result has correct structure."""
        engine = StockScreeningEngine(db_session, settings)
        results = engine.screen_stocks()

        assert len(results) > 0
        result = results[0]

        assert isinstance(result, ScreeningResult)
        assert result.ticker is not None
        assert result.name_kr is not None
        assert result.market is not None
        assert result.current_price is not None
        assert result.per is not None
        assert result.pbr is not None
        assert result.debt_ratio is not None
        assert result.avg_volume is not None
        assert result.volatility_pct is not None
        assert result.stability_score is not None

    def test_screening_summary(
        self,
        db_session,
        settings,
        sample_stock_with_data,
        undervalued_stock
    ):
        """Test screening summary generation."""
        engine = StockScreeningEngine(db_session, settings)
        results = engine.screen_stocks()
        summary = engine.get_screening_summary(results)

        assert 'total_stocks' in summary
        assert 'undervalued_count' in summary
        assert 'markets' in summary
        assert 'sectors' in summary
        assert summary['total_stocks'] > 0

    def test_no_data_filtering(self, db_session, settings, sample_stock):
        """Test that stocks without data are filtered out."""
        engine = StockScreeningEngine(db_session, settings)
        results = engine.screen_stocks()

        # Stock without price/fundamental data should not appear
        assert len(results) == 0

    def test_insufficient_price_history(self, db_session, settings, sample_stock):
        """Test that stocks with insufficient history are filtered."""
        # Add only 10 days of price data (below minimum)
        base_date = datetime.now() - timedelta(days=10)
        for i in range(10):
            price = StockPrice(
                stock_id=sample_stock.id,
                date=base_date + timedelta(days=i),
                open=70000,
                high=71000,
                low=69000,
                close=70000,
                volume=10000000,
                trading_value=700000000000,
                adjusted_close=70000
            )
            db_session.add(price)
        db_session.commit()

        engine = StockScreeningEngine(db_session, settings)
        criteria = ScreeningCriteria(min_price_history_days=60)
        results = engine.screen_stocks(criteria)

        # Should be filtered out due to insufficient history
        assert len(results) == 0


class TestScreeningCriteria:
    """Test cases for ScreeningCriteria dataclass."""

    def test_default_criteria(self):
        """Test default criteria initialization."""
        criteria = ScreeningCriteria()
        assert criteria.max_volatility_pct is None
        assert criteria.max_per is None
        assert criteria.min_price_history_days == 60

    def test_custom_criteria(self):
        """Test custom criteria initialization."""
        criteria = ScreeningCriteria(
            max_volatility_pct=30.0,
            max_per=40.0,
            max_pbr=3.0,
            min_avg_volume=500000
        )
        assert criteria.max_volatility_pct == 30.0
        assert criteria.max_per == 40.0
        assert criteria.max_pbr == 3.0
        assert criteria.min_avg_volume == 500000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
