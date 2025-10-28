"""
Score Service.

Orchestrates the composite score calculation process for stocks.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
import logging

from services.stock_scorer.stock_scorer import StockScorer, ScoreMetrics
from services.stock_scorer.score_repository import ScoreDataRepository
from shared.database.models import Stock, CompositeScore

logger = logging.getLogger(__name__)


class ScoreService:
    """Service for calculating and managing composite scores."""

    def __init__(
        self,
        db_session: Session,
        weight_value: float = 0.25,
        weight_growth: float = 0.25,
        weight_quality: float = 0.25,
        weight_momentum: float = 0.25
    ):
        """
        Initialize the score service.

        Args:
            db_session: SQLAlchemy database session
            weight_value: Weight for value score
            weight_growth: Weight for growth score
            weight_quality: Weight for quality score
            weight_momentum: Weight for momentum score
        """
        self.db = db_session
        self.repository = ScoreDataRepository(db_session)
        self.scorer = StockScorer(
            weight_value=weight_value,
            weight_growth=weight_growth,
            weight_quality=weight_quality,
            weight_momentum=weight_momentum
        )
        self.logger = logging.getLogger(__name__)

    def calculate_score_for_stock(self, stock_id: int) -> Optional[ScoreMetrics]:
        """
        Calculate composite score for a single stock.

        Args:
            stock_id: Stock ID

        Returns:
            ScoreMetrics object or None if calculation fails
        """
        try:
            # Get stock info
            stock = self.repository.get_stock_by_id(stock_id)
            if not stock:
                self.logger.warning(f"Stock {stock_id} not found")
                return None

            # Get fundamental data
            fundamental_data = self.repository.get_latest_fundamental_data(stock_id)
            if not fundamental_data:
                self.logger.warning(f"No fundamental data for stock {stock.ticker}")
                return None

            # Get technical data
            technical_data = self.repository.get_latest_technical_data(stock_id)
            if not technical_data:
                self.logger.warning(f"No technical data for stock {stock.ticker}")
                # We can still calculate with just fundamental data
                technical_data = {}

            # Get price history
            price_data = self.repository.get_price_history(stock_id, lookback_days=60)
            if not price_data or len(price_data) < 20:
                self.logger.warning(f"Insufficient price history for stock {stock.ticker}")
                # We can still calculate with available data
                price_data = []

            # Calculate score
            self.logger.info(f"Calculating score for {stock.ticker}")
            metrics = self.scorer.calculate_score(
                fundamental_data=fundamental_data,
                technical_data=technical_data,
                price_data=price_data
            )

            # Save to database
            score_dict = metrics.to_dict()
            success = self.repository.save_composite_score(stock_id, score_dict)

            if success:
                self.logger.info(
                    f"Saved score for {stock.ticker}: "
                    f"Composite={metrics.composite_score:.1f}, "
                    f"Value={metrics.value_score:.1f}, "
                    f"Growth={metrics.growth_score:.1f}, "
                    f"Quality={metrics.quality_score:.1f}, "
                    f"Momentum={metrics.momentum_score:.1f}"
                )
                return metrics
            else:
                self.logger.error(f"Failed to save score for {stock.ticker}")
                return metrics  # Return metrics even if save failed

        except Exception as e:
            self.logger.error(f"Error calculating score for stock {stock_id}: {e}", exc_info=True)
            return None

    def calculate_scores_for_all_stocks(
        self,
        limit: Optional[int] = None,
        update_percentiles: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate composite scores for all active stocks.

        Args:
            limit: Optional limit on number of stocks to process
            update_percentiles: Whether to update percentile ranks after calculation

        Returns:
            Dictionary with summary statistics
        """
        try:
            # Get active stocks
            stocks = self.repository.get_active_stocks(limit=limit)
            self.logger.info(f"Calculating scores for {len(stocks)} stocks")

            results = {
                'total_stocks': len(stocks),
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'scores': [],
                'errors': []
            }

            for stock in stocks:
                try:
                    metrics = self.calculate_score_for_stock(stock.id)
                    if metrics:
                        results['successful'] += 1
                        results['scores'].append({
                            'stock_id': stock.id,
                            'ticker': stock.ticker,
                            'name': stock.name_kr,
                            'composite_score': metrics.composite_score,
                            'value_score': metrics.value_score,
                            'growth_score': metrics.growth_score,
                            'quality_score': metrics.quality_score,
                            'momentum_score': metrics.momentum_score,
                        })
                    else:
                        results['skipped'] += 1
                except Exception as e:
                    self.logger.error(f"Error processing stock {stock.ticker}: {e}")
                    results['failed'] += 1
                    results['errors'].append({
                        'stock_id': stock.id,
                        'ticker': stock.ticker,
                        'error': str(e)
                    })

            # Update percentile ranks
            if update_percentiles and results['successful'] > 0:
                self.logger.info("Updating percentile ranks")
                self.repository.calculate_percentile_ranks()

            self.logger.info(
                f"Score calculation complete: "
                f"{results['successful']} successful, "
                f"{results['failed']} failed, "
                f"{results['skipped']} skipped"
            )

            return results

        except Exception as e:
            self.logger.error(f"Error in batch score calculation: {e}", exc_info=True)
            return {
                'error': str(e),
                'total_stocks': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0
            }

    def get_top_stocks(
        self,
        limit: int = 50,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top-scoring stocks.

        Args:
            limit: Maximum number of stocks to return
            min_score: Minimum composite score threshold

        Returns:
            List of dictionaries with stock and score information
        """
        try:
            results = self.repository.get_top_scored_stocks(
                limit=limit,
                min_score=min_score
            )

            top_stocks = []
            for stock, score in results:
                top_stocks.append({
                    'stock_id': stock.id,
                    'ticker': stock.ticker,
                    'name_kr': stock.name_kr,
                    'name_en': stock.name_en,
                    'market': stock.market,
                    'sector': stock.sector,
                    'industry': stock.industry,
                    'composite_score': score.composite_score,
                    'percentile_rank': score.percentile_rank,
                    'value_score': score.value_score,
                    'growth_score': score.growth_score,
                    'quality_score': score.quality_score,
                    'momentum_score': score.momentum_score,
                    'data_quality_score': score.data_quality_score,
                    'date': score.date,
                })

            self.logger.info(f"Retrieved {len(top_stocks)} top-scoring stocks")
            return top_stocks

        except Exception as e:
            self.logger.error(f"Error retrieving top stocks: {e}")
            return []

    def add_top_stocks_to_watchlist(
        self,
        user_id: str,
        limit: int = 50,
        min_score: Optional[float] = 60.0,
        tags: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add top-scoring stocks to watchlist.

        Args:
            user_id: User identifier
            limit: Maximum number of stocks to add
            min_score: Minimum composite score threshold
            tags: Optional tags (comma-separated)

        Returns:
            Dictionary with summary statistics
        """
        try:
            # Get top stocks
            top_stocks = self.get_top_stocks(limit=limit, min_score=min_score)

            if not top_stocks:
                self.logger.warning("No top stocks found to add to watchlist")
                return {
                    'total': 0,
                    'added': 0,
                    'failed': 0,
                    'stocks': []
                }

            results = {
                'total': len(top_stocks),
                'added': 0,
                'failed': 0,
                'stocks': []
            }

            default_tags = tags or "top-scored,auto-added"

            for stock_data in top_stocks:
                try:
                    reason = (
                        f"Top {limit} stock by composite score "
                        f"(Score: {stock_data['composite_score']:.1f}, "
                        f"Percentile: {stock_data['percentile_rank']:.0f}%)"
                    )

                    success = self.repository.add_to_watchlist(
                        user_id=user_id,
                        stock_id=stock_data['stock_id'],
                        ticker=stock_data['ticker'],
                        score=stock_data['composite_score'],
                        reason=reason,
                        tags=default_tags
                    )

                    if success:
                        results['added'] += 1
                        results['stocks'].append({
                            'ticker': stock_data['ticker'],
                            'name': stock_data['name_kr'],
                            'score': stock_data['composite_score'],
                            'percentile': stock_data['percentile_rank']
                        })
                    else:
                        results['failed'] += 1

                except Exception as e:
                    self.logger.error(f"Error adding {stock_data['ticker']} to watchlist: {e}")
                    results['failed'] += 1

            self.logger.info(
                f"Added {results['added']} stocks to watchlist for user {user_id}"
            )

            return results

        except Exception as e:
            self.logger.error(f"Error adding top stocks to watchlist: {e}", exc_info=True)
            return {
                'error': str(e),
                'total': 0,
                'added': 0,
                'failed': 0
            }

    def get_stock_score_breakdown(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed score breakdown for a stock.

        Args:
            stock_id: Stock ID

        Returns:
            Dictionary with detailed score breakdown or None
        """
        try:
            stock = self.repository.get_stock_by_id(stock_id)
            if not stock:
                return None

            score = self.repository.get_latest_composite_score(stock_id)
            if not score:
                return None

            return {
                'stock': {
                    'id': stock.id,
                    'ticker': stock.ticker,
                    'name_kr': stock.name_kr,
                    'market': stock.market,
                    'sector': stock.sector,
                    'industry': stock.industry,
                },
                'composite_score': score.composite_score,
                'percentile_rank': score.percentile_rank,
                'date': score.date,
                'components': {
                    'value': {
                        'score': score.value_score,
                        'weight': score.weight_value,
                        'per_score': score.per_score,
                        'pbr_score': score.pbr_score,
                        'psr_score': score.psr_score,
                        'dividend_yield_score': score.dividend_yield_score,
                    },
                    'growth': {
                        'score': score.growth_score,
                        'weight': score.weight_growth,
                        'revenue_growth_score': score.revenue_growth_score,
                        'earnings_growth_score': score.earnings_growth_score,
                        'equity_growth_score': score.equity_growth_score,
                    },
                    'quality': {
                        'score': score.quality_score,
                        'weight': score.weight_quality,
                        'roe_score': score.roe_score,
                        'operating_margin_score': score.operating_margin_score,
                        'net_margin_score': score.net_margin_score,
                        'debt_ratio_score': score.debt_ratio_score,
                        'current_ratio_score': score.current_ratio_score,
                    },
                    'momentum': {
                        'score': score.momentum_score,
                        'weight': score.weight_momentum,
                        'rsi_score': score.rsi_score,
                        'macd_score': score.macd_score,
                        'price_trend_score': score.price_trend_score,
                        'volume_trend_score': score.volume_trend_score,
                    }
                },
                'data_quality': {
                    'score': score.data_quality_score,
                    'missing_count': score.missing_value_count,
                    'total_count': score.total_metric_count,
                },
                'notes': score.notes,
            }

        except Exception as e:
            self.logger.error(f"Error getting score breakdown for stock {stock_id}: {e}")
            return None
