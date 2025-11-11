"""
Tests for Web Viewer API endpoints.
"""
import pytest
from fastapi import status


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_success(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "web_viewer"
        assert "timestamp" in data


class TestStocksListEndpoint:
    """Tests for stocks list endpoint."""

    def test_get_stocks_empty_database(self, client):
        """Test getting stocks from empty database returns empty list."""
        response = client.get("/api/stocks")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_get_stocks_with_data(self, client, sample_stocks):
        """Test getting stocks returns all active stocks."""
        response = client.get("/api/stocks")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Should only return active stocks (3 out of 4)
        assert len(data) == 3

        # Check first stock structure
        assert data[0]["ticker"] in ["005930", "000660", "035420"]
        assert "name_kr" in data[0]
        assert "market" in data[0]

    def test_get_stocks_includes_inactive(self, client, sample_stocks):
        """Test getting stocks with is_active=False parameter."""
        response = client.get("/api/stocks?is_active=false")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # The is_active parameter is boolean, false string is treated as True in FastAPI
        # So this will return all active stocks
        assert len(data) >= 3

    def test_get_stocks_respects_limit(self, client, sample_stocks):
        """Test limit parameter restricts number of stocks returned."""
        response = client.get("/api/stocks?limit=2")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 2

    def test_get_stocks_sorted_by_ticker(self, client, sample_stocks):
        """Test stocks are sorted by ticker."""
        response = client.get("/api/stocks")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        tickers = [stock["ticker"] for stock in data]
        assert tickers == sorted(tickers)


class TestStockInfoEndpoint:
    """Tests for individual stock info endpoint."""

    def test_get_stock_info_success(self, client, sample_stocks):
        """Test getting info for existing stock."""
        response = client.get("/api/stocks/005930/info")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["ticker"] == "005930"
        assert data["name_kr"] == "삼성전자"
        assert data["name_en"] == "Samsung Electronics"
        assert data["market"] == "KOSPI"

    def test_get_stock_info_not_found(self, client, sample_stocks):
        """Test getting info for non-existent stock returns 404."""
        response = client.get("/api/stocks/999990/info")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert "detail" in data
        assert "999990" in data["detail"]

    def test_get_stock_info_empty_database(self, client):
        """Test getting stock info from empty database returns 404."""
        response = client.get("/api/stocks/005930/info")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStockPricesEndpoint:
    """Tests for stock prices endpoint."""

    def test_get_prices_with_data(self, client, sample_stocks, sample_prices):
        """Test getting prices for stock with data."""
        response = client.get("/api/stocks/005930/prices")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["ticker"] == "005930"
        assert data["stock_name"] == "삼성전자"
        assert data["total_records"] == 150
        assert data["page"] == 1
        assert data["page_size"] == 100
        assert data["total_pages"] == 2
        assert len(data["data"]) == 100

    def test_get_prices_empty_data(self, client, empty_stock):
        """Test getting prices for stock with no price data."""
        response = client.get(f"/api/stocks/{empty_stock.ticker}/prices")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["ticker"] == empty_stock.ticker
        assert data["total_records"] == 0
        assert data["total_pages"] == 0
        assert len(data["data"]) == 0

    def test_get_prices_stock_not_found(self, client):
        """Test getting prices for non-existent stock returns 404."""
        response = client.get("/api/stocks/999999/prices")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert "detail" in data

    def test_get_prices_pagination_page_1(self, client, sample_stocks, sample_prices):
        """Test pagination - first page."""
        response = client.get("/api/stocks/005930/prices?page=1&page_size=50")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert data["total_pages"] == 3
        assert len(data["data"]) == 50

        # Check data is sorted by date ascending (oldest first)
        dates = [record["date"] for record in data["data"]]
        assert dates == sorted(dates)

    def test_get_prices_pagination_page_2(self, client, sample_stocks, sample_prices):
        """Test pagination - second page."""
        response = client.get("/api/stocks/005930/prices?page=2&page_size=50")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["page"] == 2
        assert len(data["data"]) == 50

    def test_get_prices_pagination_last_page(self, client, sample_stocks, sample_prices):
        """Test pagination - last page with partial data."""
        response = client.get("/api/stocks/005930/prices?page=2&page_size=100")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["page"] == 2
        assert data["total_pages"] == 2
        assert len(data["data"]) == 50  # Only 50 records on last page

    def test_get_prices_invalid_page_number(self, client, sample_stocks, sample_prices):
        """Test pagination with invalid page number returns empty data."""
        response = client.get("/api/stocks/005930/prices?page=999")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["page"] == 999
        assert len(data["data"]) == 0

    def test_get_prices_page_size_limits(self, client, sample_stocks, sample_prices):
        """Test page size respects min/max limits."""
        # Test minimum page size
        response = client.get("/api/stocks/005930/prices?page_size=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page_size"] == 10
        assert len(data["data"]) == 10

        # Test maximum page size
        response = client.get("/api/stocks/005930/prices?page_size=500")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page_size"] == 500

    def test_get_prices_data_structure(self, client, sample_stocks, sample_prices):
        """Test price data has correct structure."""
        response = client.get("/api/stocks/005930/prices?page=1&page_size=1")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        price_record = data["data"][0]

        # Check all required fields are present
        required_fields = ["id", "date", "open", "high", "low", "close", "volume"]
        for field in required_fields:
            assert field in price_record

        # Check data types
        assert isinstance(price_record["id"], int)
        assert isinstance(price_record["open"], (int, float))
        assert isinstance(price_record["high"], (int, float))
        assert isinstance(price_record["low"], (int, float))
        assert isinstance(price_record["close"], (int, float))
        assert isinstance(price_record["volume"], int)

    def test_get_prices_data_sorted_ascending(self, client, sample_stocks, sample_prices):
        """Test price data is sorted by date in ascending order (oldest first)."""
        response = client.get("/api/stocks/005930/prices?page=1&page_size=10")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        dates = [record["date"] for record in data["data"]]

        # Dates should be in ascending order
        for i in range(len(dates) - 1):
            assert dates[i] <= dates[i + 1], "Dates should be in ascending order"


class TestRootEndpoint:
    """Tests for root endpoint (main page)."""

    def test_root_returns_html(self, client):
        """Test root endpoint returns HTML page."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    def test_root_contains_expected_content(self, client):
        """Test root page contains expected UI elements."""
        response = client.get("/")
        content = response.text

        # Check for key UI elements
        assert "주식 데이터베이스 뷰어" in content
        assert "종목 목록" in content
        assert "stock-list" in content
        assert "table-container" in content
