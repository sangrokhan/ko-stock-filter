"""
Technical Indicator Data Repository.

Handles data retrieval and storage for technical indicator calculations.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import logging
import pandas as pd

from shared.database.models import (
    Stock,
    StockPrice,
    TechnicalIndicator
)

logger = logging.getLogger(__name__)


class TechnicalDataRepository:
    """Repository for technical indicator data access."""

    def __init__(self, db_session: Session):
        """
        Initialize the repository.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.logger = logging.getLogger(__name__)

    def get_active_stocks(self) -> List[Stock]:
        """
        Get all active stocks.

        Returns:
            List of active Stock objects
        """
        try:
            stocks = self.db.query(Stock).filter(Stock.is_active == True).all()
            self.logger.info(f"Retrieved {len(stocks)} active stocks")
            return stocks
        except Exception as e:
            self.logger.error(f"Error retrieving active stocks: {e}")
            return []

    def get_stock_by_id(self, stock_id: int) -> Optional[Stock]:
        """
        Get stock by ID.

        Args:
            stock_id: Stock ID

        Returns:
            Stock object or None
        """
        try:
            return self.db.query(Stock).filter(Stock.id == stock_id).first()
        except Exception as e:
            self.logger.error(f"Error retrieving stock {stock_id}: {e}")
            return None

    def get_stock_by_ticker(self, ticker: str) -> Optional[Stock]:
        """
        Get stock by ticker.

        Args:
            ticker: Stock ticker code

        Returns:
            Stock object or None
        """
        try:
            return self.db.query(Stock).filter(Stock.ticker == ticker).first()
        except Exception as e:
            self.logger.error(f"Error retrieving stock {ticker}: {e}")
            return None

    def get_price_history(
        self,
        stock_id: int,
        days: int = 250,
        as_of_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get historical price data for a stock as a pandas DataFrame.

        Args:
            stock_id: Stock ID
            days: Number of days of history to retrieve
            as_of_date: Get prices as of this date (default: today)

        Returns:
            DataFrame with OHLCV data, indexed by date
        """
        try:
            if as_of_date is None:
                as_of_date = datetime.utcnow()

            # Calculate start date
            start_date = as_of_date - timedelta(days=days)

            # Query price data
            prices = (
                self.db.query(StockPrice)
                .filter(
                    and_(
                        StockPrice.stock_id == stock_id,
                        StockPrice.date >= start_date,
                        StockPrice.date <= as_of_date
                    )
                )
                .order_by(StockPrice.date)
                .all()
            )

            if not prices:
                self.logger.warning(f"No price data found for stock {stock_id}")
                return pd.DataFrame()

            # Convert to DataFrame
            data = []
            for price in prices:
                data.append({
                    'date': price.date,
                    'open': float(price.open) if price.open else None,
                    'high': float(price.high) if price.high else None,
                    'low': float(price.low) if price.low else None,
                    'close': float(price.close) if price.close else None,
                    'volume': int(price.volume) if price.volume else 0,
                    'adjusted_close': float(price.adjusted_close) if price.adjusted_close else None,
                })

            df = pd.DataFrame(data)
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            self.logger.info(f"Retrieved {len(df)} days of price data for stock {stock_id}")
            return df

        except Exception as e:
            self.logger.error(f"Error retrieving price history for stock {stock_id}: {e}")
            return pd.DataFrame()

    def get_latest_price_date(self, stock_id: int) -> Optional[datetime]:
        """
        Get the date of the latest price data for a stock.

        Args:
            stock_id: Stock ID

        Returns:
            Latest price date or None
        """
        try:
            price = (
                self.db.query(StockPrice)
                .filter(StockPrice.stock_id == stock_id)
                .order_by(desc(StockPrice.date))
                .first()
            )
            return price.date if price else None
        except Exception as e:
            self.logger.error(f"Error retrieving latest price date for stock {stock_id}: {e}")
            return None

    def save_technical_indicators(
        self,
        stock_id: int,
        indicators: Dict[str, Any],
        calculation_date: Optional[datetime] = None
    ) -> bool:
        """
        Save calculated technical indicators to database.

        Args:
            stock_id: Stock ID
            indicators: Dictionary of calculated indicators
            calculation_date: Date of calculation (default: today)

        Returns:
            True if successful, False otherwise
        """
        try:
            if calculation_date is None:
                calculation_date = datetime.utcnow()

            # Convert date to date object (no time component)
            calc_date = calculation_date.date() if hasattr(calculation_date, 'date') else calculation_date

            # Check if indicators already exist for this date
            existing = (
                self.db.query(TechnicalIndicator)
                .filter(
                    and_(
                        TechnicalIndicator.stock_id == stock_id,
                        TechnicalIndicator.date == calc_date
                    )
                )
                .first()
            )

            if existing:
                # Update existing record
                for key, value in indicators.items():
                    if hasattr(existing, key) and key != 'date':
                        setattr(existing, key, value)
                self.logger.info(f"Updated existing technical indicators for stock {stock_id}")
            else:
                # Create new record
                technical = TechnicalIndicator(
                    stock_id=stock_id,
                    **indicators
                )
                self.db.add(technical)
                self.logger.info(f"Created new technical indicators for stock {stock_id}")

            self.db.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error saving technical indicators for stock {stock_id}: {e}")
            self.db.rollback()
            return False

    def get_stocks_without_recent_indicators(
        self,
        days_threshold: int = 1
    ) -> List[Stock]:
        """
        Get stocks that don't have technical indicators calculated recently.

        Args:
            days_threshold: Number of days to consider as "recent" (default: 1)

        Returns:
            List of Stock objects
        """
        try:
            threshold_date = datetime.utcnow() - timedelta(days=days_threshold)

            # Subquery to get stocks with recent indicators
            recent_stocks = (
                self.db.query(TechnicalIndicator.stock_id)
                .filter(TechnicalIndicator.date >= threshold_date)
                .distinct()
            )

            # Get active stocks without recent indicators
            stocks = (
                self.db.query(Stock)
                .filter(
                    and_(
                        Stock.is_active == True,
                        ~Stock.id.in_(recent_stocks)
                    )
                )
                .all()
            )

            self.logger.info(
                f"Found {len(stocks)} stocks without technical indicators in the last {days_threshold} days"
            )
            return stocks

        except Exception as e:
            self.logger.error(f"Error getting stocks without recent indicators: {e}")
            return []

    def get_stocks_by_tickers(self, tickers: List[str]) -> List[Stock]:
        """
        Get stocks by list of ticker codes.

        Args:
            tickers: List of ticker codes

        Returns:
            List of Stock objects
        """
        try:
            stocks = (
                self.db.query(Stock)
                .filter(
                    and_(
                        Stock.ticker.in_(tickers),
                        Stock.is_active == True
                    )
                )
                .all()
            )
            self.logger.info(f"Retrieved {len(stocks)} stocks from {len(tickers)} tickers")
            return stocks
        except Exception as e:
            self.logger.error(f"Error retrieving stocks by tickers: {e}")
            return []

    def has_sufficient_price_data(
        self,
        stock_id: int,
        min_days: int = 200
    ) -> bool:
        """
        Check if stock has sufficient price data for technical analysis.

        Args:
            stock_id: Stock ID
            min_days: Minimum number of days required

        Returns:
            True if sufficient data exists, False otherwise
        """
        try:
            count = (
                self.db.query(StockPrice)
                .filter(StockPrice.stock_id == stock_id)
                .count()
            )
            return count >= min_days
        except Exception as e:
            self.logger.error(f"Error checking price data for stock {stock_id}: {e}")
            return False
