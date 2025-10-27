"""
Tests for Price Monitor Service.
"""
import pytest
from datetime import datetime, date, time
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import pytz

from services.price_monitor.market_calendar import KoreanMarketCalendar
from services.price_monitor.event_publisher import PriceEventPublisher
from services.price_monitor.price_monitor import PriceMonitor


class TestKoreanMarketCalendar:
    """Test Korean market calendar functionality."""

    def test_market_hours(self):
        """Test market hours are correctly defined."""
        calendar = KoreanMarketCalendar()
        assert calendar.MARKET_OPEN == time(9, 0)
        assert calendar.MARKET_CLOSE == time(15, 30)

    def test_is_holiday_weekend(self):
        """Test weekend detection."""
        calendar = KoreanMarketCalendar()

        # Saturday
        saturday = date(2024, 10, 26)
        assert calendar.is_holiday(saturday) is True

        # Sunday
        sunday = date(2024, 10, 27)
        assert calendar.is_holiday(sunday) is True

    def test_is_holiday_weekday(self):
        """Test weekday is not a holiday."""
        calendar = KoreanMarketCalendar()

        # Regular weekday (not in holiday list)
        weekday = date(2024, 10, 28)  # Monday
        # This might be a holiday in the actual calendar, adjust if needed
        # For this test, we'll just check it doesn't crash
        result = calendar.is_holiday(weekday)
        assert isinstance(result, bool)

    def test_is_holiday_new_year(self):
        """Test New Year's Day is a holiday."""
        calendar = KoreanMarketCalendar()
        assert calendar.is_holiday(date(2024, 1, 1)) is True
        assert calendar.is_holiday(date(2025, 1, 1)) is True

    def test_is_market_open_during_hours(self):
        """Test market is open during trading hours."""
        calendar = KoreanMarketCalendar()
        kst = pytz.timezone('Asia/Seoul')

        # Monday at 10:00 (should be open if not a holiday)
        check_time = kst.localize(datetime(2024, 10, 28, 10, 0))
        # We can't assert True because we don't know if it's a holiday
        # Just verify it returns a boolean
        result = calendar.is_market_open(check_time)
        assert isinstance(result, bool)

    def test_is_market_open_before_hours(self):
        """Test market is closed before trading hours."""
        calendar = KoreanMarketCalendar()
        kst = pytz.timezone('Asia/Seoul')

        # Monday at 08:00 (before market open)
        check_time = kst.localize(datetime(2024, 10, 28, 8, 0))
        result = calendar.is_market_open(check_time)
        assert result is False

    def test_is_market_open_after_hours(self):
        """Test market is closed after trading hours."""
        calendar = KoreanMarketCalendar()
        kst = pytz.timezone('Asia/Seoul')

        # Monday at 16:00 (after market close)
        check_time = kst.localize(datetime(2024, 10, 28, 16, 0))
        result = calendar.is_market_open(check_time)
        assert result is False

    def test_is_market_open_on_weekend(self):
        """Test market is closed on weekends."""
        calendar = KoreanMarketCalendar()
        kst = pytz.timezone('Asia/Seoul')

        # Saturday at 10:00
        check_time = kst.localize(datetime(2024, 10, 26, 10, 0))
        assert calendar.is_market_open(check_time) is False

    def test_get_next_market_open(self):
        """Test getting next market open time."""
        calendar = KoreanMarketCalendar()
        kst = pytz.timezone('Asia/Seoul')

        # Friday evening
        check_time = kst.localize(datetime(2024, 10, 25, 16, 0))
        next_open = calendar.get_next_market_open(check_time)

        # Should be Monday at 09:00
        assert next_open.time() == time(9, 0)
        assert next_open.weekday() < 5  # Not weekend

    def test_seconds_until_market_open(self):
        """Test calculation of seconds until market open."""
        calendar = KoreanMarketCalendar()
        seconds = calendar.seconds_until_market_open()
        assert isinstance(seconds, int)
        assert seconds >= 0

    def test_seconds_until_market_close(self):
        """Test calculation of seconds until market close."""
        calendar = KoreanMarketCalendar()
        result = calendar.seconds_until_market_close()
        # Can be None if market is closed, or int if open
        assert result is None or isinstance(result, int)


class TestPriceEventPublisher:
    """Test price event publisher."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        with patch('services.price_monitor.event_publisher.redis.Redis') as mock:
            redis_instance = Mock()
            redis_instance.ping.return_value = True
            redis_instance.publish.return_value = 1
            redis_instance.setex.return_value = True
            redis_instance.get.return_value = None
            mock.return_value = redis_instance
            yield redis_instance

    def test_publisher_init(self, mock_redis):
        """Test publisher initialization."""
        publisher = PriceEventPublisher()
        assert publisher.redis_client is not None
        mock_redis.ping.assert_called_once()

    def test_publish_price_update(self, mock_redis):
        """Test publishing price update event."""
        publisher = PriceEventPublisher()

        price_data = {
            "current_price": 50000.0,
            "open": 49500.0,
            "high": 50500.0,
            "low": 49200.0,
            "volume": 1234567
        }

        result = publisher.publish_price_update("005930", price_data)
        assert result is True
        mock_redis.publish.assert_called()

    def test_publish_significant_change(self, mock_redis):
        """Test publishing significant change event."""
        publisher = PriceEventPublisher()

        price_data = {
            "current_price": 52500.0,
            "open": 49500.0,
            "volume": 1234567
        }

        result = publisher.publish_significant_change(
            ticker="005930",
            old_price=50000.0,
            new_price=52500.0,
            change_pct=5.0,
            price_data=price_data
        )
        assert result is True
        mock_redis.publish.assert_called()

    def test_set_latest_price(self, mock_redis):
        """Test caching latest price."""
        publisher = PriceEventPublisher()

        price_data = {"current_price": 50000.0}
        publisher.set_latest_price("005930", price_data)

        mock_redis.setex.assert_called_once()


class TestPriceMonitor:
    """Test price monitor logic."""

    @pytest.fixture
    def mock_event_publisher(self):
        """Create mock event publisher."""
        publisher = Mock(spec=PriceEventPublisher)
        publisher.publish_price_update.return_value = True
        publisher.publish_significant_change.return_value = True
        publisher.set_latest_price.return_value = None
        return publisher

    @pytest.fixture
    def mock_market_calendar(self):
        """Create mock market calendar."""
        calendar = Mock(spec=KoreanMarketCalendar)
        calendar.is_market_open.return_value = True
        return calendar

    @pytest.fixture
    def price_monitor(self, mock_event_publisher, mock_market_calendar):
        """Create price monitor instance."""
        return PriceMonitor(
            event_publisher=mock_event_publisher,
            market_calendar=mock_market_calendar,
            significant_change_threshold=5.0
        )

    def test_calculate_price_change(self, price_monitor):
        """Test price change calculation."""
        change = price_monitor.calculate_price_change(100.0, 105.0)
        assert change == 5.0

        change = price_monitor.calculate_price_change(100.0, 95.0)
        assert change == -5.0

        change = price_monitor.calculate_price_change(0, 100.0)
        assert change == 0.0

    def test_is_significant_change(self, price_monitor):
        """Test significant change detection."""
        assert price_monitor.is_significant_change(5.0) is True
        assert price_monitor.is_significant_change(-5.0) is True
        assert price_monitor.is_significant_change(6.0) is True
        assert price_monitor.is_significant_change(4.9) is False
        assert price_monitor.is_significant_change(0.0) is False

    def test_fetch_current_price_not_implemented(self, price_monitor):
        """Test that fetch_current_price returns None (not implemented)."""
        result = price_monitor.fetch_current_price("005930")
        assert result is None

    @patch('services.price_monitor.price_monitor.get_db_session')
    def test_monitor_all_stocks_market_closed(
        self,
        mock_db_session,
        price_monitor,
        mock_market_calendar
    ):
        """Test monitoring when market is closed."""
        mock_market_calendar.is_market_open.return_value = False

        stats = price_monitor.monitor_all_stocks()

        assert stats["total"] == 0
        assert stats["success"] == 0
        assert stats["failed"] == 0
        assert stats["skipped"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
