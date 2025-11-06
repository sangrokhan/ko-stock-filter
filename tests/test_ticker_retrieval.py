"""
Unit tests for stock ticker retrieval functionality.

Tests the ability to retrieve multiple stock tickers from the database
in bulk operations across different repository classes.
"""
import pytest
from datetime import datetime
from typing import List

from shared.database.models import Stock
from services.indicator_calculator.technical_repository import TechnicalDataRepository


@pytest.fixture
def multiple_stocks(test_db_session) -> List[Stock]:
    """Create multiple sample stocks in the database."""
    stocks_data = [
        {
            'ticker': '005930',
            'name_kr': '삼성전자',
            'name_en': 'Samsung Electronics',
            'market': 'KOSPI',
            'sector': 'Technology',
            'industry': 'Semiconductors',
            'is_active': True
        },
        {
            'ticker': '000660',
            'name_kr': 'SK하이닉스',
            'name_en': 'SK Hynix',
            'market': 'KOSPI',
            'sector': 'Technology',
            'industry': 'Semiconductors',
            'is_active': True
        },
        {
            'ticker': '035420',
            'name_kr': 'NAVER',
            'name_en': 'NAVER',
            'market': 'KOSPI',
            'sector': 'Technology',
            'industry': 'Internet',
            'is_active': True
        },
        {
            'ticker': '035720',
            'name_kr': '카카오',
            'name_en': 'Kakao',
            'market': 'KOSPI',
            'sector': 'Technology',
            'industry': 'Internet',
            'is_active': True
        },
        {
            'ticker': '051910',
            'name_kr': 'LG화학',
            'name_en': 'LG Chem',
            'market': 'KOSPI',
            'sector': 'Materials',
            'industry': 'Chemicals',
            'is_active': True
        },
        {
            'ticker': '006400',
            'name_kr': '삼성SDI',
            'name_en': 'Samsung SDI',
            'market': 'KOSPI',
            'sector': 'Technology',
            'industry': 'Battery',
            'is_active': False  # Inactive stock
        },
    ]

    stocks = []
    for stock_data in stocks_data:
        stock = Stock(**stock_data)
        test_db_session.add(stock)
        stocks.append(stock)

    test_db_session.commit()
    return stocks


class TestTickerRetrieval:
    """Test suite for stock ticker retrieval from database."""

    def test_get_all_active_stocks(self, test_db_session, multiple_stocks):
        """Test retrieving all active stocks from database."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)

        # Act
        active_stocks = repo.get_active_stocks()

        # Assert
        assert len(active_stocks) == 5  # Should exclude inactive stock
        assert all(stock.is_active for stock in active_stocks)

        # Verify tickers are present
        tickers = [stock.ticker for stock in active_stocks]
        assert '005930' in tickers
        assert '000660' in tickers
        assert '035420' in tickers
        assert '035720' in tickers
        assert '051910' in tickers
        assert '006400' not in tickers  # Inactive stock should not be included

    def test_get_stocks_by_tickers_list(self, test_db_session, multiple_stocks):
        """Test retrieving specific stocks by ticker list."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)
        target_tickers = ['005930', '035420', '051910']

        # Act
        stocks = repo.get_stocks_by_tickers(target_tickers)

        # Assert
        assert len(stocks) == 3
        retrieved_tickers = [stock.ticker for stock in stocks]
        assert '005930' in retrieved_tickers
        assert '035420' in retrieved_tickers
        assert '051910' in retrieved_tickers

    def test_get_stocks_by_tickers_empty_list(self, test_db_session, multiple_stocks):
        """Test retrieving stocks with empty ticker list."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)

        # Act
        stocks = repo.get_stocks_by_tickers([])

        # Assert
        assert len(stocks) == 0

    def test_get_stocks_by_tickers_nonexistent(self, test_db_session, multiple_stocks):
        """Test retrieving stocks with non-existent tickers."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)

        # Act
        stocks = repo.get_stocks_by_tickers(['999999', '888888'])

        # Assert
        assert len(stocks) == 0

    def test_get_stocks_by_tickers_mixed(self, test_db_session, multiple_stocks):
        """Test retrieving stocks with mix of existing and non-existing tickers."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)
        mixed_tickers = ['005930', '999999', '035420', '888888']

        # Act
        stocks = repo.get_stocks_by_tickers(mixed_tickers)

        # Assert
        assert len(stocks) == 2  # Only existing tickers
        retrieved_tickers = [stock.ticker for stock in stocks]
        assert '005930' in retrieved_tickers
        assert '035420' in retrieved_tickers
        assert '999999' not in retrieved_tickers
        assert '888888' not in retrieved_tickers

    def test_get_stocks_by_tickers_excludes_inactive(self, test_db_session, multiple_stocks):
        """Test that get_stocks_by_tickers excludes inactive stocks."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)
        tickers = ['005930', '006400']  # 006400 is inactive

        # Act
        stocks = repo.get_stocks_by_tickers(tickers)

        # Assert
        assert len(stocks) == 1  # Only active stock
        assert stocks[0].ticker == '005930'

    def test_get_stock_by_ticker_single(self, test_db_session, multiple_stocks):
        """Test retrieving a single stock by ticker."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)

        # Act
        stock = repo.get_stock_by_ticker('005930')

        # Assert
        assert stock is not None
        assert stock.ticker == '005930'
        assert stock.name_kr == '삼성전자'
        assert stock.market == 'KOSPI'

    def test_get_stock_by_ticker_nonexistent(self, test_db_session, multiple_stocks):
        """Test retrieving non-existent stock by ticker."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)

        # Act
        stock = repo.get_stock_by_ticker('999999')

        # Assert
        assert stock is None

    def test_bulk_ticker_retrieval_performance(self, test_db_session):
        """Test performance of bulk ticker retrieval with many stocks."""
        # Arrange - Create 100 stocks
        for i in range(100):
            stock = Stock(
                ticker=f'{i:06d}',
                name_kr=f'테스트종목{i}',
                name_en=f'Test Stock {i}',
                market='KOSPI',
                sector='Technology',
                industry='Software',
                is_active=True
            )
            test_db_session.add(stock)
        test_db_session.commit()

        repo = TechnicalDataRepository(test_db_session)

        # Act - Retrieve all active stocks
        import time
        start_time = time.time()
        stocks = repo.get_active_stocks()
        end_time = time.time()

        # Assert
        assert len(stocks) == 100
        elapsed_time = end_time - start_time
        assert elapsed_time < 1.0  # Should complete in less than 1 second

    def test_ticker_retrieval_maintains_data_integrity(self, test_db_session, multiple_stocks):
        """Test that retrieved stocks maintain all their data integrity."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)

        # Act
        stocks = repo.get_active_stocks()

        # Assert
        for stock in stocks:
            assert stock.ticker is not None
            assert stock.name_kr is not None
            assert stock.market is not None
            assert stock.is_active is True
            assert isinstance(stock.ticker, str)
            assert len(stock.ticker) > 0

    def test_get_active_stocks_empty_database(self, test_db_session):
        """Test retrieving active stocks from empty database."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)

        # Act
        stocks = repo.get_active_stocks()

        # Assert
        assert len(stocks) == 0
        assert isinstance(stocks, list)

    def test_get_active_stocks_with_only_inactive(self, test_db_session):
        """Test retrieving active stocks when only inactive stocks exist."""
        # Arrange
        inactive_stock = Stock(
            ticker='999999',
            name_kr='비활성종목',
            name_en='Inactive Stock',
            market='KOSPI',
            is_active=False
        )
        test_db_session.add(inactive_stock)
        test_db_session.commit()

        repo = TechnicalDataRepository(test_db_session)

        # Act
        stocks = repo.get_active_stocks()

        # Assert
        assert len(stocks) == 0

    def test_get_stocks_by_market(self, test_db_session, multiple_stocks):
        """Test filtering stocks by market type."""
        # Arrange - Add some KOSDAQ stocks
        kosdaq_stocks = [
            Stock(ticker='123450', name_kr='코스닥1', name_en='KOSDAQ 1',
                  market='KOSDAQ', is_active=True),
            Stock(ticker='123460', name_kr='코스닥2', name_en='KOSDAQ 2',
                  market='KOSDAQ', is_active=True),
        ]
        for stock in kosdaq_stocks:
            test_db_session.add(stock)
        test_db_session.commit()

        # Act - Query by market
        kospi_stocks = test_db_session.query(Stock).filter(
            Stock.market == 'KOSPI',
            Stock.is_active == True
        ).all()

        kosdaq_stocks = test_db_session.query(Stock).filter(
            Stock.market == 'KOSDAQ',
            Stock.is_active == True
        ).all()

        # Assert
        assert len(kospi_stocks) == 5
        assert len(kosdaq_stocks) == 2
        assert all(stock.market == 'KOSPI' for stock in kospi_stocks)
        assert all(stock.market == 'KOSDAQ' for stock in kosdaq_stocks)

    def test_ticker_list_extraction(self, test_db_session, multiple_stocks):
        """Test extracting just the ticker codes from stocks."""
        # Arrange
        repo = TechnicalDataRepository(test_db_session)

        # Act
        stocks = repo.get_active_stocks()
        tickers = [stock.ticker for stock in stocks]

        # Assert
        assert len(tickers) == 5
        assert isinstance(tickers, list)
        assert all(isinstance(ticker, str) for ticker in tickers)
        assert '005930' in tickers
        assert '000660' in tickers

    def test_ticker_retrieval_with_sector_filter(self, test_db_session, multiple_stocks):
        """Test retrieving tickers filtered by sector."""
        # Arrange
        # Act - Query by sector
        tech_stocks = test_db_session.query(Stock).filter(
            Stock.sector == 'Technology',
            Stock.is_active == True
        ).all()

        # Assert
        assert len(tech_stocks) == 4  # Samsung, SK Hynix, Naver, Kakao
        tech_tickers = [stock.ticker for stock in tech_stocks]
        assert '005930' in tech_tickers
        assert '000660' in tech_tickers
        assert '035420' in tech_tickers
        assert '035720' in tech_tickers

    def test_direct_database_query_all_tickers(self, test_db_session, multiple_stocks):
        """Test direct database query to get all ticker codes."""
        # Act - Direct query for just ticker column
        tickers = test_db_session.query(Stock.ticker).filter(
            Stock.is_active == True
        ).all()

        # Assert
        assert len(tickers) == 5
        # tickers is a list of tuples, extract first element
        ticker_codes = [t[0] for t in tickers]
        assert '005930' in ticker_codes
        assert '000660' in ticker_codes


class TestStockCodeCollectorRetrieval:
    """Test stock code collector's ability to save and retrieve stocks."""

    def test_stock_retrieval_after_save(self, test_db_session):
        """Test that stocks can be retrieved after being saved."""
        # Arrange - Manually create stocks as if collected
        from shared.database.models import Stock

        stocks_to_save = [
            Stock(ticker='001', name_kr='종목1', name_en='Stock 1',
                  market='KOSPI', is_active=True),
            Stock(ticker='002', name_kr='종목2', name_en='Stock 2',
                  market='KOSPI', is_active=True),
            Stock(ticker='003', name_kr='종목3', name_en='Stock 3',
                  market='KOSDAQ', is_active=True),
        ]

        for stock in stocks_to_save:
            test_db_session.add(stock)
        test_db_session.commit()

        # Act - Retrieve all stocks
        retrieved = test_db_session.query(Stock).filter(
            Stock.is_active == True
        ).all()

        # Assert
        assert len(retrieved) == 3
        retrieved_tickers = [s.ticker for s in retrieved]
        assert '001' in retrieved_tickers
        assert '002' in retrieved_tickers
        assert '003' in retrieved_tickers

    def test_bulk_ticker_extraction_for_price_collection(self, test_db_session):
        """Test extracting tickers for bulk price collection operation."""
        # Arrange - Create stocks
        for i in range(10):
            stock = Stock(
                ticker=f'{i:06d}',
                name_kr=f'종목{i}',
                name_en=f'Stock {i}',
                market='KOSPI',
                is_active=True
            )
            test_db_session.add(stock)
        test_db_session.commit()

        # Act - Simulate what PriceCollector does
        stocks = test_db_session.query(Stock).filter(
            Stock.is_active == True
        ).all()
        tickers = [stock.ticker for stock in stocks]

        # Assert
        assert len(tickers) == 10
        assert all(len(ticker) == 6 for ticker in tickers)

    def test_ticker_deduplication(self, test_db_session):
        """Test that duplicate tickers are handled correctly."""
        # Arrange
        stock1 = Stock(ticker='005930', name_kr='삼성전자', name_en='Samsung',
                      market='KOSPI', is_active=True)
        test_db_session.add(stock1)
        test_db_session.commit()

        # Act - Try to add duplicate (should fail or update)
        stock2 = Stock(ticker='005930', name_kr='삼성전자2', name_en='Samsung2',
                      market='KOSPI', is_active=True)
        test_db_session.add(stock2)

        # Assert - Should raise integrity error
        with pytest.raises(Exception):  # IntegrityError or similar
            test_db_session.commit()


class TestRepositoryTickerMethods:
    """Test ticker retrieval methods across different repository classes."""

    def test_technical_repository_ticker_retrieval(self, test_db_session, multiple_stocks):
        """Test TechnicalDataRepository ticker retrieval methods."""
        from services.indicator_calculator.technical_repository import TechnicalDataRepository

        repo = TechnicalDataRepository(test_db_session)

        # Test get_active_stocks
        stocks = repo.get_active_stocks()
        assert len(stocks) == 5
        assert all(hasattr(stock, 'ticker') for stock in stocks)

        # Test get_stock_by_ticker
        stock = repo.get_stock_by_ticker('005930')
        assert stock is not None
        assert stock.ticker == '005930'

    def test_score_repository_ticker_retrieval(self, test_db_session, multiple_stocks):
        """Test ScoreDataRepository ticker retrieval methods."""
        from services.stock_scorer.score_repository import ScoreDataRepository

        repo = ScoreDataRepository(test_db_session)

        # Test get_active_stocks with limit
        stocks = repo.get_active_stocks(limit=3)
        assert len(stocks) <= 3
        assert all(stock.is_active for stock in stocks)

    def test_stability_repository_ticker_retrieval(self, test_db_session, multiple_stocks):
        """Test StabilityDataRepository ticker retrieval methods."""
        from services.stability_calculator.stability_repository import StabilityDataRepository

        repo = StabilityDataRepository(test_db_session)

        # Test get_active_stocks
        stocks = repo.get_active_stocks()
        assert len(stocks) == 5
        assert all(stock.ticker for stock in stocks)

    def test_financial_repository_ticker_retrieval(self, test_db_session, multiple_stocks):
        """Test FinancialDataRepository ticker retrieval methods."""
        from services.indicator_calculator.financial_repository import FinancialDataRepository

        repo = FinancialDataRepository(test_db_session)

        # Test get_active_stocks
        stocks = repo.get_active_stocks()
        assert len(stocks) == 5
        tickers = [stock.ticker for stock in stocks]
        assert '005930' in tickers


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
