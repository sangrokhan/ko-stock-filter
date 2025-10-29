"""
Unit tests for Fundamental Collector with mocked external APIs.

Tests fundamental data collection from pykrx with proper mocking.
"""
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock

from services.data_collector.fundamental_collector import FundamentalCollector


class TestFundamentalCollector:
    """Test suite for FundamentalCollector."""

    @pytest.fixture
    def collector(self):
        """Create fundamental collector instance."""
        return FundamentalCollector()

    def test_initialization(self, collector):
        """Test collector initialization."""
        assert collector is not None
        assert collector.rate_limiter is not None

    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_fundamental_by_ticker')
    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_cap_by_ticker')
    def test_fetch_fundamental_data_success(
        self, mock_cap, mock_fund, collector, mock_pykrx_fundamental, mock_pykrx_market_cap
    ):
        """Test successful fundamental data fetch."""
        mock_fund.return_value = mock_pykrx_fundamental
        mock_cap.return_value = mock_pykrx_market_cap

        result = collector.fetch_fundamental_data('005930', '20240115')

        assert result is not None
        assert 'per' in result
        assert 'pbr' in result
        assert 'eps' in result
        assert 'bps' in result
        assert 'market_cap' in result
        assert 'listed_shares' in result
        assert result['per'] == 12.5
        assert result['pbr'] == 1.8

    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_fundamental_by_ticker')
    def test_fetch_fundamental_data_ticker_not_found(self, mock_fund, collector):
        """Test handling when ticker is not found."""
        # Return dataframe without the requested ticker
        mock_fund.return_value = pd.DataFrame({
            'BPS': [50000],
            'PER': [10.0],
            'PBR': [1.5],
            'EPS': [5000]
        }, index=['000000'])  # Different ticker

        result = collector.fetch_fundamental_data('005930', '20240115')

        # Should return None when ticker not in data
        assert result is None

    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_fundamental_by_ticker')
    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_cap_by_ticker')
    def test_fetch_fundamental_data_partial_failure(
        self, mock_cap, mock_fund, collector, mock_pykrx_fundamental
    ):
        """Test handling when market cap fetch fails but fundamental succeeds."""
        mock_fund.return_value = mock_pykrx_fundamental
        mock_cap.side_effect = Exception("Market cap error")

        result = collector.fetch_fundamental_data('005930', '20240115')

        # Should still return fundamental data
        assert result is not None
        assert 'per' in result
        assert 'pbr' in result
        # Market cap fields should be missing or zero
        assert result.get('market_cap', 0) == 0

    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_fundamental_by_ticker')
    def test_fetch_fundamental_data_complete_failure(self, mock_fund, collector):
        """Test handling when all fetches fail."""
        mock_fund.side_effect = Exception("API error")

        result = collector.fetch_fundamental_data('005930', '20240115')

        assert result is None

    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_fundamental_by_ticker')
    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_cap_by_ticker')
    def test_fetch_fundamental_data_default_date(
        self, mock_cap, mock_fund, collector, mock_pykrx_fundamental, mock_pykrx_market_cap
    ):
        """Test that date defaults to today."""
        mock_fund.return_value = mock_pykrx_fundamental
        mock_cap.return_value = mock_pykrx_market_cap

        result = collector.fetch_fundamental_data('005930')

        assert result is not None
        # Check that today's date was used
        today = datetime.now().strftime('%Y%m%d')
        mock_fund.assert_called_once_with(today, market="ALL")

    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_fundamental_by_ticker')
    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_cap_by_ticker')
    def test_fetch_all_fundamentals_bulk_success(
        self, mock_cap, mock_fund, collector
    ):
        """Test bulk fetch of all fundamentals."""
        # Create multi-stock dataframe
        fund_df = pd.DataFrame({
            'BPS': [58000, 45000, 30000],
            'PER': [12.5, 15.0, 20.0],
            'PBR': [1.8, 2.0, 2.5],
            'EPS': [5600, 4200, 3000],
            'DIV': [2.5, 3.0, 1.5],
            'DPS': [1400, 1260, 450]
        }, index=['005930', '000660', '035720'])

        cap_df = pd.DataFrame({
            '시가총액': [500000000000000, 300000000000000, 150000000000000],
            '상장주식수': [5969782550, 7000000000, 5000000000]
        }, index=['005930', '000660', '035720'])

        mock_fund.return_value = fund_df
        mock_cap.return_value = cap_df

        result = collector.fetch_all_fundamentals_bulk('20240115')

        assert result is not None
        assert len(result) == 3
        assert '005930' in result.index
        assert '000660' in result.index
        assert 'PER' in result.columns

    @patch('services.data_collector.fundamental_collector.pykrx_stock.get_market_fundamental_by_ticker')
    def test_fetch_all_fundamentals_bulk_failure(self, mock_fund, collector):
        """Test bulk fetch failure."""
        mock_fund.side_effect = Exception("Bulk fetch error")

        result = collector.fetch_all_fundamentals_bulk('20240115')

        assert result is None

    @patch.object(FundamentalCollector, 'fetch_fundamental_data')
    @patch.object(FundamentalCollector, '_save_fundamentals_to_db')
    def test_collect_fundamentals_for_stock_success(
        self, mock_save, mock_fetch, collector
    ):
        """Test successful fundamental collection for a single stock."""
        mock_fetch.return_value = {
            'per': 12.5,
            'pbr': 1.8,
            'eps': 5600,
            'bps': 58000
        }
        mock_save.return_value = True

        success = collector.collect_fundamentals_for_stock('005930', '20240115')

        assert success is True
        mock_fetch.assert_called_once_with('005930', '20240115')
        mock_save.assert_called_once()

    @patch.object(FundamentalCollector, 'fetch_fundamental_data')
    def test_collect_fundamentals_for_stock_no_data(self, mock_fetch, collector):
        """Test collection when no data is available."""
        mock_fetch.return_value = None

        success = collector.collect_fundamentals_for_stock('INVALID', '20240115')

        assert success is False

    def test_save_fundamentals_to_db_new_record(
        self, collector, test_db_session, sample_stock
    ):
        """Test saving new fundamental record to database."""
        fund_data = {
            'per': 12.5,
            'pbr': 1.8,
            'eps': 5600,
            'bps': 58000,
            'div_yield': 2.5,
            'dps': 1400
        }

        with patch('services.data_collector.fundamental_collector.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session

            success = collector._save_fundamentals_to_db('005930', '20240115', fund_data)

            assert success is True

            # Verify data was saved
            from shared.database.models import FundamentalIndicator
            saved_fund = test_db_session.query(FundamentalIndicator).filter(
                FundamentalIndicator.stock_id == sample_stock.id
            ).first()

            assert saved_fund is not None
            assert saved_fund.per == 12.5
            assert saved_fund.pbr == 1.8

    def test_save_fundamentals_to_db_update_existing(
        self, collector, test_db_session, sample_stock
    ):
        """Test updating existing fundamental record."""
        from shared.database.models import FundamentalIndicator

        # Create existing record
        existing = FundamentalIndicator(
            stock_id=sample_stock.id,
            date=datetime.strptime('20240115', '%Y%m%d'),
            per=10.0,
            pbr=1.5,
            eps=5000,
            bps=50000
        )
        test_db_session.add(existing)
        test_db_session.commit()

        # Update with new data
        fund_data = {
            'per': 12.5,
            'pbr': 1.8,
            'eps': 5600,
            'bps': 58000
        }

        with patch('services.data_collector.fundamental_collector.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session

            success = collector._save_fundamentals_to_db('005930', '20240115', fund_data)

            assert success is True

            # Verify data was updated
            updated = test_db_session.query(FundamentalIndicator).filter(
                FundamentalIndicator.stock_id == sample_stock.id
            ).first()

            assert updated.per == 12.5
            assert updated.pbr == 1.8

    def test_save_fundamentals_to_db_invalid_ticker(
        self, collector, test_db_session
    ):
        """Test saving fundamentals for non-existent ticker."""
        fund_data = {'per': 12.5, 'pbr': 1.8}

        with patch('services.data_collector.fundamental_collector.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session

            success = collector._save_fundamentals_to_db('INVALID', '20240115', fund_data)

            assert success is False


class TestFundamentalCollectorBulk:
    """Test bulk collection functionality."""

    @pytest.fixture
    def collector(self):
        """Create fundamental collector instance."""
        return FundamentalCollector()

    @patch.object(FundamentalCollector, 'fetch_all_fundamentals_bulk')
    @patch('services.data_collector.fundamental_collector.get_db_session')
    def test_collect_fundamentals_for_all_stocks(
        self, mock_session, mock_bulk_fetch, collector, test_db_session, sample_stock
    ):
        """Test collecting fundamentals for all stocks using bulk fetch."""
        # Create bulk fetch result
        bulk_data = pd.DataFrame({
            'BPS': [58000],
            'PER': [12.5],
            'PBR': [1.8],
            'EPS': [5600],
            'DIV': [2.5],
            'DPS': [1400],
            '시가총액': [500000000000000],
            '상장주식수': [5969782550]
        }, index=['005930'])

        mock_bulk_fetch.return_value = bulk_data
        mock_session.return_value.__enter__.return_value = test_db_session

        stats = collector.collect_fundamentals_for_all_stocks('20240115')

        assert stats['total_stocks'] == 1
        assert stats['successful'] == 1
        assert stats['failed'] == 0

    @patch.object(FundamentalCollector, 'fetch_all_fundamentals_bulk')
    @patch('services.data_collector.fundamental_collector.get_db_session')
    def test_collect_fundamentals_bulk_fetch_failure(
        self, mock_session, mock_bulk_fetch, collector, test_db_session, sample_stock
    ):
        """Test handling bulk fetch failure."""
        mock_bulk_fetch.return_value = None
        mock_session.return_value.__enter__.return_value = test_db_session

        stats = collector.collect_fundamentals_for_all_stocks('20240115')

        assert stats['total_stocks'] == 0
        assert stats['successful'] == 0
        assert stats['failed'] == 0

    @patch.object(FundamentalCollector, 'fetch_all_fundamentals_bulk')
    @patch('services.data_collector.fundamental_collector.get_db_session')
    def test_collect_fundamentals_missing_ticker_in_bulk(
        self, mock_session, mock_bulk_fetch, collector, test_db_session, sample_stock
    ):
        """Test handling when stock ticker is not in bulk data."""
        # Bulk data without our test ticker
        bulk_data = pd.DataFrame({
            'BPS': [50000],
            'PER': [10.0],
            'PBR': [1.5],
            'EPS': [5000]
        }, index=['000000'])  # Different ticker

        mock_bulk_fetch.return_value = bulk_data
        mock_session.return_value.__enter__.return_value = test_db_session

        stats = collector.collect_fundamentals_for_all_stocks('20240115')

        assert stats['total_stocks'] == 1
        assert stats['successful'] == 0
        assert stats['failed'] == 1

    @patch.object(FundamentalCollector, 'fetch_all_fundamentals_bulk')
    @patch('services.data_collector.fundamental_collector.get_db_session')
    def test_collect_fundamentals_updates_stock_metadata(
        self, mock_session, mock_bulk_fetch, collector, test_db_session, sample_stock
    ):
        """Test that stock metadata (market cap, shares) is updated."""
        bulk_data = pd.DataFrame({
            'BPS': [58000],
            'PER': [12.5],
            'PBR': [1.8],
            'EPS': [5600],
            'DIV': [2.5],
            'DPS': [1400],
            '시가총액': [600000000000000],  # Updated value
            '상장주식수': [6000000000]  # Updated value
        }, index=['005930'])

        mock_bulk_fetch.return_value = bulk_data
        mock_session.return_value.__enter__.return_value = test_db_session

        initial_cap = sample_stock.market_cap

        stats = collector.collect_fundamentals_for_all_stocks('20240115')

        assert stats['successful'] == 1

        # Verify stock metadata was updated
        test_db_session.refresh(sample_stock)
        assert sample_stock.market_cap == 600000000000000
        assert sample_stock.listed_shares == 6000000000

    @patch.object(FundamentalCollector, 'fetch_all_fundamentals_bulk')
    @patch('services.data_collector.fundamental_collector.get_db_session')
    def test_collect_fundamentals_batch_commit(
        self, mock_session, mock_bulk_fetch, collector, test_db_session
    ):
        """Test that commits happen in batches."""
        from shared.database.models import Stock

        # Create multiple stocks
        for i in range(10):
            stock = Stock(
                ticker=f'00{i}930',
                name_kr=f'테스트{i}',
                name_en=f'Test{i}',
                market='KOSPI',
                is_active=True
            )
            test_db_session.add(stock)
        test_db_session.commit()

        # Create bulk data for all stocks
        bulk_data = pd.DataFrame({
            'BPS': [58000] * 10,
            'PER': [12.5] * 10,
            'PBR': [1.8] * 10,
            'EPS': [5600] * 10,
            'DIV': [2.5] * 10,
            'DPS': [1400] * 10,
            '시가총액': [500000000000000] * 10,
            '상장주식수': [5000000000] * 10
        }, index=[f'00{i}930' for i in range(10)])

        mock_bulk_fetch.return_value = bulk_data
        mock_session.return_value.__enter__.return_value = test_db_session

        stats = collector.collect_fundamentals_for_all_stocks('20240115')

        assert stats['total_stocks'] == 10
        assert stats['successful'] == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
