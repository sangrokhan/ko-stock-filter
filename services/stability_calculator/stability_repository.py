"""
Stability Data Repository.

Handles data retrieval and storage for stability score calculations.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
import logging

from shared.database.models import (
    Stock,
    StockPrice,
    FundamentalIndicator,
    StabilityScore
)

logger = logging.getLogger(__name__)


class StabilityDataRepository:
    """Repository for stability calculation data access."""

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

    def get_price_history(
        self,
        stock_id: int,
        lookback_days: int = 252,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data for a stock.

        Args:
            stock_id: Stock ID
            lookback_days: Number of days to look back
            end_date: End date (default: today)

        Returns:
            List of price dictionaries with date, close, volume
        """
        try:
            if end_date is None:
                end_date = datetime.utcnow()

            start_date = end_date - timedelta(days=lookback_days)

            prices = (
                self.db.query(StockPrice)
                .filter(
                    and_(
                        StockPrice.stock_id == stock_id,
                        StockPrice.date >= start_date,
                        StockPrice.date <= end_date
                    )
                )
                .order_by(StockPrice.date)
                .all()
            )

            result = []
            for price in prices:
                result.append({
                    'date': price.date,
                    'close': float(price.close) if price.close else None,
                    'volume': int(price.volume) if price.volume else None,
                    'adjusted_close': float(price.adjusted_close) if price.adjusted_close else None,
                })

            self.logger.debug(f"Retrieved {len(result)} price records for stock {stock_id}")
            return result

        except Exception as e:
            self.logger.error(f"Error retrieving price history for stock {stock_id}: {e}")
            return []

    def get_market_index_history(
        self,
        lookback_days: int = 252,
        end_date: Optional[datetime] = None,
        index_ticker: str = "^KS11"  # KOSPI index
    ) -> List[Dict[str, Any]]:
        """
        Get historical market index data.

        Args:
            lookback_days: Number of days to look back
            end_date: End date (default: today)
            index_ticker: Market index ticker (default: KOSPI)

        Returns:
            List of price dictionaries with date, close
        """
        try:
            if end_date is None:
                end_date = datetime.utcnow()

            start_date = end_date - timedelta(days=lookback_days)

            # First, get the stock_id for the index
            index_stock = self.db.query(Stock).filter(Stock.ticker == index_ticker).first()
            if not index_stock:
                self.logger.warning(f"Market index {index_ticker} not found in database")
                return []

            prices = (
                self.db.query(StockPrice)
                .filter(
                    and_(
                        StockPrice.stock_id == index_stock.id,
                        StockPrice.date >= start_date,
                        StockPrice.date <= end_date
                    )
                )
                .order_by(StockPrice.date)
                .all()
            )

            result = []
            for price in prices:
                result.append({
                    'date': price.date,
                    'close': float(price.close) if price.close else None,
                })

            self.logger.debug(f"Retrieved {len(result)} market index records")
            return result

        except Exception as e:
            self.logger.error(f"Error retrieving market index history: {e}")
            return []

    def get_earnings_history(
        self,
        stock_id: int,
        num_periods: int = 8,
        end_date: Optional[datetime] = None
    ) -> List[float]:
        """
        Get historical earnings data for a stock.

        Args:
            stock_id: Stock ID
            num_periods: Number of periods to retrieve
            end_date: End date (default: today)

        Returns:
            List of earnings values (net income)
        """
        try:
            if end_date is None:
                end_date = datetime.utcnow()

            # Get the most recent earnings records
            fundamentals = (
                self.db.query(FundamentalIndicator)
                .filter(
                    and_(
                        FundamentalIndicator.stock_id == stock_id,
                        FundamentalIndicator.date <= end_date,
                        FundamentalIndicator.net_income.isnot(None)
                    )
                )
                .order_by(desc(FundamentalIndicator.date))
                .limit(num_periods)
                .all()
            )

            # Reverse to get chronological order
            earnings = [float(f.net_income) for f in reversed(fundamentals) if f.net_income]

            self.logger.debug(f"Retrieved {len(earnings)} earnings records for stock {stock_id}")
            return earnings

        except Exception as e:
            self.logger.error(f"Error retrieving earnings history for stock {stock_id}: {e}")
            return []

    def get_debt_ratio_history(
        self,
        stock_id: int,
        num_periods: int = 8,
        end_date: Optional[datetime] = None
    ) -> List[float]:
        """
        Get historical debt ratio data for a stock.

        Args:
            stock_id: Stock ID
            num_periods: Number of periods to retrieve
            end_date: End date (default: today)

        Returns:
            List of debt ratio values
        """
        try:
            if end_date is None:
                end_date = datetime.utcnow()

            # Get the most recent debt ratio records
            fundamentals = (
                self.db.query(FundamentalIndicator)
                .filter(
                    and_(
                        FundamentalIndicator.stock_id == stock_id,
                        FundamentalIndicator.date <= end_date,
                        FundamentalIndicator.debt_ratio.isnot(None)
                    )
                )
                .order_by(desc(FundamentalIndicator.date))
                .limit(num_periods)
                .all()
            )

            # Reverse to get chronological order
            debt_ratios = [float(f.debt_ratio) for f in reversed(fundamentals) if f.debt_ratio is not None]

            self.logger.debug(f"Retrieved {len(debt_ratios)} debt ratio records for stock {stock_id}")
            return debt_ratios

        except Exception as e:
            self.logger.error(f"Error retrieving debt ratio history for stock {stock_id}: {e}")
            return []

    def get_all_stability_data(
        self,
        stock_id: int,
        lookback_days: int = 252,
        num_fundamental_periods: int = 8,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get all data needed for stability calculation.

        Args:
            stock_id: Stock ID
            lookback_days: Days to look back for price data
            num_fundamental_periods: Number of fundamental periods to retrieve
            end_date: End date (default: today)

        Returns:
            Dictionary with all required data
        """
        try:
            if end_date is None:
                end_date = datetime.utcnow()

            return {
                'price_data': self.get_price_history(stock_id, lookback_days, end_date),
                'market_data': self.get_market_index_history(lookback_days, end_date),
                'earnings_data': self.get_earnings_history(stock_id, num_fundamental_periods, end_date),
                'debt_data': self.get_debt_ratio_history(stock_id, num_fundamental_periods, end_date),
            }

        except Exception as e:
            self.logger.error(f"Error retrieving stability data for stock {stock_id}: {e}")
            return {
                'price_data': [],
                'market_data': [],
                'earnings_data': [],
                'debt_data': [],
            }

    def save_stability_score(
        self,
        stock_id: int,
        metrics: Dict[str, Any],
        calculation_date: Optional[datetime] = None
    ) -> bool:
        """
        Save calculated stability score to database.

        Args:
            stock_id: Stock ID
            metrics: Dictionary of calculated metrics
            calculation_date: Date of calculation (default: today)

        Returns:
            True if successful, False otherwise
        """
        try:
            if calculation_date is None:
                calculation_date = datetime.utcnow()

            # Check if stability score already exists for this date
            existing = (
                self.db.query(StabilityScore)
                .filter(
                    and_(
                        StabilityScore.stock_id == stock_id,
                        StabilityScore.date == calculation_date.date()
                    )
                )
                .first()
            )

            if existing:
                # Update existing record
                for key, value in metrics.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                self.logger.info(f"Updated existing stability score for stock {stock_id}")
            else:
                # Create new record
                stability_score = StabilityScore(
                    stock_id=stock_id,
                    **metrics
                )
                self.db.add(stability_score)
                self.logger.info(f"Created new stability score for stock {stock_id}")

            self.db.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error saving stability score for stock {stock_id}: {e}")
            self.db.rollback()
            return False

    def get_stocks_without_recent_stability_scores(
        self,
        days_threshold: int = 1
    ) -> List[Stock]:
        """
        Get stocks that don't have stability scores calculated recently.

        Args:
            days_threshold: Number of days to consider as "recent" (default: 1)

        Returns:
            List of Stock objects
        """
        try:
            threshold_date = datetime.utcnow() - timedelta(days=days_threshold)

            # Subquery to get stocks with recent stability scores
            recent_stocks = (
                self.db.query(StabilityScore.stock_id)
                .filter(StabilityScore.date >= threshold_date)
                .distinct()
            )

            # Get active stocks without recent stability scores
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
                f"Found {len(stocks)} stocks without stability scores in the last {days_threshold} days"
            )
            return stocks

        except Exception as e:
            self.logger.error(f"Error getting stocks without recent stability scores: {e}")
            return []

    def get_latest_stability_score(
        self,
        stock_id: int,
        as_of_date: Optional[datetime] = None
    ) -> Optional[StabilityScore]:
        """
        Get the most recent stability score for a stock.

        Args:
            stock_id: Stock ID
            as_of_date: Get score as of this date (default: today)

        Returns:
            StabilityScore object or None
        """
        try:
            query = self.db.query(StabilityScore).filter(
                StabilityScore.stock_id == stock_id
            )

            if as_of_date:
                query = query.filter(StabilityScore.date <= as_of_date)

            score = query.order_by(desc(StabilityScore.date)).first()

            return score

        except Exception as e:
            self.logger.error(f"Error retrieving latest stability score for stock {stock_id}: {e}")
            return None

    def get_top_stable_stocks(
        self,
        limit: int = 50,
        min_score: float = 50.0,
        as_of_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top stable stocks based on stability score.

        Args:
            limit: Maximum number of stocks to return
            min_score: Minimum stability score threshold
            as_of_date: Get scores as of this date (default: today)

        Returns:
            List of dictionaries with stock and stability info
        """
        try:
            # Subquery to get the latest stability score for each stock
            subq = (
                self.db.query(
                    StabilityScore.stock_id,
                    func.max(StabilityScore.date).label('max_date')
                )
                .group_by(StabilityScore.stock_id)
                .subquery()
            )

            # Join with Stock and StabilityScore tables
            query = (
                self.db.query(Stock, StabilityScore)
                .join(subq, Stock.id == subq.c.stock_id)
                .join(
                    StabilityScore,
                    and_(
                        StabilityScore.stock_id == subq.c.stock_id,
                        StabilityScore.date == subq.c.max_date
                    )
                )
                .filter(
                    and_(
                        Stock.is_active == True,
                        StabilityScore.stability_score >= min_score
                    )
                )
                .order_by(desc(StabilityScore.stability_score))
                .limit(limit)
            )

            if as_of_date:
                query = query.filter(StabilityScore.date <= as_of_date)

            results = []
            for stock, score in query.all():
                results.append({
                    'stock_id': stock.id,
                    'ticker': stock.ticker,
                    'name_kr': stock.name_kr,
                    'market': stock.market,
                    'sector': stock.sector,
                    'stability_score': score.stability_score,
                    'calculation_date': score.date,
                    'price_volatility_score': score.price_volatility_score,
                    'beta_score': score.beta_score,
                    'volume_stability_score': score.volume_stability_score,
                    'earnings_consistency_score': score.earnings_consistency_score,
                    'debt_stability_score': score.debt_stability_score,
                })

            self.logger.info(f"Retrieved {len(results)} top stable stocks")
            return results

        except Exception as e:
            self.logger.error(f"Error getting top stable stocks: {e}")
            return []
