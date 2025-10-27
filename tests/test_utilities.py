"""
Tests for shared utilities.
"""
import pytest
from datetime import datetime
from shared.utilities.validators import (
    validate_korean_ticker,
    validate_date_format,
    validate_price,
    validate_quantity,
)
from shared.utilities.date_utils import get_kst_now, is_market_open


class TestValidators:
    """Test validation functions."""

    def test_validate_korean_ticker_valid(self):
        """Test valid Korean ticker validation."""
        assert validate_korean_ticker("005930") is True
        assert validate_korean_ticker("000660") is True

    def test_validate_korean_ticker_invalid(self):
        """Test invalid Korean ticker validation."""
        assert validate_korean_ticker("5930") is False
        assert validate_korean_ticker("AAPL") is False
        assert validate_korean_ticker("00593A") is False

    def test_validate_date_format_valid(self):
        """Test valid date format validation."""
        assert validate_date_format("2024-01-01") is True
        assert validate_date_format("2024-12-31") is True

    def test_validate_date_format_invalid(self):
        """Test invalid date format validation."""
        assert validate_date_format("01-01-2024") is False
        assert validate_date_format("2024/01/01") is False
        assert validate_date_format("invalid") is False

    def test_validate_price_valid(self):
        """Test valid price validation."""
        assert validate_price(100.0) is True
        assert validate_price(0.01) is True

    def test_validate_price_invalid(self):
        """Test invalid price validation."""
        assert validate_price(0.0) is False
        assert validate_price(-100.0) is False

    def test_validate_quantity_valid(self):
        """Test valid quantity validation."""
        assert validate_quantity(1) is True
        assert validate_quantity(1000) is True

    def test_validate_quantity_invalid(self):
        """Test invalid quantity validation."""
        assert validate_quantity(0) is False
        assert validate_quantity(-10) is False


class TestDateUtils:
    """Test date utility functions."""

    def test_get_kst_now(self):
        """Test getting current KST time."""
        kst_time = get_kst_now()
        assert kst_time.tzinfo is not None
        assert isinstance(kst_time, datetime)

    def test_is_market_open_weekend(self):
        """Test market open check for weekend."""
        # Saturday
        saturday = datetime(2024, 1, 6, 10, 0, 0)
        assert is_market_open(saturday) is False

        # Sunday
        sunday = datetime(2024, 1, 7, 10, 0, 0)
        assert is_market_open(sunday) is False

    def test_is_market_open_during_hours(self):
        """Test market open check during market hours."""
        # Weekday during market hours (10:00 AM)
        weekday_open = datetime(2024, 1, 8, 10, 0, 0)
        assert is_market_open(weekday_open) is True

    def test_is_market_open_outside_hours(self):
        """Test market open check outside market hours."""
        # Weekday before market open (8:00 AM)
        weekday_before = datetime(2024, 1, 8, 8, 0, 0)
        assert is_market_open(weekday_before) is False

        # Weekday after market close (4:00 PM)
        weekday_after = datetime(2024, 1, 8, 16, 0, 0)
        assert is_market_open(weekday_after) is False
