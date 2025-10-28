"""
Tests for Trading Signal Generator.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from shared.database.models import (
    Base, Stock, StockPrice, CompositeScore, TechnicalIndicator,
    FundamentalIndicator, Portfolio
)
from services.trading_engine.signal_generator import (
    TradingSignalGenerator, SignalType, SignalStrength, OrderType
)


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_stock(db_session):
    """Create sample stock for testing."""
    stock = Stock(
        ticker='005930',
        name_kr='삼성전자',
        name_en='Samsung Electronics',
        market='KOSPI',
        sector='Technology',
        industry='Semiconductors',
        market_cap=500_000_000_000_000,
        is_active=True
    )
    db_session.add(stock)
    db_session.commit()
    return stock


@pytest.fixture
def sample_price_data(db_session, sample_stock):
    """Create sample price data."""
    prices = []
    base_price = 70000
    base_date = datetime.now() - timedelta(days=30)

    for i in range(30):
        price = base_price + (i * 100)  # Uptrend
        volume = 10_000_000 + (i * 100_000)  # Increasing volume

        price_data = StockPrice(
            stock_id=sample_stock.id,
            date=base_date + timedelta(days=i),
            open=Decimal(str(price - 500)),
            high=Decimal(str(price + 500)),
            low=Decimal(str(price - 1000)),
            close=Decimal(str(price)),
            volume=volume,
            adjusted_close=Decimal(str(price)),
            trading_value=int(price * volume)
        )
        prices.append(price_data)
        db_session.add(price_data)

    db_session.commit()
    return prices


@pytest.fixture
def sample_composite_score(db_session, sample_stock):
    """Create sample composite score."""
    score = CompositeScore(
        stock_id=sample_stock.id,
        date=datetime.now(),
        value_score=75.0,
        growth_score=70.0,
        quality_score=80.0,
        momentum_score=65.0,
        composite_score=72.5,
        percentile_rank=85.0,
        per_score=80.0,
        pbr_score=75.0,
        roe_score=85.0,
        rsi_score=60.0,
        price_trend_score=70.0,
        data_quality_score=90.0,
        missing_value_count=0,
        total_metric_count=20
    )
    db_session.add(score)
    db_session.commit()
    return score


@pytest.fixture
def sample_technical(db_session, sample_stock):
    """Create sample technical indicators."""
    tech = TechnicalIndicator(
        stock_id=sample_stock.id,
        date=datetime.now(),
        rsi_14=55.0,
        macd=150.0,
        macd_signal=120.0,
        macd_histogram=30.0,
        sma_20=68000.0,
        sma_50=65000.0,
        bollinger_upper=75000.0,
        bollinger_middle=70000.0,
        bollinger_lower=65000.0
    )
    db_session.add(tech)
    db_session.commit()
    return tech


@pytest.fixture
def sample_fundamental(db_session, sample_stock):
    """Create sample fundamental indicators."""
    fund = FundamentalIndicator(
        stock_id=sample_stock.id,
        date=datetime.now(),
        per=12.5,
        pbr=1.8,
        roe=15.0,
        debt_ratio=35.0,
        current_ratio=1.8,
        revenue_growth=12.0,
        earnings_growth=15.0,
        operating_margin=18.0,
        net_margin=12.0
    )
    db_session.add(fund)
    db_session.commit()
    return fund


@pytest.fixture
def signal_generator(db_session):
    """Create signal generator instance."""
    return TradingSignalGenerator(
        db=db_session,
        user_id='test_user',
        portfolio_value=100_000_000,
        risk_tolerance=2.0,
        max_position_size_pct=10.0,
        min_conviction_score=60.0,
        use_limit_orders=True
    )


class TestSignalGenerator:
    """Test suite for signal generator."""

    def test_initialization(self, signal_generator):
        """Test signal generator initialization."""
        assert signal_generator.user_id == 'test_user'
        assert signal_generator.portfolio_value == 100_000_000
        assert signal_generator.risk_tolerance == 2.0
        assert signal_generator.position_sizer is not None
        assert signal_generator.position_monitor is not None

    def test_generate_entry_signal(
        self,
        signal_generator,
        sample_stock,
        sample_price_data,
        sample_composite_score,
        sample_technical,
        sample_fundamental
    ):
        """Test entry signal generation."""
        signals = signal_generator.generate_entry_signals(
            candidate_tickers=['005930'],
            min_composite_score=60.0,
            min_momentum_score=50.0
        )

        assert len(signals) > 0
        signal = signals[0]

        # Check signal properties
        assert signal.ticker == '005930'
        assert signal.signal_type == SignalType.ENTRY_BUY
        assert signal.is_valid is True
        assert signal.current_price > 0
        assert signal.recommended_shares > 0
        assert signal.conviction_score is not None
        assert signal.conviction_score.total_score >= 60.0

        # Check order details
        assert signal.order_type in [OrderType.MARKET, OrderType.LIMIT]
        if signal.order_type == OrderType.LIMIT:
            assert signal.limit_price is not None
            assert signal.limit_price < signal.current_price

        # Check risk parameters
        assert signal.stop_loss_price is not None
        assert signal.take_profit_price is not None
        assert signal.stop_loss_price < signal.current_price
        assert signal.take_profit_price > signal.current_price

        # Check position sizing
        assert 0 < signal.position_pct <= 10.0  # Within max position size

    def test_conviction_score_calculation(
        self,
        signal_generator,
        sample_stock,
        sample_price_data,
        sample_composite_score,
        sample_technical,
        sample_fundamental
    ):
        """Test conviction score calculation."""
        conviction = signal_generator._calculate_conviction_score(
            sample_composite_score,
            sample_technical,
            sample_fundamental,
            sample_price_data[-1],
            sample_stock.id
        )

        # Check conviction score components
        assert 0 <= conviction.total_score <= 100
        assert 0 <= conviction.value_component <= 100
        assert 0 <= conviction.momentum_component <= 100
        assert 0 <= conviction.volume_component <= 100
        assert 0 <= conviction.quality_component <= 100

        # Check weights sum to 1
        total_weight = (
            conviction.weight_value +
            conviction.weight_momentum +
            conviction.weight_volume +
            conviction.weight_quality
        )
        assert abs(total_weight - 1.0) < 0.01

    def test_volume_score_calculation(
        self,
        signal_generator,
        sample_stock,
        sample_price_data
    ):
        """Test volume score calculation."""
        volume_score = signal_generator._calculate_volume_score(sample_stock.id)

        assert 0 <= volume_score <= 100
        # With increasing volume trend, should get high score
        assert volume_score > 50

    def test_signal_strength_determination(self, signal_generator):
        """Test signal strength determination."""
        # Very strong
        assert signal_generator._determine_signal_strength(90) == SignalStrength.VERY_STRONG

        # Strong
        assert signal_generator._determine_signal_strength(80) == SignalStrength.STRONG

        # Moderate
        assert signal_generator._determine_signal_strength(70) == SignalStrength.MODERATE

        # Weak
        assert signal_generator._determine_signal_strength(60) == SignalStrength.WEAK

    def test_urgency_determination(self, signal_generator):
        """Test urgency level determination."""
        assert signal_generator._determine_urgency(SignalStrength.VERY_STRONG) == "high"
        assert signal_generator._determine_urgency(SignalStrength.STRONG) == "normal"
        assert signal_generator._determine_urgency(SignalStrength.MODERATE) == "normal"
        assert signal_generator._determine_urgency(SignalStrength.WEAK) == "low"

    def test_exit_signal_generation_for_empty_portfolio(
        self,
        signal_generator
    ):
        """Test exit signal generation with no positions."""
        exit_signals = signal_generator.generate_exit_signals()

        # Should return empty list when no positions exist
        assert len(exit_signals) == 0

    def test_exit_signal_generation_with_position(
        self,
        db_session,
        signal_generator,
        sample_stock
    ):
        """Test exit signal generation with existing position."""
        # Create a position that triggers stop-loss
        position = Portfolio(
            user_id='test_user',
            ticker='005930',
            quantity=100,
            avg_price=Decimal('70000'),
            current_price=Decimal('60000'),  # Below stop-loss
            stop_loss_price=Decimal('63000'),
            take_profit_price=Decimal('84000'),
            unrealized_pnl=-1_000_000,
            unrealized_pnl_pct=-14.3
        )
        db_session.add(position)
        db_session.commit()

        exit_signals = signal_generator.generate_exit_signals()

        # Should generate exit signal due to stop-loss
        assert len(exit_signals) > 0
        signal = exit_signals[0]
        assert signal.signal_type == SignalType.EXIT_SELL
        assert signal.ticker == '005930'
        assert 'stop' in signal.reasons[0].lower() or 'loss' in signal.reasons[0].lower()

    def test_signal_validation(
        self,
        signal_generator,
        sample_stock,
        sample_price_data,
        sample_composite_score,
        sample_technical,
        sample_fundamental
    ):
        """Test signal validation."""
        signals = signal_generator.generate_entry_signals(
            candidate_tickers=['005930'],
            min_composite_score=60.0
        )

        assert len(signals) > 0
        signal = signals[0]

        # Signal should be validated during generation
        assert signal.is_valid is True

        # Check for validation warnings
        if signal.validation_warnings:
            # Warnings should be informative strings
            for warning in signal.validation_warnings:
                assert isinstance(warning, str)
                assert len(warning) > 0

    def test_position_sizing_with_kelly_criterion(
        self,
        signal_generator,
        sample_stock,
        sample_price_data,
        sample_composite_score,
        sample_technical,
        sample_fundamental
    ):
        """Test position sizing uses Kelly Criterion."""
        signals = signal_generator.generate_entry_signals(
            candidate_tickers=['005930']
        )

        if signals:
            signal = signals[0]

            # Should have Kelly fraction information
            assert signal.kelly_fraction is not None or signal.conviction_score is not None

            # Position size should be reasonable
            assert signal.position_value > 0
            assert signal.position_value <= signal_generator.portfolio_value

    def test_limit_order_pricing(
        self,
        signal_generator,
        sample_stock,
        sample_price_data,
        sample_composite_score,
        sample_technical,
        sample_fundamental
    ):
        """Test limit order pricing."""
        # Enable limit orders
        signal_generator.use_limit_orders = True
        signal_generator.limit_order_discount_pct = 1.0

        signals = signal_generator.generate_entry_signals(
            candidate_tickers=['005930']
        )

        if signals:
            signal = signals[0]

            if signal.order_type == OrderType.LIMIT:
                assert signal.limit_price is not None
                # Limit price should be below current price
                assert signal.limit_price < signal.current_price
                # Discount should be approximately correct
                expected_discount = signal.current_price * 0.01
                actual_discount = signal.current_price - signal.limit_price
                assert abs(actual_discount - expected_discount) < signal.current_price * 0.001

    def test_minimum_conviction_threshold(
        self,
        db_session,
        sample_stock,
        sample_price_data
    ):
        """Test minimum conviction score threshold."""
        # Create low-quality composite score
        low_score = CompositeScore(
            stock_id=sample_stock.id,
            date=datetime.now(),
            value_score=40.0,
            growth_score=35.0,
            quality_score=45.0,
            momentum_score=30.0,
            composite_score=37.5,
            data_quality_score=80.0
        )
        db_session.add(low_score)
        db_session.commit()

        generator = TradingSignalGenerator(
            db=db_session,
            user_id='test_user',
            portfolio_value=100_000_000,
            min_conviction_score=60.0
        )

        signals = generator.generate_entry_signals(
            candidate_tickers=['005930'],
            min_composite_score=30.0  # Lower threshold to allow evaluation
        )

        # Should not generate signals due to low conviction
        assert len(signals) == 0

    def test_signal_to_dict(
        self,
        signal_generator,
        sample_stock,
        sample_price_data,
        sample_composite_score,
        sample_technical,
        sample_fundamental
    ):
        """Test signal serialization to dictionary."""
        signals = signal_generator.generate_entry_signals(
            candidate_tickers=['005930']
        )

        if signals:
            signal = signals[0]
            signal_dict = signal.to_dict()

            # Check essential fields
            assert 'signal_id' in signal_dict
            assert 'ticker' in signal_dict
            assert 'signal_type' in signal_dict
            assert 'current_price' in signal_dict
            assert 'recommended_shares' in signal_dict
            assert 'conviction_score' in signal_dict
            assert 'reasons' in signal_dict

            # Check data types
            assert isinstance(signal_dict['ticker'], str)
            assert isinstance(signal_dict['current_price'], (int, float))
            assert isinstance(signal_dict['reasons'], list)

    def test_deteriorating_fundamentals_detection(
        self,
        db_session,
        signal_generator,
        sample_stock
    ):
        """Test detection of deteriorating fundamentals."""
        # Create position
        position = Portfolio(
            user_id='test_user',
            ticker='005930',
            quantity=100,
            avg_price=Decimal('70000'),
            current_price=Decimal('72000')
        )
        db_session.add(position)

        # Create current low score
        low_score = CompositeScore(
            stock_id=sample_stock.id,
            date=datetime.now(),
            value_score=35.0,
            growth_score=25.0,
            quality_score=30.0,
            momentum_score=20.0,
            composite_score=27.5
        )
        db_session.add(low_score)

        # Create historical high score
        historical_score = CompositeScore(
            stock_id=sample_stock.id,
            date=datetime.now() - timedelta(days=30),
            value_score=70.0,
            growth_score=65.0,
            quality_score=75.0,
            momentum_score=60.0,
            composite_score=67.5
        )
        db_session.add(historical_score)
        db_session.commit()

        exit_signals = signal_generator._check_deteriorating_fundamentals()

        # Should detect deteriorating fundamentals
        assert len(exit_signals) > 0
        signal = exit_signals[0]
        assert signal.signal_type == SignalType.EXIT_SELL
        assert 'deteriorat' in signal.notes.lower() or 'fundamental' in signal.notes.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
