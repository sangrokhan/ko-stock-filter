"""
Event Publisher for price updates and alerts.

Publishes events to Redis for consumption by other services.
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import redis
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)


class PriceEventPublisher:
    """Publisher for stock price events to Redis."""

    # Event channels
    CHANNEL_PRICE_UPDATE = "stock:price:update"
    CHANNEL_PRICE_ALERT = "stock:price:alert"
    CHANNEL_SIGNIFICANT_CHANGE = "stock:price:significant_change"

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None
    ):
        """
        Initialize the event publisher.

        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            redis_password: Redis password (optional)
        """
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )
        self._test_connection()

    def _test_connection(self):
        """Test Redis connection."""
        try:
            self.redis_client.ping()
            logger.info("Successfully connected to Redis")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _serialize_event(self, data: Dict[str, Any]) -> str:
        """
        Serialize event data to JSON.

        Args:
            data: Event data dictionary

        Returns:
            JSON string
        """
        # Convert Decimal to float for JSON serialization
        def converter(o):
            if isinstance(o, Decimal):
                return float(o)
            if isinstance(o, datetime):
                return o.isoformat()
            raise TypeError(f"Object of type {type(o)} is not JSON serializable")

        return json.dumps(data, default=converter)

    def publish_price_update(
        self,
        ticker: str,
        price_data: Dict[str, Any]
    ) -> bool:
        """
        Publish a price update event.

        Args:
            ticker: Stock ticker symbol
            price_data: Price data dictionary containing current price info

        Returns:
            True if published successfully
        """
        try:
            event = {
                "event_type": "price_update",
                "ticker": ticker,
                "timestamp": datetime.utcnow().isoformat(),
                "data": price_data
            }

            message = self._serialize_event(event)
            subscribers = self.redis_client.publish(self.CHANNEL_PRICE_UPDATE, message)

            logger.debug(
                f"Published price update for {ticker} to {subscribers} subscribers"
            )
            return True

        except RedisError as e:
            logger.error(f"Failed to publish price update for {ticker}: {e}")
            return False

    def publish_significant_change(
        self,
        ticker: str,
        old_price: float,
        new_price: float,
        change_pct: float,
        price_data: Dict[str, Any]
    ) -> bool:
        """
        Publish a significant price change event.

        Args:
            ticker: Stock ticker symbol
            old_price: Previous price
            new_price: Current price
            change_pct: Percentage change
            price_data: Complete price data

        Returns:
            True if published successfully
        """
        try:
            event = {
                "event_type": "significant_change",
                "ticker": ticker,
                "timestamp": datetime.utcnow().isoformat(),
                "old_price": old_price,
                "new_price": new_price,
                "change_pct": change_pct,
                "data": price_data
            }

            message = self._serialize_event(event)
            subscribers = self.redis_client.publish(
                self.CHANNEL_SIGNIFICANT_CHANGE,
                message
            )

            logger.info(
                f"Published significant change for {ticker}: "
                f"{change_pct:.2f}% change to {subscribers} subscribers"
            )
            return True

        except RedisError as e:
            logger.error(
                f"Failed to publish significant change for {ticker}: {e}"
            )
            return False

    def publish_price_alert(
        self,
        ticker: str,
        alert_type: str,
        message: str,
        price_data: Dict[str, Any]
    ) -> bool:
        """
        Publish a price alert event.

        Args:
            ticker: Stock ticker symbol
            alert_type: Type of alert (e.g., 'threshold_breach', 'volatility')
            message: Alert message
            price_data: Price data associated with alert

        Returns:
            True if published successfully
        """
        try:
            event = {
                "event_type": "price_alert",
                "ticker": ticker,
                "alert_type": alert_type,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "data": price_data
            }

            message_str = self._serialize_event(event)
            subscribers = self.redis_client.publish(self.CHANNEL_PRICE_ALERT, message_str)

            logger.info(
                f"Published price alert for {ticker} ({alert_type}) "
                f"to {subscribers} subscribers"
            )
            return True

        except RedisError as e:
            logger.error(f"Failed to publish price alert for {ticker}: {e}")
            return False

    def set_latest_price(self, ticker: str, price_data: Dict[str, Any], ttl: int = 3600):
        """
        Store the latest price in Redis cache.

        Args:
            ticker: Stock ticker symbol
            price_data: Price data to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        try:
            key = f"stock:latest_price:{ticker}"
            value = self._serialize_event(price_data)
            self.redis_client.setex(key, ttl, value)
            logger.debug(f"Cached latest price for {ticker}")
        except RedisError as e:
            logger.error(f"Failed to cache price for {ticker}: {e}")

    def get_latest_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest cached price.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Price data dictionary or None if not found
        """
        try:
            key = f"stock:latest_price:{ticker}"
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except RedisError as e:
            logger.error(f"Failed to retrieve cached price for {ticker}: {e}")
            return None

    def close(self):
        """Close Redis connection."""
        try:
            self.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
