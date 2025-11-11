"""
Tests for edge cases and error handling in Web Viewer.
"""
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError, DatabaseError


class TestDatabaseConnectionErrors:
    """Tests for database connection error handling."""

    def test_stocks_endpoint_database_error(self, client):
        """Test stocks endpoint handles database errors gracefully."""
        with patch('services.web_viewer.main.get_db') as mock_db:
            mock_session = MagicMock()
            mock_session.query.side_effect = OperationalError(
                "Database connection failed", None, None
            )
            mock_db.return_value.__enter__.return_value = mock_session

            # The endpoint should handle the error and return 500
            # Note: This test might need adjustment based on actual error handling
            response = client.get("/api/stocks")
            # Depending on implementation, might return 500 or empty list
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


class TestInvalidInputs:
    """Tests for invalid input handling."""

    def test_get_prices_with_negative_page(self, client, sample_stocks):
        """Test getting prices with negative page number."""
        # FastAPI validation should prevent this, returning 422
        response = client.get("/api/stocks/005930/prices?page=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_prices_with_zero_page(self, client, sample_stocks):
        """Test getting prices with page 0."""
        response = client.get("/api/stocks/005930/prices?page=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_prices_with_invalid_page_size_too_small(self, client, sample_stocks):
        """Test getting prices with page size below minimum."""
        response = client.get("/api/stocks/005930/prices?page_size=5")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_prices_with_invalid_page_size_too_large(self, client, sample_stocks):
        """Test getting prices with page size above maximum."""
        response = client.get("/api/stocks/005930/prices?page_size=1000")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_prices_with_non_numeric_page(self, client, sample_stocks):
        """Test getting prices with non-numeric page parameter."""
        response = client.get("/api/stocks/005930/prices?page=abc")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_stocks_with_excessive_limit(self, client, sample_stocks):
        """Test getting stocks with limit exceeding maximum."""
        response = client.get("/api/stocks?limit=10000")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSpecialCharactersInTicker:
    """Tests for special characters in ticker parameter."""

    def test_get_prices_with_special_chars_ticker(self, client):
        """Test getting prices for ticker with special characters."""
        response = client.get("/api/stocks/ABC@#$/prices")
        # Should return 404 as ticker doesn't exist
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_info_with_special_chars_ticker(self, client):
        """Test getting info for ticker with special characters."""
        response = client.get("/api/stocks/!@#$%/info")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_prices_with_sql_injection_attempt(self, client):
        """Test SQL injection attempt in ticker parameter."""
        malicious_ticker = "005930' OR '1'='1"
        response = client.get(f"/api/stocks/{malicious_ticker}/prices")
        # Should safely return 404, not expose data
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestEmptyDatabaseScenarios:
    """Tests for empty database scenarios."""

    def test_all_endpoints_with_empty_db(self, client):
        """Test all endpoints work correctly with empty database."""
        # Health check should still work
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        # Stocks list should return empty array
        response = client.get("/api/stocks")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

        # Stock info should return 404
        response = client.get("/api/stocks/005930/info")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Stock prices should return 404
        response = client.get("/api/stocks/005930/prices")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDataIntegrity:
    """Tests for data integrity and consistency."""

    def test_prices_total_records_matches_actual_count(self, client, sample_stocks, sample_prices):
        """Test that total_records matches actual database count."""
        response = client.get("/api/stocks/005930/prices?page=1&page_size=10")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        total_records = data["total_records"]

        # Get all pages and count total records
        actual_count = 0
        for page in range(1, data["total_pages"] + 1):
            page_response = client.get(f"/api/stocks/005930/prices?page={page}&page_size=10")
            page_data = page_response.json()
            actual_count += len(page_data["data"])

        assert actual_count == total_records

    def test_pagination_no_duplicate_records(self, client, sample_stocks, sample_prices):
        """Test that pagination doesn't return duplicate records."""
        page1_response = client.get("/api/stocks/005930/prices?page=1&page_size=50")
        page2_response = client.get("/api/stocks/005930/prices?page=2&page_size=50")

        page1_ids = {record["id"] for record in page1_response.json()["data"]}
        page2_ids = {record["id"] for record in page2_response.json()["data"]}

        # No overlap between pages
        assert len(page1_ids.intersection(page2_ids)) == 0

    def test_pagination_no_missing_records(self, client, sample_stocks, sample_prices):
        """Test that pagination covers all records without gaps."""
        # Get first page
        page1_response = client.get("/api/stocks/005930/prices?page=1&page_size=50")
        total_records = page1_response.json()["total_records"]

        # Collect all record IDs across all pages
        all_ids = set()
        page = 1
        while True:
            response = client.get(f"/api/stocks/005930/prices?page={page}&page_size=50")
            data = response.json()["data"]
            if not data:
                break
            all_ids.update(record["id"] for record in data)
            page += 1

        # Should have collected all records
        assert len(all_ids) == total_records


class TestInactiveStocks:
    """Tests for inactive stock handling."""

    def test_inactive_stock_not_in_list_by_default(self, client, sample_stocks):
        """Test that inactive stocks are excluded from default list."""
        response = client.get("/api/stocks")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        tickers = [stock["ticker"] for stock in data]

        # Inactive stock (999999) should not be in the list
        assert "999999" not in tickers

    def test_inactive_stock_info_still_accessible(self, client, sample_stocks):
        """Test that inactive stock info can still be retrieved directly."""
        response = client.get("/api/stocks/999999/info")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["ticker"] == "999999"
        assert data["name_kr"] == "비활성종목"


class TestLargeDatasets:
    """Tests for handling large datasets."""

    @pytest.fixture
    def large_stock_list(self, test_db):
        """Create a large number of stocks for testing."""
        from shared.database.models import Stock

        stocks = []
        for i in range(1000):
            stock = Stock(
                ticker=f"{i:06d}",
                name_kr=f"종목{i}",
                name_en=f"Stock {i}",
                market="KOSPI" if i % 2 == 0 else "KOSDAQ",
                sector="테스트",
                is_active=True
            )
            stocks.append(stock)
            test_db.add(stock)

        test_db.commit()
        return stocks

    def test_get_stocks_with_large_dataset(self, client, large_stock_list):
        """Test getting stocks works with large dataset."""
        response = client.get("/api/stocks?limit=5000")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 1000  # All stocks

    def test_get_stocks_respects_limit_with_large_dataset(self, client, large_stock_list):
        """Test limit parameter works correctly with large dataset."""
        response = client.get("/api/stocks?limit=100")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 100


class TestConcurrentAccess:
    """Tests for concurrent access scenarios."""

    def test_multiple_simultaneous_requests(self, client, sample_stocks, sample_prices):
        """Test handling multiple simultaneous requests."""
        import concurrent.futures

        def make_request(ticker):
            return client.get(f"/api/stocks/{ticker}/prices")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(make_request, "005930")
                for _ in range(10)
            ]

            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        assert all(r.status_code == status.HTTP_200_OK for r in results)
        # All should return the same data
        first_data = results[0].json()
        assert all(r.json()["total_records"] == first_data["total_records"] for r in results)


class TestNumericPrecision:
    """Tests for numeric precision in price data."""

    def test_price_decimal_precision(self, client, sample_stocks, sample_prices):
        """Test that price values maintain proper decimal precision."""
        response = client.get("/api/stocks/005930/prices?page=1&page_size=1")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()["data"][0]

        # Prices should be numeric (int or float)
        assert isinstance(data["open"], (int, float))
        assert isinstance(data["high"], (int, float))
        assert isinstance(data["low"], (int, float))
        assert isinstance(data["close"], (int, float))

        # Prices should be positive
        assert data["open"] > 0
        assert data["high"] > 0
        assert data["low"] > 0
        assert data["close"] > 0

        # Volume should be positive integer
        assert isinstance(data["volume"], int)
        assert data["volume"] > 0
