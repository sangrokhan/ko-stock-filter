"""
Financial Data Repository.

Handles data retrieval and storage for financial indicator calculations.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import logging

from shared.database.models import (
    Stock,
    StockPrice,
    FundamentalIndicator
)

logger = logging.getLogger(__name__)


class FinancialDataRepository:
    """Repository for financial data access."""

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

    def get_latest_price(self, stock_id: int, as_of_date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Get the latest stock price for a stock.

        Args:
            stock_id: Stock ID
            as_of_date: Get price as of this date (default: today)

        Returns:
            Dictionary with price data or None
        """
        try:
            query = self.db.query(StockPrice).filter(StockPrice.stock_id == stock_id)

            if as_of_date:
                query = query.filter(StockPrice.date <= as_of_date)

            price = query.order_by(desc(StockPrice.date)).first()

            if not price:
                self.logger.debug(f"No price data found for stock {stock_id}")
                return None

            return {
                'date': price.date,
                'close': float(price.close) if price.close else None,
                'adjusted_close': float(price.adjusted_close) if price.adjusted_close else None,
            }
        except Exception as e:
            self.logger.error(f"Error retrieving latest price for stock {stock_id}: {e}")
            return None

    def get_latest_fundamental_data(
        self,
        stock_id: int,
        as_of_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest fundamental data for a stock.

        Args:
            stock_id: Stock ID
            as_of_date: Get data as of this date (default: today)

        Returns:
            Dictionary with fundamental data or None
        """
        try:
            query = self.db.query(FundamentalIndicator).filter(
                FundamentalIndicator.stock_id == stock_id
            )

            if as_of_date:
                query = query.filter(FundamentalIndicator.date <= as_of_date)

            fundamental = query.order_by(desc(FundamentalIndicator.date)).first()

            if not fundamental:
                self.logger.debug(f"No fundamental data found for stock {stock_id}")
                return None

            return {
                'date': fundamental.date,
                'revenue': fundamental.revenue,
                'operating_profit': fundamental.operating_profit,
                'net_income': fundamental.net_income,
                'total_assets': fundamental.total_assets,
                'total_equity': fundamental.total_equity,
                'total_debt': fundamental.total_debt,
                'eps': fundamental.eps,
                'bps': fundamental.bps,
            }
        except Exception as e:
            self.logger.error(f"Error retrieving fundamental data for stock {stock_id}: {e}")
            return None

    def get_previous_period_data(
        self,
        stock_id: int,
        current_date: datetime,
        lookback_days: int = 365
    ) -> Optional[Dict[str, Any]]:
        """
        Get fundamental data from previous period (typically 1 year ago).

        Args:
            stock_id: Stock ID
            current_date: Current date
            lookback_days: Number of days to look back (default: 365 for YoY)

        Returns:
            Dictionary with previous period fundamental data or None
        """
        try:
            target_date = current_date - timedelta(days=lookback_days)
            # Allow some flexibility in the date range (±30 days)
            date_from = target_date - timedelta(days=30)
            date_to = target_date + timedelta(days=30)

            fundamental = (
                self.db.query(FundamentalIndicator)
                .filter(
                    and_(
                        FundamentalIndicator.stock_id == stock_id,
                        FundamentalIndicator.date >= date_from,
                        FundamentalIndicator.date <= date_to
                    )
                )
                .order_by(desc(FundamentalIndicator.date))
                .first()
            )

            if not fundamental:
                self.logger.debug(
                    f"No previous period data found for stock {stock_id} around {target_date}"
                )
                return None

            return {
                'date': fundamental.date,
                'revenue': fundamental.revenue,
                'eps': fundamental.eps,
            }
        except Exception as e:
            self.logger.error(f"Error retrieving previous period data for stock {stock_id}: {e}")
            return None

    def get_current_financial_data(
        self,
        stock_id: int,
        stock: Stock,
        as_of_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get all current financial data needed for indicator calculation.

        Args:
            stock_id: Stock ID
            stock: Stock object
            as_of_date: Get data as of this date (default: today)

        Returns:
            Dictionary with all current financial data or None
        """
        try:
            # Get latest price
            price_data = self.get_latest_price(stock_id, as_of_date)
            if not price_data:
                self.logger.warning(f"No price data for stock {stock_id}")
                return None

            # Get latest fundamental data
            fundamental_data = self.get_latest_fundamental_data(stock_id, as_of_date)
            if not fundamental_data:
                self.logger.warning(f"No fundamental data for stock {stock_id}")
                return None

            # Combine all data
            return {
                'current_price': price_data.get('close') or price_data.get('adjusted_close'),
                'net_income': fundamental_data.get('net_income'),
                'total_equity': fundamental_data.get('total_equity'),
                'total_debt': fundamental_data.get('total_debt'),
                'total_assets': fundamental_data.get('total_assets'),
                'operating_profit': fundamental_data.get('operating_profit'),
                'revenue': fundamental_data.get('revenue'),
                'shares_outstanding': stock.listed_shares,
                'price_date': price_data.get('date'),
                'fundamental_date': fundamental_data.get('date'),
            }
        except Exception as e:
            self.logger.error(f"Error retrieving current financial data for stock {stock_id}: {e}")
            return None

    def save_fundamental_indicators(
        self,
        stock_id: int,
        indicators: Dict[str, Any],
        calculation_date: Optional[datetime] = None
    ) -> bool:
        """
        Save calculated fundamental indicators to database.

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

            # Check if indicators already exist for this date
            existing = (
                self.db.query(FundamentalIndicator)
                .filter(
                    and_(
                        FundamentalIndicator.stock_id == stock_id,
                        FundamentalIndicator.date == calculation_date.date()
                    )
                )
                .first()
            )

            if existing:
                # Update existing record
                for key, value in indicators.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                self.logger.info(f"Updated existing fundamental indicators for stock {stock_id}")
            else:
                # Create new record
                fundamental = FundamentalIndicator(
                    stock_id=stock_id,
                    **indicators
                )
                self.db.add(fundamental)
                self.logger.info(f"Created new fundamental indicators for stock {stock_id}")

            self.db.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error saving fundamental indicators for stock {stock_id}: {e}")
            self.db.rollback()
            return False

    def get_stocks_without_recent_indicators(
        self,
        days_threshold: int = 1
    ) -> List[Stock]:
        """
        Get stocks that don't have indicators calculated recently.

        Args:
            days_threshold: Number of days to consider as "recent" (default: 1)

        Returns:
            List of Stock objects
        """
        try:
            threshold_date = datetime.utcnow() - timedelta(days=days_threshold)

            # Subquery to get stocks with recent indicators
            recent_stocks = (
                self.db.query(FundamentalIndicator.stock_id)
                .filter(FundamentalIndicator.date >= threshold_date)
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
                f"Found {len(stocks)} stocks without indicators in the last {days_threshold} days"
            )
            return stocks

        except Exception as e:
            self.logger.error(f"Error getting stocks without recent indicators: {e}")
            return []
