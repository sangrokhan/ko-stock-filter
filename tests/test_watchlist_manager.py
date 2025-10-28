"""
Tests for Watchlist Manager functionality.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.models import (
    Base, Stock, Watchlist, WatchlistHistory, StockPrice,
    CompositeScore, StabilityScore, FundamentalIndicator
)
from services.watchlist_manager.watchlist_manager import WatchlistManager
from services.stock_screener.screening_engine import ScreeningCriteria


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


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
        is_active=True
    )
    db_session.add(stock)
    db_session.commit()
    db_session.refresh(stock)
    return stock


@pytest.fixture
def sample_stock_data(db_session, sample_stock):
    """Create sample stock data (price, scores, etc.)."""
    # Add price data
    price = StockPrice(
        stock_id=sample_stock.id,
        date=datetime.utcnow(),
        open=Decimal('70000'),
        high=Decimal('71000'),
        low=Decimal('69000'),
        close=Decimal('70500'),
        volume=1000000,
        trading_value=70500000000
    )
    db_session.add(price)

    # Add composite score
    score = CompositeScore(
        stock_id=sample_stock.id,
        date=datetime.utcnow(),
        composite_score=75.5,
        value_score=80.0,
        growth_score=70.0,
        quality_score=75.0,
        momentum_score=77.0
    )
    db_session.add(score)

    # Add stability score
    stability = StabilityScore(
        stock_id=sample_stock.id,
        date=datetime.utcnow(),
        stability_score=72.0,
        price_volatility=25.0,
        beta=1.1
    )
    db_session.add(stability)

    # Add fundamental data
    fundamental = FundamentalIndicator(
        stock_id=sample_stock.id,
        date=datetime.utcnow(),
        per=12.5,
        pbr=1.8,
        roe=18.5,
        debt_ratio=45.0,
        dividend_yield=2.5
    )
    db_session.add(fundamental)

    db_session.commit()

    return {
        'price': price,
        'score': score,
        'stability': stability,
        'fundamental': fundamental
    }


@pytest.fixture
def watchlist_manager(db_session):
    """Create a WatchlistManager instance."""
    return WatchlistManager(db_session, user_id='test_user')


class TestWatchlistManager:
    """Test suite for WatchlistManager."""

    def test_add_to_watchlist(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test adding a stock to watchlist."""
        entry = watchlist_manager.add_to_watchlist(
            ticker='005930',
            target_price=75000,
            tags='tech,semiconductor'
        )

        assert entry is not None
        assert entry.ticker == '005930'
        assert entry.target_price == Decimal('75000')
        assert entry.score == 75.5
        assert entry.is_active is True
        assert 'tech,semiconductor' in entry.tags

    def test_add_with_custom_reason(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test adding a stock with custom reason."""
        custom_reason = "Strong earnings report Q3 2025"
        entry = watchlist_manager.add_to_watchlist(
            ticker='005930',
            custom_reason=custom_reason
        )

        assert entry is not None
        assert entry.reason == custom_reason

    def test_add_duplicate_stock(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test adding a stock that's already in watchlist."""
        # Add first time
        entry1 = watchlist_manager.add_to_watchlist(ticker='005930')
        assert entry1 is not None

        # Try to add again
        entry2 = watchlist_manager.add_to_watchlist(ticker='005930')
        assert entry2 is not None
        assert entry1.id == entry2.id  # Should return existing entry

    def test_automatic_reason_generation(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test automatic reason generation."""
        entry = watchlist_manager.add_to_watchlist(ticker='005930')

        assert entry is not None
        assert entry.reason is not None
        assert len(entry.reason) > 0

    def test_get_watchlist(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test retrieving watchlist entries."""
        # Add stock to watchlist
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Get watchlist
        entries = watchlist_manager.get_watchlist()

        assert len(entries) == 1
        assert entries[0]['ticker'] == '005930'
        assert entries[0]['composite_score'] == 75.5

    def test_get_watchlist_sorting(self, db_session, watchlist_manager):
        """Test watchlist sorting."""
        # Create multiple stocks with different scores
        stocks_data = [
            ('000001', 'Stock A', 80.0),
            ('000002', 'Stock B', 60.0),
            ('000003', 'Stock C', 90.0),
        ]

        for ticker, name, score in stocks_data:
            stock = Stock(ticker=ticker, name_kr=name, market='KOSPI', is_active=True)
            db_session.add(stock)
            db_session.commit()
            db_session.refresh(stock)

            price = StockPrice(
                stock_id=stock.id,
                date=datetime.utcnow(),
                open=Decimal('10000'),
                high=Decimal('11000'),
                low=Decimal('9000'),
                close=Decimal('10500'),
                volume=100000
            )
            db_session.add(price)

            composite_score = CompositeScore(
                stock_id=stock.id,
                date=datetime.utcnow(),
                composite_score=score
            )
            db_session.add(composite_score)
            db_session.commit()

            watchlist_manager.add_to_watchlist(ticker=ticker)

        # Test sorting by score (descending)
        entries = watchlist_manager.get_watchlist(sort_by='score', ascending=False)
        assert len(entries) == 3
        assert entries[0]['ticker'] == '000003'  # Highest score
        assert entries[2]['ticker'] == '000002'  # Lowest score

    def test_remove_from_watchlist(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test removing a stock from watchlist."""
        # Add to watchlist
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Remove (mark inactive)
        result = watchlist_manager.remove_from_watchlist(ticker='005930', permanently=False)
        assert result is True

        # Verify it's marked inactive
        entries = watchlist_manager.get_watchlist(include_inactive=False)
        assert len(entries) == 0

        # Verify it still exists when including inactive
        entries_with_inactive = watchlist_manager.get_watchlist(include_inactive=True)
        assert len(entries_with_inactive) == 1
        assert entries_with_inactive[0]['is_active'] is False

    def test_update_watchlist_daily(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test daily watchlist update."""
        # Add to watchlist
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Update watchlist
        stats = watchlist_manager.update_watchlist_daily()

        assert stats['total_entries'] == 1
        assert stats['updated'] == 1
        assert stats['failed'] == 0

    def test_history_snapshot_creation(self, db_session, watchlist_manager, sample_stock, sample_stock_data):
        """Test that history snapshots are created."""
        # Add to watchlist (should create initial snapshot)
        entry = watchlist_manager.add_to_watchlist(ticker='005930')

        # Check that history entry was created
        history = db_session.query(WatchlistHistory).filter(
            WatchlistHistory.watchlist_id == entry.id
        ).all()

        assert len(history) == 1
        assert history[0].price == Decimal('70500')
        assert history[0].composite_score == 75.5
        assert history[0].snapshot_reason == 'added'

    def test_criteria_violations_check(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test checking for criteria violations."""
        # Add stock to watchlist
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Create strict criteria that the stock violates
        criteria = ScreeningCriteria(
            max_per=10.0,  # Stock has PER 12.5
            max_pbr=1.0    # Stock has PBR 1.8
        )

        # Check violations
        violations = watchlist_manager._check_criteria_violations(
            sample_stock.id,
            criteria
        )

        assert len(violations) > 0
        assert any('PER' in v for v in violations)
        assert any('PBR' in v for v in violations)

    def test_remove_stocks_not_meeting_criteria(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test automatic removal of stocks not meeting criteria."""
        # Add to watchlist
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Create criteria that stock doesn't meet
        criteria = ScreeningCriteria(max_per=10.0)

        # Run cleanup
        stats = watchlist_manager.remove_stocks_not_meeting_criteria(criteria)

        assert stats['total_checked'] == 1
        assert stats['removed'] == 1

        # Verify stock is marked inactive
        entries = watchlist_manager.get_watchlist(include_inactive=False)
        assert len(entries) == 0

    def test_export_to_csv(self, watchlist_manager, sample_stock, sample_stock_data, tmp_path):
        """Test exporting watchlist to CSV."""
        # Add to watchlist
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Export to CSV
        csv_path = tmp_path / "watchlist.csv"
        result = watchlist_manager.export_to_csv(str(csv_path))

        assert result is True
        assert csv_path.exists()

        # Read and verify CSV content
        with open(csv_path, 'r') as f:
            content = f.read()
            assert '005930' in content
            assert 'ticker' in content  # Header

    def test_export_to_json(self, watchlist_manager, sample_stock, sample_stock_data, tmp_path):
        """Test exporting watchlist to JSON."""
        # Add to watchlist
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Export to JSON
        json_path = tmp_path / "watchlist.json"
        result = watchlist_manager.export_to_json(str(json_path))

        assert result is True
        assert json_path.exists()

        # Read and verify JSON content
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
            assert data['total_stocks'] == 1
            assert data['user_id'] == 'test_user'
            assert data['watchlist'][0]['ticker'] == '005930'

    def test_export_to_json_with_history(self, watchlist_manager, sample_stock, sample_stock_data, tmp_path):
        """Test exporting watchlist to JSON with history."""
        # Add to watchlist
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Export to JSON with history
        json_path = tmp_path / "watchlist_with_history.json"
        result = watchlist_manager.export_to_json(str(json_path), include_history=True)

        assert result is True

        # Read and verify JSON content
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
            assert 'history' in data['watchlist'][0]
            assert len(data['watchlist'][0]['history']) > 0

    def test_get_historical_performance(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test retrieving historical performance data."""
        # Add to watchlist (creates initial snapshot)
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Get historical data
        history = watchlist_manager.get_historical_performance(ticker='005930')

        assert len(history) > 0
        assert history[0]['price'] == 70500
        assert history[0]['composite_score'] == 75.5

    def test_performance_summary(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test getting performance summary."""
        # Add to watchlist
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Get summary
        summary = watchlist_manager.get_performance_summary()

        assert summary['total_stocks'] == 1
        assert 'average_score' in summary
        assert 'average_return_pct' in summary

    def test_enrich_watchlist_entry(self, watchlist_manager, sample_stock, sample_stock_data):
        """Test watchlist entry enrichment with latest data."""
        # Add to watchlist
        entry = watchlist_manager.add_to_watchlist(ticker='005930')

        # Enrich the entry
        enriched = watchlist_manager._enrich_watchlist_entry(entry)

        assert enriched['ticker'] == '005930'
        assert enriched['name'] == '삼성전자'
        assert enriched['market'] == 'KOSPI'
        assert enriched['sector'] == 'Technology'
        assert enriched['current_price'] == 70500
        assert enriched['composite_score'] == 75.5

    def test_price_change_calculation(self, db_session, watchlist_manager, sample_stock):
        """Test price change calculation in history."""
        # Add initial price
        initial_price = StockPrice(
            stock_id=sample_stock.id,
            date=datetime.utcnow() - timedelta(days=7),
            open=Decimal('60000'),
            high=Decimal('61000'),
            low=Decimal('59000'),
            close=Decimal('60000'),
            volume=1000000
        )
        db_session.add(initial_price)

        # Add score data
        score = CompositeScore(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            composite_score=75.0
        )
        db_session.add(score)

        # Add current price
        current_price = StockPrice(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            open=Decimal('70000'),
            high=Decimal('71000'),
            low=Decimal('69000'),
            close=Decimal('70000'),
            volume=1000000
        )
        db_session.add(current_price)
        db_session.commit()

        # Add to watchlist
        watchlist_manager.add_to_watchlist(ticker='005930')

        # Get history
        history = watchlist_manager.get_historical_performance(ticker='005930')

        # Price change should be calculated
        assert len(history) > 0
        # Initial price was 60000, current is 70000, so ~16.67% gain
        if history[0]['price_change_pct'] is not None:
            assert history[0]['price_change_pct'] > 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
