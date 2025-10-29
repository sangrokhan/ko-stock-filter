"""
Unit tests for Price Collector with mocked external APIs.

Tests data collection from FinanceDataReader and pykrx with proper mocking.
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from services.data_collector.price_collector import PriceCollector


class TestPriceCollector:
    """Test suite for PriceCollector."""

    @pytest.fixture
    def collector(self):
        """Create price collector instance."""
        return PriceCollector()

    def test_initialization(self, collector):
        """Test collector initialization."""
        assert collector is not None
        assert collector.rate_limiter is not None

    @patch('services.data_collector.price_collector.fdr.DataReader')
    def test_fetch_price_data_success_fdr(self, mock_fdr, collector, mock_fdr_data):
        """Test successful price data fetch from FinanceDataReader."""
        mock_fdr.return_value = mock_fdr_data

        result = collector.fetch_price_data('005930', '2024-01-01', '2024-01-31')

        assert result is not None
        assert not result.empty
        assert len(result) == 30
        assert 'Date' in result.columns or result.index.name == 'Date'
        assert 'Close' in result.columns
        assert 'Volume' in result.columns
        mock_fdr.assert_called_once_with('005930', '2024-01-01', '2024-01-31')

    @patch('services.data_collector.price_collector.pykrx_stock.get_market_ohlcv_by_date')
    @patch('services.data_collector.price_collector.fdr.DataReader')
    def test_fetch_price_data_fallback_to_pykrx(
        self, mock_fdr, mock_pykrx, collector, mock_fdr_data
    ):
        """Test fallback to pykrx when FinanceDataReader fails."""
        # FDR fails
        mock_fdr.side_effect = Exception("FDR error")

        # pykrx succeeds with Korean column names
        pykrx_data = pd.DataFrame({
            '날짜': pd.date_range(end=datetime.now(), periods=30, freq='D'),
            '시가': [70000 + i * 100 for i in range(30)],
            '고가': [71000 + i * 100 for i in range(30)],
            '저가': [69000 + i * 100 for i in range(30)],
            '종가': [70000 + i * 100 for i in range(30)],
            '거래량': [10000000 + i * 100000 for i in range(30)],
            '거래대금': [700000000000 + i * 1000000000 for i in range(30)]
        })
        pykrx_data.set_index('날짜', inplace=True)
        mock_pykrx.return_value = pykrx_data

        result = collector.fetch_price_data('005930', '2024-01-01', '2024-01-31')

        assert result is not None
        assert not result.empty
        assert 'Close' in result.columns  # Should be renamed from 종가
        assert 'Volume' in result.columns  # Should be renamed from 거래량
        mock_pykrx.assert_called_once()

    @patch('services.data_collector.price_collector.fdr.DataReader')
    def test_fetch_price_data_no_data(self, mock_fdr, collector):
        """Test handling when no price data is available."""
        mock_fdr.return_value = pd.DataFrame()  # Empty dataframe

        result = collector.fetch_price_data('INVALID', '2024-01-01', '2024-01-31')

        assert result is None

    @patch('services.data_collector.price_collector.pykrx_stock.get_market_ohlcv_by_date')
    @patch('services.data_collector.price_collector.fdr.DataReader')
    def test_fetch_price_data_both_sources_fail(self, mock_fdr, mock_pykrx, collector):
        """Test handling when both data sources fail."""
        mock_fdr.side_effect = Exception("FDR error")
        mock_pykrx.side_effect = Exception("pykrx error")

        result = collector.fetch_price_data('005930', '2024-01-01', '2024-01-31')

        assert result is None

    @patch('services.data_collector.price_collector.fdr.DataReader')
    def test_fetch_price_data_default_end_date(self, mock_fdr, collector, mock_fdr_data):
        """Test that end_date defaults to today."""
        mock_fdr.return_value = mock_fdr_data

        result = collector.fetch_price_data('005930', '2024-01-01')

        assert result is not None
        # Check that end date was set to today
        mock_fdr.assert_called_once()
        call_args = mock_fdr.call_args[0]
        assert call_args[2] == datetime.now().strftime('%Y-%m-%d')

    @patch.object(PriceCollector, 'fetch_price_data')
    @patch.object(PriceCollector, '_save_prices_to_db')
    def test_collect_prices_for_stock_success(
        self, mock_save, mock_fetch, collector, mock_fdr_data
    ):
        """Test successful price collection for a single stock."""
        mock_fetch.return_value = mock_fdr_data
        mock_save.return_value = 30

        count = collector.collect_prices_for_stock('005930', '2024-01-01', '2024-01-31')

        assert count == 30
        mock_fetch.assert_called_once_with('005930', '2024-01-01', '2024-01-31')
        mock_save.assert_called_once()

    @patch.object(PriceCollector, 'fetch_price_data')
    def test_collect_prices_for_stock_no_data(self, mock_fetch, collector):
        """Test price collection when no data is available."""
        mock_fetch.return_value = None

        count = collector.collect_prices_for_stock('INVALID')

        assert count == 0

    @patch.object(PriceCollector, 'fetch_price_data')
    @patch.object(PriceCollector, '_save_prices_to_db')
    def test_collect_prices_for_stock_default_dates(
        self, mock_save, mock_fetch, collector, mock_fdr_data
    ):
        """Test that default dates are used when not specified."""
        mock_fetch.return_value = mock_fdr_data
        mock_save.return_value = 30

        count = collector.collect_prices_for_stock('005930')

        assert count == 30
        # Verify default dates were used
        call_args = mock_fetch.call_args[0]
        assert len(call_args) == 3  # ticker, start_date, end_date

    def test_save_prices_to_db(self, collector, test_db_session, sample_stock, mock_fdr_data):
        """Test saving price data to database."""
        # Need to patch get_db_session to use test session
        with patch('services.data_collector.price_collector.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session

            count = collector._save_prices_to_db('005930', mock_fdr_data)

            assert count > 0
            # Verify data was saved
            from shared.database.models import StockPrice
            saved_prices = test_db_session.query(StockPrice).filter(
                StockPrice.stock_id == sample_stock.id
            ).all()
            assert len(saved_prices) > 0

    def test_save_prices_to_db_invalid_ticker(self, collector, test_db_session, mock_fdr_data):
        """Test saving prices for non-existent ticker."""
        with patch('services.data_collector.price_collector.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session

            count = collector._save_prices_to_db('INVALID', mock_fdr_data)

            assert count == 0

    def test_save_prices_to_db_updates_existing(
        self, collector, test_db_session, sample_stock, sample_stock_prices, mock_fdr_data
    ):
        """Test that existing price records are updated."""
        with patch('services.data_collector.price_collector.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session

            # Save with overlapping dates
            initial_count = len(sample_stock_prices)
            count = collector._save_prices_to_db('005930', mock_fdr_data)

            # Should update existing records
            assert count > 0

    def test_save_prices_to_db_skips_zero_prices(
        self, collector, test_db_session, sample_stock
    ):
        """Test that zero prices are skipped."""
        # Create dataframe with zero prices
        zero_price_data = pd.DataFrame({
            'Date': pd.date_range(end=datetime.now(), periods=3, freq='D'),
            'Open': [0, 0, 0],
            'High': [0, 0, 0],
            'Low': [0, 0, 0],
            'Close': [0, 0, 0],
            'Volume': [10000, 10000, 10000]
        })
        zero_price_data.set_index('Date', inplace=True)

        with patch('services.data_collector.price_collector.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session

            count = collector._save_prices_to_db('005930', zero_price_data)

            # Should skip all zero-price records
            assert count == 0

    def test_get_last_price_date(self, collector, test_db_session, sample_stock, sample_stock_prices):
        """Test getting last price date for a stock."""
        with patch('services.data_collector.price_collector.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session

            last_date = collector.get_last_price_date('005930')

            assert last_date is not None
            assert isinstance(last_date, datetime)

    def test_get_last_price_date_no_data(self, collector, test_db_session, sample_stock):
        """Test getting last price date when no price data exists."""
        with patch('services.data_collector.price_collector.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session

            last_date = collector.get_last_price_date('005930')

            assert last_date is None

    def test_get_last_price_date_invalid_ticker(self, collector, test_db_session):
        """Test getting last price date for invalid ticker."""
        with patch('services.data_collector.price_collector.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db_session

            last_date = collector.get_last_price_date('INVALID')

            assert last_date is None


class TestPriceCollectorIntegration:
    """Integration tests for price collector."""

    @pytest.fixture
    def collector(self):
        """Create price collector instance."""
        return PriceCollector()

    @patch.object(PriceCollector, 'collect_prices_for_stock')
    @patch('services.data_collector.price_collector.get_db_session')
    def test_collect_prices_for_all_stocks(
        self, mock_session, mock_collect_single, collector, test_db_session, sample_stock
    ):
        """Test collecting prices for all stocks."""
        mock_session.return_value.__enter__.return_value = test_db_session
        mock_collect_single.return_value = 30

        stats = collector.collect_prices_for_all_stocks('2024-01-01', '2024-01-31')

        assert stats['total_stocks'] == 1
        assert stats['successful'] == 1
        assert stats['failed'] == 0
        assert stats['total_records'] == 30

    @patch.object(PriceCollector, 'collect_prices_for_stock')
    @patch('services.data_collector.price_collector.get_db_session')
    def test_collect_prices_for_all_stocks_with_failures(
        self, mock_session, mock_collect_single, collector, test_db_session, sample_stock
    ):
        """Test collecting prices with some failures."""
        mock_session.return_value.__enter__.return_value = test_db_session
        mock_collect_single.return_value = 0  # Simulate failure

        stats = collector.collect_prices_for_all_stocks()

        assert stats['total_stocks'] == 1
        assert stats['failed'] == 1
        assert stats['successful'] == 0

    @patch.object(PriceCollector, 'collect_prices_for_stock')
    @patch('services.data_collector.price_collector.get_db_session')
    def test_collect_prices_batch_logging(
        self, mock_session, mock_collect_single, collector, test_db_session
    ):
        """Test that batch progress is logged."""
        # Create multiple stocks
        from shared.database.models import Stock
        for i in range(5):
            stock = Stock(
                ticker=f'00{i}930',
                name_kr=f'테스트{i}',
                name_en=f'Test{i}',
                market='KOSPI',
                is_active=True
            )
            test_db_session.add(stock)
        test_db_session.commit()

        mock_session.return_value.__enter__.return_value = test_db_session
        mock_collect_single.return_value = 10

        stats = collector.collect_prices_for_all_stocks(batch_size=2)

        assert stats['total_stocks'] == 5
        assert stats['successful'] == 5
        assert mock_collect_single.call_count == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
