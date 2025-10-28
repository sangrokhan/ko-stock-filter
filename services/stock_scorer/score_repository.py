"""
Score Data Repository.

Handles data retrieval and storage for composite score calculations.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
import logging

from shared.database.models import (
    Stock,
    StockPrice,
    FundamentalIndicator,
    TechnicalIndicator,
    CompositeScore,
    Watchlist
)

logger = logging.getLogger(__name__)


class ScoreDataRepository:
    """Repository for score calculation data access."""

    def __init__(self, db_session: Session):
        """
        Initialize the repository.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.logger = logging.getLogger(__name__)

    def get_active_stocks(self, limit: Optional[int] = None) -> List[Stock]:
        """
        Get all active stocks.

        Args:
            limit: Optional limit on number of stocks to return

        Returns:
            List of active Stock objects
        """
        try:
            query = self.db.query(Stock).filter(Stock.is_active == True)
            if limit:
                query = query.limit(limit)
            stocks = query.all()
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
            ticker: Stock ticker

        Returns:
            Stock object or None
        """
        try:
            return self.db.query(Stock).filter(Stock.ticker == ticker).first()
        except Exception as e:
            self.logger.error(f"Error retrieving stock {ticker}: {e}")
            return None

    def get_latest_fundamental_data(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the most recent fundamental indicator data for a stock.

        Args:
            stock_id: Stock ID

        Returns:
            Dictionary with fundamental metrics or None
        """
        try:
            fundamental = (
                self.db.query(FundamentalIndicator)
                .filter(FundamentalIndicator.stock_id == stock_id)
                .order_by(desc(FundamentalIndicator.date))
                .first()
            )

            if not fundamental:
                return None

            return {
                'date': fundamental.date,
                'per': fundamental.per,
                'pbr': fundamental.pbr,
                'pcr': fundamental.pcr,
                'psr': fundamental.psr,
                'roe': fundamental.roe,
                'roa': fundamental.roa,
                'roic': fundamental.roic,
                'operating_margin': fundamental.operating_margin,
                'net_margin': fundamental.net_margin,
                'debt_ratio': fundamental.debt_ratio,
                'debt_to_equity': fundamental.debt_to_equity,
                'current_ratio': fundamental.current_ratio,
                'quick_ratio': fundamental.quick_ratio,
                'interest_coverage': fundamental.interest_coverage,
                'revenue_growth': fundamental.revenue_growth,
                'earnings_growth': fundamental.earnings_growth,
                'equity_growth': fundamental.equity_growth,
                'dividend_yield': fundamental.dividend_yield,
                'dividend_payout_ratio': fundamental.dividend_payout_ratio,
                'eps': fundamental.eps,
                'bps': fundamental.bps,
                'cps': fundamental.cps,
                'sps': fundamental.sps,
                'dps': fundamental.dps,
                'revenue': fundamental.revenue,
                'operating_profit': fundamental.operating_profit,
                'net_income': fundamental.net_income,
                'total_assets': fundamental.total_assets,
                'total_equity': fundamental.total_equity,
                'total_debt': fundamental.total_debt,
            }

        except Exception as e:
            self.logger.error(f"Error retrieving fundamental data for stock {stock_id}: {e}")
            return None

    def get_latest_technical_data(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the most recent technical indicator data for a stock.

        Args:
            stock_id: Stock ID

        Returns:
            Dictionary with technical metrics or None
        """
        try:
            technical = (
                self.db.query(TechnicalIndicator)
                .filter(TechnicalIndicator.stock_id == stock_id)
                .order_by(desc(TechnicalIndicator.date))
                .first()
            )

            if not technical:
                return None

            return {
                'date': technical.date,
                'rsi_14': technical.rsi_14,
                'rsi_9': technical.rsi_9,
                'stochastic_k': technical.stochastic_k,
                'stochastic_d': technical.stochastic_d,
                'macd': technical.macd,
                'macd_signal': technical.macd_signal,
                'macd_histogram': technical.macd_histogram,
                'adx': technical.adx,
                'sma_5': technical.sma_5,
                'sma_20': technical.sma_20,
                'sma_50': technical.sma_50,
                'sma_120': technical.sma_120,
                'sma_200': technical.sma_200,
                'ema_12': technical.ema_12,
                'ema_26': technical.ema_26,
                'bollinger_upper': technical.bollinger_upper,
                'bollinger_middle': technical.bollinger_middle,
                'bollinger_lower': technical.bollinger_lower,
                'atr': technical.atr,
                'obv': technical.obv,
                'volume_ma_20': technical.volume_ma_20,
            }

        except Exception as e:
            self.logger.error(f"Error retrieving technical data for stock {stock_id}: {e}")
            return None

    def get_price_history(
        self,
        stock_id: int,
        lookback_days: int = 60,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data for a stock.

        Args:
            stock_id: Stock ID
            lookback_days: Number of days to look back
            end_date: End date (default: today)

        Returns:
            List of price dictionaries with date, close, volume, etc.
        """
        try:
            if end_date is None:
                end_date = datetime.utcnow()

            start_date = end_date - timedelta(days=lookback_days * 2)  # Get extra for weekends/holidays

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
                    'open': float(price.open) if price.open else None,
                    'high': float(price.high) if price.high else None,
                    'low': float(price.low) if price.low else None,
                    'close': float(price.close) if price.close else None,
                    'volume': int(price.volume) if price.volume else None,
                    'adjusted_close': float(price.adjusted_close) if price.adjusted_close else None,
                })

            self.logger.debug(f"Retrieved {len(result)} price records for stock {stock_id}")
            return result

        except Exception as e:
            self.logger.error(f"Error retrieving price history for stock {stock_id}: {e}")
            return []

    def save_composite_score(self, stock_id: int, score_data: Dict[str, Any]) -> bool:
        """
        Save composite score to database.

        Args:
            stock_id: Stock ID
            score_data: Dictionary with score metrics

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if score already exists for this stock and date
            existing = (
                self.db.query(CompositeScore)
                .filter(
                    and_(
                        CompositeScore.stock_id == stock_id,
                        CompositeScore.date == score_data['date']
                    )
                )
                .first()
            )

            if existing:
                # Update existing score
                for key, value in score_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                self.logger.debug(f"Updated composite score for stock {stock_id}")
            else:
                # Create new score
                score = CompositeScore(
                    stock_id=stock_id,
                    **score_data
                )
                self.db.add(score)
                self.logger.debug(f"Created new composite score for stock {stock_id}")

            self.db.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error saving composite score for stock {stock_id}: {e}")
            self.db.rollback()
            return False

    def get_latest_composite_score(self, stock_id: int) -> Optional[CompositeScore]:
        """
        Get the most recent composite score for a stock.

        Args:
            stock_id: Stock ID

        Returns:
            CompositeScore object or None
        """
        try:
            return (
                self.db.query(CompositeScore)
                .filter(CompositeScore.stock_id == stock_id)
                .order_by(desc(CompositeScore.date))
                .first()
            )
        except Exception as e:
            self.logger.error(f"Error retrieving composite score for stock {stock_id}: {e}")
            return None

    def get_top_scored_stocks(
        self,
        limit: int = 50,
        min_score: Optional[float] = None,
        date: Optional[datetime] = None
    ) -> List[Tuple[Stock, CompositeScore]]:
        """
        Get top-scoring stocks.

        Args:
            limit: Maximum number of stocks to return
            min_score: Minimum composite score threshold
            date: Specific date to query (default: latest)

        Returns:
            List of (Stock, CompositeScore) tuples ordered by composite_score descending
        """
        try:
            # Get latest scores for each stock
            subquery = (
                self.db.query(
                    CompositeScore.stock_id,
                    func.max(CompositeScore.date).label('max_date')
                )
                .group_by(CompositeScore.stock_id)
                .subquery()
            )

            query = (
                self.db.query(Stock, CompositeScore)
                .join(
                    CompositeScore,
                    Stock.id == CompositeScore.stock_id
                )
                .join(
                    subquery,
                    and_(
                        CompositeScore.stock_id == subquery.c.stock_id,
                        CompositeScore.date == subquery.c.max_date
                    )
                )
                .filter(Stock.is_active == True)
            )

            if min_score is not None:
                query = query.filter(CompositeScore.composite_score >= min_score)

            if date is not None:
                query = query.filter(CompositeScore.date == date)

            query = query.order_by(desc(CompositeScore.composite_score)).limit(limit)

            results = query.all()
            self.logger.info(f"Retrieved {len(results)} top-scoring stocks")
            return results

        except Exception as e:
            self.logger.error(f"Error retrieving top-scoring stocks: {e}")
            return []

    def calculate_percentile_ranks(self, date: Optional[datetime] = None) -> bool:
        """
        Calculate and update percentile ranks for all stocks.

        Args:
            date: Specific date to calculate for (default: latest)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all scores for the given date
            if date is None:
                # Get latest date
                latest_date = (
                    self.db.query(func.max(CompositeScore.date))
                    .scalar()
                )
                if not latest_date:
                    self.logger.warning("No composite scores found")
                    return False
                date = latest_date

            scores = (
                self.db.query(CompositeScore)
                .filter(CompositeScore.date == date)
                .order_by(CompositeScore.composite_score)
                .all()
            )

            if not scores:
                self.logger.warning(f"No scores found for date {date}")
                return False

            # Calculate percentile for each score
            total_count = len(scores)
            for idx, score in enumerate(scores):
                percentile = ((idx + 1) / total_count) * 100
                score.percentile_rank = round(percentile, 2)

            self.db.commit()
            self.logger.info(f"Updated percentile ranks for {total_count} stocks")
            return True

        except Exception as e:
            self.logger.error(f"Error calculating percentile ranks: {e}")
            self.db.rollback()
            return False

    def add_to_watchlist(
        self,
        user_id: str,
        stock_id: int,
        ticker: str,
        score: float,
        reason: Optional[str] = None,
        tags: Optional[str] = None
    ) -> bool:
        """
        Add a stock to the watchlist.

        Args:
            user_id: User identifier
            stock_id: Stock ID
            ticker: Stock ticker
            score: Composite score
            reason: Reason for adding
            tags: Tags (comma-separated)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already in watchlist
            existing = (
                self.db.query(Watchlist)
                .filter(
                    and_(
                        Watchlist.user_id == user_id,
                        Watchlist.stock_id == stock_id,
                        Watchlist.is_active == True
                    )
                )
                .first()
            )

            if existing:
                # Update existing entry
                existing.score = score
                if reason:
                    existing.reason = reason
                if tags:
                    existing.tags = tags
                existing.updated_at = datetime.utcnow()
                self.logger.debug(f"Updated watchlist entry for stock {ticker}")
            else:
                # Create new entry
                watchlist_entry = Watchlist(
                    stock_id=stock_id,
                    user_id=user_id,
                    ticker=ticker,
                    score=score,
                    reason=reason or "Top-scoring stock",
                    tags=tags or "composite-score,auto-added",
                    is_active=True,
                    added_date=datetime.utcnow()
                )
                self.db.add(watchlist_entry)
                self.logger.debug(f"Added stock {ticker} to watchlist")

            self.db.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error adding stock to watchlist: {e}")
            self.db.rollback()
            return False

    def get_watchlist(self, user_id: str, active_only: bool = True) -> List[Tuple[Stock, Watchlist]]:
        """
        Get user's watchlist.

        Args:
            user_id: User identifier
            active_only: Only return active watchlist entries

        Returns:
            List of (Stock, Watchlist) tuples
        """
        try:
            query = (
                self.db.query(Stock, Watchlist)
                .join(Watchlist, Stock.id == Watchlist.stock_id)
                .filter(Watchlist.user_id == user_id)
            )

            if active_only:
                query = query.filter(Watchlist.is_active == True)

            query = query.order_by(desc(Watchlist.score), desc(Watchlist.added_date))

            results = query.all()
            self.logger.info(f"Retrieved {len(results)} watchlist entries for user {user_id}")
            return results

        except Exception as e:
            self.logger.error(f"Error retrieving watchlist: {e}")
            return []
