"""
Unit tests for Stock Code Collector with mocked external APIs.

Tests stock code collection from FinanceDataReader and pykrx with proper mocking.
"""
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from services.data_collector.stock_code_collector import StockCodeCollector
from shared.database.models import Stock


class TestStockCodeCollector:
    """Test suite for StockCodeCollector."""

    @pytest.fixture
    def collector(self):
        """Create stock code collector instance."""
        return StockCodeCollector()

    @pytest.fixture
    def mock_stock_listing_data(self):
        """Mock FinanceDataReader StockListing data."""
        return pd.DataFrame({
            'Code': ['005930', '000660', '035420'],
            'Name': ['삼성전자', 'SK하이닉스', 'NAVER'],
            'Sector': ['전기전자', '전기전자', '서비스업'],
            'Industry': ['반도체', '반도체', '인터넷'],
            'ListingDate': pd.to_datetime(['1975-06-11', '1996-12-26', '2002-10-29'])
        })

    @pytest.fixture
    def mock_market_cap_data(self):
        """Mock pykrx market cap data."""
        return pd.DataFrame({
            '시가총액': [500000000000000, 80000000000000, 40000000000000],
            '상장주식수': [5969782550, 728002365, 147299337]
        }, index=['005930', '000660', '035420'])

    def test_initialization(self, collector):
        """Test collector initialization."""
        assert collector is not None
        assert collector.rate_limiter is not None

    @patch('services.data_collector.stock_code_collector.fdr.StockListing')
    def test_fetch_stock_codes_success(self, mock_stock_listing, collector, mock_stock_listing_data):
        """Test successful stock codes fetch from FinanceDataReader."""
        mock_stock_listing.return_value = mock_stock_listing_data

        result = collector.fetch_stock_codes('KOSPI')

        assert result is not None
        assert not result.empty
        assert len(result) == 3
        assert 'Code' in result.columns
        assert 'Name' in result.columns
        mock_stock_listing.assert_called_once_with('KOSPI')

    @patch('services.data_collector.stock_code_collector.fdr.StockListing')
    def test_fetch_stock_codes_failure(self, mock_stock_listing, collector):
        """Test handling when stock codes fetch fails."""
        mock_stock_listing.side_effect = Exception("API error")

        with pytest.raises(Exception):
            collector.fetch_stock_codes('KOSPI')

    @patch('services.data_collector.stock_code_collector.pykrx_stock.get_market_cap_by_ticker')
    def test_fetch_stock_details_success(self, mock_market_cap, collector, mock_market_cap_data):
        """Test successful stock details fetch."""
        mock_market_cap.return_value = mock_market_cap_data

        result = collector.fetch_stock_details('005930')

        assert result is not None
        assert 'market_cap' in result
        assert 'listed_shares' in result
        assert result['market_cap'] == 500000000000000
        assert result['listed_shares'] == 5969782550

    @patch('services.data_collector.stock_code_collector.pykrx_stock.get_market_cap_by_ticker')
    def test_fetch_stock_details_not_found(self, mock_market_cap, collector):
        """Test handling when stock details not found."""
        mock_market_cap.return_value = pd.DataFrame()

        result = collector.fetch_stock_details('INVALID')

        assert result is None

    @patch('services.data_collector.stock_code_collector.pykrx_stock.get_market_cap_by_ticker')
    def test_fetch_stock_details_failure(self, mock_market_cap, collector):
        """Test handling when stock details fetch fails."""
        mock_market_cap.side_effect = Exception("API error")

        result = collector.fetch_stock_details('005930')

        assert result is None

    @patch.object(StockCodeCollector, 'fetch_stock_details')
    @patch('services.data_collector.stock_code_collector.get_db_session')
    @patch('services.data_collector.stock_code_collector.fdr.StockListing')
    def test_collect_single_stock_new_stock(
        self,
        mock_stock_listing,
        mock_get_db_session,
        mock_fetch_details,
        collector,
        mock_stock_listing_data,
        test_db_session
    ):
        """Test collecting a single new stock that doesn't exist in database."""
        # Mock the database session
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock FinanceDataReader
        mock_stock_listing.return_value = mock_stock_listing_data

        # Mock stock details
        mock_fetch_details.return_value = {
            'market_cap': 500000000000000,
            'listed_shares': 5969782550
        }

        # Collect the stock
        result = collector.collect_single_stock('005930')

        assert result is True

        # Verify stock was saved to database
        stock = test_db_session.query(Stock).filter(Stock.ticker == '005930').first()
        assert stock is not None
        assert stock.name_kr == '삼성전자'
        assert stock.market == 'KOSPI'
        assert stock.market_cap == 500000000000000
        assert stock.listed_shares == 5969782550
        assert stock.is_active is True

    @patch.object(StockCodeCollector, 'fetch_stock_details')
    @patch('services.data_collector.stock_code_collector.get_db_session')
    @patch('services.data_collector.stock_code_collector.fdr.StockListing')
    def test_collect_single_stock_existing_stock(
        self,
        mock_stock_listing,
        mock_get_db_session,
        mock_fetch_details,
        collector,
        mock_stock_listing_data,
        test_db_session,
        sample_stock
    ):
        """Test collecting a single stock that already exists in database (update scenario)."""
        # Mock the database session
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock FinanceDataReader
        mock_stock_listing.return_value = mock_stock_listing_data

        # Mock stock details with updated values
        mock_fetch_details.return_value = {
            'market_cap': 550000000000000,  # Updated value
            'listed_shares': 5969782550
        }

        # Update the stock
        result = collector.collect_single_stock('005930')

        assert result is True

        # Verify stock was updated
        stock = test_db_session.query(Stock).filter(Stock.ticker == '005930').first()
        assert stock is not None
        assert stock.name_kr == '삼성전자'
        assert stock.market_cap == 550000000000000  # Should be updated

    @patch('services.data_collector.stock_code_collector.get_db_session')
    @patch('services.data_collector.stock_code_collector.fdr.StockListing')
    def test_collect_single_stock_not_found(
        self,
        mock_stock_listing,
        mock_get_db_session,
        collector,
        test_db_session
    ):
        """Test collecting a single stock that doesn't exist in any market."""
        # Mock the database session
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock empty DataFrames for all markets
        mock_stock_listing.return_value = pd.DataFrame()

        # Try to collect invalid stock
        result = collector.collect_single_stock('INVALID')

        assert result is False

    @patch('services.data_collector.stock_code_collector.get_db_session')
    @patch('services.data_collector.stock_code_collector.fdr.StockListing')
    def test_collect_single_stock_api_error(
        self,
        mock_stock_listing,
        mock_get_db_session,
        collector,
        test_db_session
    ):
        """Test handling when API error occurs during single stock collection."""
        # Mock the database session
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock API error
        mock_stock_listing.side_effect = Exception("API error")

        # Try to collect stock
        result = collector.collect_single_stock('005930')

        assert result is False

    @patch.object(StockCodeCollector, '_save_stocks_to_db')
    @patch.object(StockCodeCollector, 'fetch_stock_codes')
    def test_collect_all_stock_codes_success(
        self,
        mock_fetch_codes,
        mock_save_stocks,
        collector,
        mock_stock_listing_data
    ):
        """Test successful collection of all stock codes from all markets."""
        # Mock fetch for each market
        mock_fetch_codes.return_value = mock_stock_listing_data
        mock_save_stocks.return_value = 3

        result = collector.collect_all_stock_codes()

        # Should be called for KOSPI, KOSDAQ, KONEX
        assert mock_fetch_codes.call_count == 3
        assert mock_save_stocks.call_count == 3
        assert result == 9  # 3 stocks per market * 3 markets

    @patch.object(StockCodeCollector, 'fetch_stock_codes')
    def test_collect_all_stock_codes_empty_market(
        self,
        mock_fetch_codes,
        collector
    ):
        """Test handling when a market returns no data."""
        # First market returns data, second is empty, third returns data
        mock_fetch_codes.side_effect = [
            pd.DataFrame({'Code': ['005930'], 'Name': ['삼성전자']}),
            pd.DataFrame(),  # Empty
            pd.DataFrame({'Code': ['035420'], 'Name': ['NAVER']})
        ]

        result = collector.collect_all_stock_codes()

        # Should still process successfully
        assert result >= 0

    @patch.object(StockCodeCollector, 'fetch_stock_codes')
    def test_collect_all_stock_codes_partial_failure(
        self,
        mock_fetch_codes,
        collector
    ):
        """Test handling when one market fails but others succeed."""
        # First market succeeds, second fails, third succeeds
        mock_fetch_codes.side_effect = [
            pd.DataFrame({'Code': ['005930'], 'Name': ['삼성전자']}),
            Exception("API error"),
            pd.DataFrame({'Code': ['035420'], 'Name': ['NAVER']})
        ]

        result = collector.collect_all_stock_codes()

        # Should continue processing other markets
        assert result >= 0

    @patch.object(StockCodeCollector, 'fetch_stock_details')
    @patch('services.data_collector.stock_code_collector.get_db_session')
    def test_save_stocks_to_db_batch_commit(
        self,
        mock_get_db_session,
        mock_fetch_details,
        collector,
        test_db_session
    ):
        """Test that stocks are committed in batches."""
        # Mock the database session
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Create a large dataset (more than 50 stocks)
        large_df = pd.DataFrame({
            'Code': [f'{i:06d}' for i in range(100)],
            'Name': [f'Stock {i}' for i in range(100)],
            'Sector': ['Technology'] * 100,
            'Industry': ['IT'] * 100
        })

        # Mock stock details
        mock_fetch_details.return_value = {
            'market_cap': 1000000000000,
            'listed_shares': 1000000
        }

        result = collector._save_stocks_to_db(large_df, 'KOSPI')

        assert result == 100
        # Verify stocks were saved
        stocks = test_db_session.query(Stock).count()
        assert stocks == 100

    @patch.object(StockCodeCollector, 'fetch_stock_details')
    @patch('services.data_collector.stock_code_collector.get_db_session')
    def test_save_stocks_to_db_handles_errors(
        self,
        mock_get_db_session,
        mock_fetch_details,
        collector,
        test_db_session
    ):
        """Test that _save_stocks_to_db handles individual stock errors gracefully."""
        # Mock the database session
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Create dataset with valid and invalid data
        df = pd.DataFrame({
            'Code': ['005930', None, '035420'],  # Middle one has None code
            'Name': ['삼성전자', 'Invalid', 'NAVER'],
            'Sector': ['Technology', 'Unknown', 'Service'],
            'Industry': ['Semiconductor', 'Unknown', 'Internet']
        })

        mock_fetch_details.return_value = {
            'market_cap': 1000000000000,
            'listed_shares': 1000000
        }

        result = collector._save_stocks_to_db(df, 'KOSPI')

        # Should save 2 out of 3 (skips the one with None code)
        assert result == 2

    @patch.object(StockCodeCollector, 'fetch_stock_details')
    @patch('services.data_collector.stock_code_collector.get_db_session')
    def test_update_stock_details_single_stock(
        self,
        mock_get_db_session,
        mock_fetch_details,
        collector,
        test_db_session,
        sample_stock
    ):
        """Test updating details for a single stock."""
        # Mock the database session
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock updated stock details
        mock_fetch_details.return_value = {
            'market_cap': 550000000000000,
            'listed_shares': 6000000000
        }

        result = collector.update_stock_details('005930')

        assert result == 1

        # Verify stock was updated
        stock = test_db_session.query(Stock).filter(Stock.ticker == '005930').first()
        assert stock.market_cap == 550000000000000
        assert stock.listed_shares == 6000000000

    @patch.object(StockCodeCollector, 'fetch_stock_details')
    @patch('services.data_collector.stock_code_collector.get_db_session')
    def test_update_stock_details_all_stocks(
        self,
        mock_get_db_session,
        mock_fetch_details,
        collector,
        test_db_session
    ):
        """Test updating details for all stocks."""
        # Mock the database session
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Create multiple stocks
        stocks_data = [
            ('005930', '삼성전자', 'KOSPI'),
            ('000660', 'SK하이닉스', 'KOSPI'),
            ('035420', 'NAVER', 'KOSPI')
        ]

        for ticker, name, market in stocks_data:
            stock = Stock(
                ticker=ticker,
                name_kr=name,
                market=market,
                is_active=True
            )
            test_db_session.add(stock)
        test_db_session.commit()

        # Mock stock details
        mock_fetch_details.return_value = {
            'market_cap': 1000000000000,
            'listed_shares': 1000000
        }

        result = collector.update_stock_details()

        assert result == 3

    @patch.object(StockCodeCollector, 'fetch_stock_details')
    @patch('services.data_collector.stock_code_collector.get_db_session')
    def test_update_stock_details_handles_errors(
        self,
        mock_get_db_session,
        mock_fetch_details,
        collector,
        test_db_session,
        sample_stock
    ):
        """Test that update_stock_details handles errors gracefully."""
        # Mock the database session
        mock_get_db_session.return_value.__enter__.return_value = test_db_session

        # Mock fetch_stock_details to fail
        mock_fetch_details.side_effect = Exception("API error")

        result = collector.update_stock_details('005930')

        # Should return 0 when update fails
        assert result == 0

    @patch('services.data_collector.stock_code_collector.fdr.StockListing')
    def test_fetch_stock_codes_multiple_markets(self, mock_stock_listing, collector):
        """Test fetching stock codes from different markets."""
        kospi_data = pd.DataFrame({
            'Code': ['005930', '000660'],
            'Name': ['삼성전자', 'SK하이닉스']
        })

        kosdaq_data = pd.DataFrame({
            'Code': ['035420', '035720'],
            'Name': ['NAVER', '카카오']
        })

        # Mock different returns for different markets
        mock_stock_listing.side_effect = [kospi_data, kosdaq_data]

        kospi_result = collector.fetch_stock_codes('KOSPI')
        kosdaq_result = collector.fetch_stock_codes('KOSDAQ')

        assert len(kospi_result) == 2
        assert len(kosdaq_result) == 2
        assert kospi_result['Code'].iloc[0] == '005930'
        assert kosdaq_result['Code'].iloc[0] == '035420'
