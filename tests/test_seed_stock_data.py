"""
Unit tests for Data Seeding Script.

Tests the DataSeeder class and its methods with mocked collectors and database.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
import sys
from pathlib import Path

# Add scripts directory to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.seed_stock_data import DataSeeder, DEFAULT_STOCK_TICKERS
from shared.database.models import Stock, StockPrice, FundamentalIndicator


class TestDataSeeder:
    """Test suite for DataSeeder class."""

    @pytest.fixture
    def seeder(self):
        """Create DataSeeder instance with dry_run=True."""
        return DataSeeder(days=30, dry_run=True)

    @pytest.fixture
    def seeder_with_mocks(self):
        """Create DataSeeder instance with mocked collectors."""
        with patch('scripts.seed_stock_data.StockCodeCollector') as mock_stock_collector, \
             patch('scripts.seed_stock_data.PriceCollector') as mock_price_collector, \
             patch('scripts.seed_stock_data.FundamentalCollector') as mock_fund_collector:

            seeder = DataSeeder(days=30, dry_run=False)
            seeder.stock_code_collector = mock_stock_collector.return_value
            seeder.price_collector = mock_price_collector.return_value
            seeder.fundamental_collector = mock_fund_collector.return_value

            yield seeder

    def test_initialization_with_defaults(self):
        """Test DataSeeder initialization with default values."""
        seeder = DataSeeder()

        assert seeder.days == 365
        assert seeder.dry_run is False
        assert seeder.skip_prices is False
        assert seeder.skip_fundamentals is False
        assert seeder.end_date is not None
        assert seeder.start_date is not None

    def test_initialization_with_custom_values(self):
        """Test DataSeeder initialization with custom values."""
        seeder = DataSeeder(
            days=100,
            dry_run=True,
            skip_prices=True,
            skip_fundamentals=True
        )

        assert seeder.days == 100
        assert seeder.dry_run is True
        assert seeder.skip_prices is True
        assert seeder.skip_fundamentals is True

    def test_initialization_date_calculation(self):
        """Test that start_date and end_date are calculated correctly."""
        days = 30
        seeder = DataSeeder(days=days)

        # Check that the difference is approximately the specified days
        date_diff = (seeder.end_date - seeder.start_date).days
        assert date_diff == days

    def test_dry_run_mode(self, seeder):
        """Test that dry_run mode doesn't initialize collectors."""
        # In dry_run mode, collectors should not be initialized
        assert not hasattr(seeder, 'stock_code_collector')
        assert not hasattr(seeder, 'price_collector')
        assert not hasattr(seeder, 'fundamental_collector')

    @patch('scripts.seed_stock_data.get_db_session')
    def test_check_stock_exists_found(self, mock_get_db_session, seeder, test_db_session, sample_stock):
        """Test checking if a stock exists in the database (found)."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        result = seeder.check_stock_exists('005930', test_db_session)

        assert result is not None
        assert result.ticker == '005930'
        assert result.name_kr == '삼성전자'

    @patch('scripts.seed_stock_data.get_db_session')
    def test_check_stock_exists_not_found(self, mock_get_db_session, seeder, test_db_session):
        """Test checking if a stock exists in the database (not found)."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        result = seeder.check_stock_exists('INVALID', test_db_session)

        assert result is None

    @patch('scripts.seed_stock_data.get_db_session')
    def test_check_price_data_count_with_data(
        self,
        mock_get_db_session,
        seeder,
        test_db_session,
        sample_stock_prices
    ):
        """Test counting price data records for a stock with data."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        count = seeder.check_price_data_count('005930', test_db_session)

        assert count == 30  # sample_stock_prices creates 30 records

    @patch('scripts.seed_stock_data.get_db_session')
    def test_check_price_data_count_without_data(self, mock_get_db_session, seeder, test_db_session):
        """Test counting price data records for a stock without data."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        count = seeder.check_price_data_count('INVALID', test_db_session)

        assert count == 0

    @patch('scripts.seed_stock_data.get_db_session')
    def test_check_fundamental_data_exists_true(
        self,
        mock_get_db_session,
        seeder,
        test_db_session,
        sample_stock
    ):
        """Test checking if fundamental data exists (found)."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Add fundamental data
        fundamental = FundamentalIndicator(
            stock_id=sample_stock.id,
            date=datetime.now(),
            per=12.5,
            pbr=1.8
        )
        test_db_session.add(fundamental)
        test_db_session.commit()

        result = seeder.check_fundamental_data_exists('005930', test_db_session)

        assert result is True

    @patch('scripts.seed_stock_data.get_db_session')
    def test_check_fundamental_data_exists_false(
        self,
        mock_get_db_session,
        seeder,
        test_db_session
    ):
        """Test checking if fundamental data exists (not found)."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        result = seeder.check_fundamental_data_exists('INVALID', test_db_session)

        assert result is False

    def test_seed_stock_metadata_dry_run(self, seeder):
        """Test seeding stock metadata in dry_run mode."""
        tickers = ['005930', '000660']

        results = seeder.seed_stock_metadata(tickers)

        # Dry run should return all True without actually doing anything
        assert results == {'005930': True, '000660': True}

    @patch('scripts.seed_stock_data.get_db_session')
    def test_seed_stock_metadata_new_stock(
        self,
        mock_get_db_session,
        seeder_with_mocks,
        test_db_session
    ):
        """Test seeding metadata for a new stock."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock collect_single_stock to return success
        seeder_with_mocks.stock_code_collector.collect_single_stock.return_value = True

        tickers = ['005930']
        results = seeder_with_mocks.seed_stock_metadata(tickers)

        assert results['005930'] is True
        seeder_with_mocks.stock_code_collector.collect_single_stock.assert_called_once_with('005930')

    @patch('scripts.seed_stock_data.get_db_session')
    def test_seed_stock_metadata_existing_stock(
        self,
        mock_get_db_session,
        seeder_with_mocks,
        test_db_session,
        sample_stock
    ):
        """Test seeding metadata for an existing stock."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        tickers = ['005930']
        results = seeder_with_mocks.seed_stock_metadata(tickers)

        assert results['005930'] is True
        # Should not call collect_single_stock for existing stock
        seeder_with_mocks.stock_code_collector.collect_single_stock.assert_not_called()

    @patch('scripts.seed_stock_data.get_db_session')
    def test_seed_stock_metadata_collector_failure(
        self,
        mock_get_db_session,
        seeder_with_mocks,
        test_db_session
    ):
        """Test handling when stock collector fails."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock collect_single_stock to return failure
        seeder_with_mocks.stock_code_collector.collect_single_stock.return_value = False

        tickers = ['INVALID']
        results = seeder_with_mocks.seed_stock_metadata(tickers)

        assert results['INVALID'] is False

    def test_seed_price_data_dry_run(self, seeder):
        """Test seeding price data in dry_run mode."""
        tickers = ['005930', '000660']

        results = seeder.seed_price_data(tickers)

        # Dry run should return all 0 without actually doing anything
        assert results == {'005930': 0, '000660': 0}

    @patch('scripts.seed_stock_data.get_db_session')
    def test_seed_price_data_success(
        self,
        mock_get_db_session,
        seeder_with_mocks,
        test_db_session,
        sample_stock
    ):
        """Test successful price data seeding."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock price collector to return success
        seeder_with_mocks.price_collector.collect_prices_for_stock.return_value = 30

        tickers = ['005930']
        results = seeder_with_mocks.seed_price_data(tickers)

        assert results['005930'] == 30
        seeder_with_mocks.price_collector.collect_prices_for_stock.assert_called_once()

    @patch('scripts.seed_stock_data.get_db_session')
    def test_seed_price_data_skips_sufficient_data(
        self,
        mock_get_db_session,
        seeder_with_mocks,
        test_db_session,
        sample_stock_prices
    ):
        """Test that seeding skips stocks with sufficient existing data."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        tickers = ['005930']
        results = seeder_with_mocks.seed_price_data(tickers)

        # Should skip because sample_stock_prices creates 30 records (100% of requested 30 days)
        assert results['005930'] == 30
        # Should not call price collector
        seeder_with_mocks.price_collector.collect_prices_for_stock.assert_not_called()

    @patch('scripts.seed_stock_data.get_db_session')
    def test_seed_price_data_collector_failure(
        self,
        mock_get_db_session,
        seeder_with_mocks,
        test_db_session,
        sample_stock
    ):
        """Test handling when price collector fails."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock price collector to return failure
        seeder_with_mocks.price_collector.collect_prices_for_stock.return_value = 0

        tickers = ['005930']
        results = seeder_with_mocks.seed_price_data(tickers)

        assert results['005930'] == 0

    def test_seed_fundamental_data_dry_run(self, seeder):
        """Test seeding fundamental data in dry_run mode."""
        tickers = ['005930', '000660']

        results = seeder.seed_fundamental_data(tickers)

        # Dry run should return all True without actually doing anything
        assert results == {'005930': True, '000660': True}

    @patch('scripts.seed_stock_data.get_db_session')
    def test_seed_fundamental_data_success(
        self,
        mock_get_db_session,
        seeder_with_mocks,
        test_db_session,
        sample_stock
    ):
        """Test successful fundamental data seeding."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock fundamental collector to return success
        seeder_with_mocks.fundamental_collector.collect_fundamentals_for_stock.return_value = True

        tickers = ['005930']
        results = seeder_with_mocks.seed_fundamental_data(tickers)

        assert results['005930'] is True
        seeder_with_mocks.fundamental_collector.collect_fundamentals_for_stock.assert_called_once_with('005930')

    @patch('scripts.seed_stock_data.get_db_session')
    def test_seed_fundamental_data_skips_existing(
        self,
        mock_get_db_session,
        seeder_with_mocks,
        test_db_session,
        sample_stock
    ):
        """Test that seeding skips stocks with existing fundamental data."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Add fundamental data
        fundamental = FundamentalIndicator(
            stock_id=sample_stock.id,
            date=datetime.now(),
            per=12.5
        )
        test_db_session.add(fundamental)
        test_db_session.commit()

        tickers = ['005930']
        results = seeder_with_mocks.seed_fundamental_data(tickers)

        assert results['005930'] is True
        # Should not call fundamental collector
        seeder_with_mocks.fundamental_collector.collect_fundamentals_for_stock.assert_not_called()

    @patch('scripts.seed_stock_data.get_db_session')
    def test_seed_fundamental_data_collector_failure(
        self,
        mock_get_db_session,
        seeder_with_mocks,
        test_db_session,
        sample_stock
    ):
        """Test handling when fundamental collector fails."""
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock fundamental collector to return failure
        seeder_with_mocks.fundamental_collector.collect_fundamentals_for_stock.return_value = False

        tickers = ['005930']
        results = seeder_with_mocks.seed_fundamental_data(tickers)

        assert results['005930'] is False

    @patch.object(DataSeeder, 'seed_fundamental_data')
    @patch.object(DataSeeder, 'seed_price_data')
    @patch.object(DataSeeder, 'seed_stock_metadata')
    def test_seed_complete_workflow(
        self,
        mock_seed_metadata,
        mock_seed_prices,
        mock_seed_fundamentals,
        seeder_with_mocks
    ):
        """Test complete seeding workflow."""
        # Mock successful results
        mock_seed_metadata.return_value = {'005930': True, '000660': True}
        mock_seed_prices.return_value = {'005930': 30, '000660': 30}
        mock_seed_fundamentals.return_value = {'005930': True, '000660': True}

        tickers = ['005930', '000660']
        results = seeder_with_mocks.seed(tickers)

        # Verify all steps were called
        mock_seed_metadata.assert_called_once_with(tickers)
        mock_seed_prices.assert_called_once()
        mock_seed_fundamentals.assert_called_once()

        # Check results structure
        assert 'stock_metadata' in results
        assert 'price_data' in results
        assert 'fundamental_data' in results

    @patch.object(DataSeeder, 'seed_stock_metadata')
    def test_seed_aborts_if_no_stocks_successful(
        self,
        mock_seed_metadata,
        seeder_with_mocks
    ):
        """Test that seeding aborts if no stocks are successfully seeded."""
        # Mock all stocks failing
        mock_seed_metadata.return_value = {'005930': False, '000660': False}

        tickers = ['005930', '000660']
        results = seeder_with_mocks.seed(tickers)

        # Should only have stock_metadata results, others should be empty
        assert len(results['stock_metadata']) == 2
        assert len(results['price_data']) == 0
        assert len(results['fundamental_data']) == 0

    @patch.object(DataSeeder, 'seed_price_data')
    @patch.object(DataSeeder, 'seed_stock_metadata')
    def test_seed_with_skip_prices(
        self,
        mock_seed_metadata,
        mock_seed_prices,
        seeder_with_mocks
    ):
        """Test seeding with skip_prices option."""
        seeder_with_mocks.skip_prices = True

        mock_seed_metadata.return_value = {'005930': True}

        tickers = ['005930']
        results = seeder_with_mocks.seed(tickers)

        # Price seeding should not be called
        mock_seed_prices.assert_not_called()
        assert len(results['price_data']) == 0

    @patch.object(DataSeeder, 'seed_fundamental_data')
    @patch.object(DataSeeder, 'seed_price_data')
    @patch.object(DataSeeder, 'seed_stock_metadata')
    def test_seed_with_skip_fundamentals(
        self,
        mock_seed_metadata,
        mock_seed_prices,
        mock_seed_fundamentals,
        seeder_with_mocks
    ):
        """Test seeding with skip_fundamentals option."""
        seeder_with_mocks.skip_fundamentals = True

        mock_seed_metadata.return_value = {'005930': True}
        mock_seed_prices.return_value = {'005930': 30}

        tickers = ['005930']
        results = seeder_with_mocks.seed(tickers)

        # Fundamental seeding should not be called
        mock_seed_fundamentals.assert_not_called()
        assert len(results['fundamental_data']) == 0

    def test_default_stock_tickers_list(self):
        """Test that DEFAULT_STOCK_TICKERS contains expected stocks."""
        # Verify the list is not empty
        assert len(DEFAULT_STOCK_TICKERS) > 0

        # Verify it contains some major stocks
        major_stocks = ['005930', '000660', '035420']  # Samsung, SK Hynix, NAVER
        for stock in major_stocks:
            assert stock in DEFAULT_STOCK_TICKERS

        # Verify all tickers are strings
        for ticker in DEFAULT_STOCK_TICKERS:
            assert isinstance(ticker, str)
            assert len(ticker) == 6  # Korean stock tickers are 6 digits

    @patch.object(DataSeeder, 'seed_fundamental_data')
    @patch.object(DataSeeder, 'seed_price_data')
    @patch.object(DataSeeder, 'seed_stock_metadata')
    def test_seed_filters_successful_tickers(
        self,
        mock_seed_metadata,
        mock_seed_prices,
        mock_seed_fundamentals,
        seeder_with_mocks
    ):
        """Test that only successfully seeded stocks are used for price/fundamental collection."""
        # Mock metadata seeding with partial success
        mock_seed_metadata.return_value = {
            '005930': True,
            '000660': False,  # Failed
            '035420': True
        }

        mock_seed_prices.return_value = {'005930': 30, '035420': 30}
        mock_seed_fundamentals.return_value = {'005930': True, '035420': True}

        tickers = ['005930', '000660', '035420']
        results = seeder_with_mocks.seed(tickers)

        # Price and fundamental seeding should only be called with successful tickers
        price_call_args = mock_seed_prices.call_args[0][0]
        fund_call_args = mock_seed_fundamentals.call_args[0][0]

        assert '005930' in price_call_args
        assert '035420' in price_call_args
        assert '000660' not in price_call_args

        assert '005930' in fund_call_args
        assert '035420' in fund_call_args
        assert '000660' not in fund_call_args

    def test_date_range_calculation(self):
        """Test that date range is calculated correctly for different days values."""
        test_cases = [
            (30, 30),
            (90, 90),
            (365, 365),
            (200, 200)
        ]

        for days, expected_days in test_cases:
            seeder = DataSeeder(days=days)
            actual_days = (seeder.end_date - seeder.start_date).days
            assert actual_days == expected_days
