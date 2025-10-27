"""
Price Monitor - Core monitoring logic.

Monitors stock prices, detects changes, and updates the database.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select

from shared.database.models import Stock, StockPrice
from shared.database.connection import get_db_session
from .event_publisher import PriceEventPublisher
from .market_calendar import KoreanMarketCalendar


logger = logging.getLogger(__name__)


class PriceMonitor:
    """Monitor stock prices and detect significant changes."""

    def __init__(
        self,
        event_publisher: PriceEventPublisher,
        market_calendar: KoreanMarketCalendar,
        significant_change_threshold: float = 5.0
    ):
        """
        Initialize the price monitor.

        Args:
            event_publisher: Event publisher for price updates
            market_calendar: Market calendar for hours detection
            significant_change_threshold: Threshold for significant change (default: 5%)
        """
        self.event_publisher = event_publisher
        self.market_calendar = market_calendar
        self.significant_change_threshold = significant_change_threshold
        logger.info(
            f"Price Monitor initialized with {significant_change_threshold}% "
            f"change threshold"
        )

    def get_active_stocks(self, db: Session) -> List[Stock]:
        """
        Get all active stocks to monitor.

        Args:
            db: Database session

        Returns:
            List of active stocks
        """
        stmt = select(Stock).where(Stock.is_active == True)
        result = db.execute(stmt)
        stocks = result.scalars().all()
        logger.info(f"Retrieved {len(stocks)} active stocks to monitor")
        return stocks

    def get_latest_price_from_db(self, db: Session, stock_id: int) -> Optional[StockPrice]:
        """
        Get the latest price record from database.

        Args:
            db: Database session
            stock_id: Stock ID

        Returns:
            Latest StockPrice record or None
        """
        stmt = (
            select(StockPrice)
            .where(StockPrice.stock_id == stock_id)
            .order_by(StockPrice.date.desc())
            .limit(1)
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def fetch_current_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch current price from market data source.

        NOTE: This is a placeholder. In production, this should integrate with
        Korean stock market APIs (e.g., KIS API, eBest API, etc.)

        Args:
            ticker: Stock ticker symbol

        Returns:
            Price data dictionary or None if unavailable
        """
        # TODO: Integrate with actual Korean stock market API
        # For now, returning a mock structure
        logger.warning(
            f"fetch_current_price for {ticker} is not implemented - "
            f"integrate with Korean stock API"
        )
        return None

        # Example expected return structure:
        # {
        #     "ticker": ticker,
        #     "current_price": 50000.0,
        #     "open": 49500.0,
        #     "high": 50500.0,
        #     "low": 49200.0,
        #     "volume": 1234567,
        #     "trading_value": 61728350000,
        #     "timestamp": datetime.utcnow()
        # }

    def calculate_price_change(
        self,
        old_price: float,
        new_price: float
    ) -> float:
        """
        Calculate percentage price change.

        Args:
            old_price: Previous price
            new_price: Current price

        Returns:
            Percentage change
        """
        if old_price == 0:
            return 0.0
        return ((new_price - old_price) / old_price) * 100

    def is_significant_change(self, change_pct: float) -> bool:
        """
        Check if price change is significant.

        Args:
            change_pct: Percentage change

        Returns:
            True if change exceeds threshold
        """
        return abs(change_pct) >= self.significant_change_threshold

    def update_price_in_db(
        self,
        db: Session,
        stock_id: int,
        price_data: Dict[str, Any]
    ) -> StockPrice:
        """
        Update stock price in database.

        Args:
            db: Database session
            stock_id: Stock ID
            price_data: Price data dictionary

        Returns:
            Created StockPrice record
        """
        stock_price = StockPrice(
            stock_id=stock_id,
            date=price_data.get("timestamp", datetime.utcnow()),
            open=Decimal(str(price_data["open"])),
            high=Decimal(str(price_data["high"])),
            low=Decimal(str(price_data["low"])),
            close=Decimal(str(price_data["current_price"])),
            volume=price_data["volume"],
            trading_value=price_data.get("trading_value"),
            change_pct=price_data.get("change_pct")
        )

        db.add(stock_price)
        db.commit()
        db.refresh(stock_price)

        logger.info(
            f"Updated price for stock_id={stock_id}, "
            f"price={price_data['current_price']}"
        )
        return stock_price

    def process_stock_price(self, stock: Stock, db: Session) -> bool:
        """
        Process a single stock's price update.

        Args:
            stock: Stock object
            db: Database session

        Returns:
            True if processing was successful
        """
        try:
            # Fetch current price from market
            current_price_data = self.fetch_current_price(stock.ticker)

            if current_price_data is None:
                logger.debug(f"No price data available for {stock.ticker}")
                return False

            # Get latest price from database
            latest_db_price = self.get_latest_price_from_db(db, stock.id)

            # Calculate price change if we have historical data
            change_pct = 0.0
            if latest_db_price and latest_db_price.close:
                old_price = float(latest_db_price.close)
                new_price = current_price_data["current_price"]
                change_pct = self.calculate_price_change(old_price, new_price)
                current_price_data["change_pct"] = change_pct

            # Update database
            self.update_price_in_db(db, stock.id, current_price_data)

            # Publish price update event
            self.event_publisher.publish_price_update(
                stock.ticker,
                current_price_data
            )

            # Cache latest price in Redis
            self.event_publisher.set_latest_price(stock.ticker, current_price_data)

            # Check for significant changes
            if latest_db_price and self.is_significant_change(change_pct):
                logger.warning(
                    f"Significant price change detected for {stock.ticker}: "
                    f"{change_pct:.2f}%"
                )
                self.event_publisher.publish_significant_change(
                    ticker=stock.ticker,
                    old_price=float(latest_db_price.close),
                    new_price=current_price_data["current_price"],
                    change_pct=change_pct,
                    price_data=current_price_data
                )

            return True

        except Exception as e:
            logger.error(f"Error processing price for {stock.ticker}: {e}", exc_info=True)
            return False

    def monitor_all_stocks(self) -> Dict[str, int]:
        """
        Monitor prices for all active stocks.

        Returns:
            Statistics dictionary with success/failure counts
        """
        stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0
        }

        # Check if market is open
        if not self.market_calendar.is_market_open():
            logger.info("Market is closed - skipping price monitoring")
            return stats

        with get_db_session() as db:
            stocks = self.get_active_stocks(db)
            stats["total"] = len(stocks)

            for stock in stocks:
                try:
                    success = self.process_stock_price(stock, db)
                    if success:
                        stats["success"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception as e:
                    logger.error(
                        f"Failed to process stock {stock.ticker}: {e}",
                        exc_info=True
                    )
                    stats["failed"] += 1

        logger.info(
            f"Price monitoring completed - "
            f"Total: {stats['total']}, "
            f"Success: {stats['success']}, "
            f"Failed: {stats['failed']}, "
            f"Skipped: {stats['skipped']}"
        )

        return stats
