"""
Stability Calculation Service.

High-level service for calculating and managing stability scores.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging

from services.stability_calculator.stability_calculator import StabilityCalculator, StabilityMetrics
from services.stability_calculator.stability_repository import StabilityDataRepository

logger = logging.getLogger(__name__)


class StabilityService:
    """Service for calculating and managing stock stability scores."""

    def __init__(
        self,
        db_session: Session,
        lookback_days: int = 252,
        min_price_points: int = 30,
        min_earnings_points: int = 4
    ):
        """
        Initialize the stability service.

        Args:
            db_session: SQLAlchemy database session
            lookback_days: Number of days to look back for price data (default: 252 trading days ~ 1 year)
            min_price_points: Minimum number of price points required
            min_earnings_points: Minimum number of earnings points required
        """
        self.db = db_session
        self.repository = StabilityDataRepository(db_session)
        self.calculator = StabilityCalculator(
            lookback_days=lookback_days,
            min_price_points=min_price_points,
            min_earnings_points=min_earnings_points
        )
        self.logger = logging.getLogger(__name__)

    def calculate_stability_for_stock(
        self,
        stock_id: int,
        save_to_db: bool = True,
        weights: Optional[Dict[str, float]] = None
    ) -> Optional[StabilityMetrics]:
        """
        Calculate stability score for a single stock.

        Args:
            stock_id: Stock ID
            save_to_db: Whether to save results to database
            weights: Optional custom weights for score components

        Returns:
            StabilityMetrics object or None if calculation fails
        """
        try:
            # Get stock info
            stock = self.repository.get_stock_by_id(stock_id)
            if not stock:
                self.logger.warning(f"Stock {stock_id} not found")
                return None

            self.logger.info(f"Calculating stability score for {stock.ticker} ({stock.name_kr})")

            # Get all required data
            data = self.repository.get_all_stability_data(
                stock_id=stock_id,
                lookback_days=self.calculator.lookback_days
            )

            # Check if we have sufficient data
            if not data['price_data']:
                self.logger.warning(f"No price data available for stock {stock_id}")
                return None

            # Calculate stability metrics
            metrics = self.calculator.calculate_stability_score(
                price_data=data['price_data'],
                market_data=data['market_data'],
                earnings_data=data['earnings_data'],
                debt_data=data['debt_data'],
                weights=weights
            )

            # Log calculation summary
            self.logger.info(
                f"Stability score for {stock.ticker}: {metrics.stability_score:.2f} "
                f"(Price: {metrics.price_volatility_score or 'N/A'}, "
                f"Beta: {metrics.beta_score or 'N/A'}, "
                f"Volume: {metrics.volume_stability_score or 'N/A'}, "
                f"Earnings: {metrics.earnings_consistency_score or 'N/A'}, "
                f"Debt: {metrics.debt_stability_score or 'N/A'})"
            )

            # Save to database if requested
            if save_to_db:
                success = self.repository.save_stability_score(
                    stock_id=stock_id,
                    metrics=metrics.to_dict()
                )
                if not success:
                    self.logger.error(f"Failed to save stability score for stock {stock_id}")

            return metrics

        except Exception as e:
            self.logger.error(f"Error calculating stability for stock {stock_id}: {e}", exc_info=True)
            return None

    def calculate_stability_for_all_stocks(
        self,
        batch_size: int = 10,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate stability scores for all active stocks.

        Args:
            batch_size: Number of stocks to process before committing
            weights: Optional custom weights for score components

        Returns:
            Dictionary with calculation statistics
        """
        try:
            stocks = self.repository.get_active_stocks()
            total_stocks = len(stocks)

            self.logger.info(f"Starting stability calculation for {total_stocks} stocks")

            stats = {
                'total_stocks': total_stocks,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'errors': []
            }

            for idx, stock in enumerate(stocks, 1):
                try:
                    self.logger.info(f"Processing {idx}/{total_stocks}: {stock.ticker}")

                    metrics = self.calculate_stability_for_stock(
                        stock_id=stock.id,
                        save_to_db=True,
                        weights=weights
                    )

                    if metrics:
                        stats['successful'] += 1
                    else:
                        stats['skipped'] += 1

                    # Commit in batches to avoid long transactions
                    if idx % batch_size == 0:
                        self.db.commit()
                        self.logger.info(f"Committed batch at {idx}/{total_stocks}")

                except Exception as e:
                    self.logger.error(f"Error processing stock {stock.ticker}: {e}")
                    stats['failed'] += 1
                    stats['errors'].append({
                        'stock_id': stock.id,
                        'ticker': stock.ticker,
                        'error': str(e)
                    })
                    self.db.rollback()

            # Final commit
            self.db.commit()

            self.logger.info(
                f"Stability calculation completed: {stats['successful']} successful, "
                f"{stats['failed']} failed, {stats['skipped']} skipped"
            )

            return stats

        except Exception as e:
            self.logger.error(f"Error in batch stability calculation: {e}", exc_info=True)
            self.db.rollback()
            return {
                'total_stocks': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'errors': [str(e)]
            }

    def calculate_stability_for_outdated_stocks(
        self,
        days_threshold: int = 1,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate stability scores for stocks without recent calculations.

        Args:
            days_threshold: Days to consider as outdated
            weights: Optional custom weights for score components

        Returns:
            Dictionary with calculation statistics
        """
        try:
            stocks = self.repository.get_stocks_without_recent_stability_scores(days_threshold)
            total_stocks = len(stocks)

            self.logger.info(
                f"Found {total_stocks} stocks needing stability score update "
                f"(older than {days_threshold} days)"
            )

            stats = {
                'total_stocks': total_stocks,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'errors': []
            }

            for idx, stock in enumerate(stocks, 1):
                try:
                    self.logger.info(f"Processing {idx}/{total_stocks}: {stock.ticker}")

                    metrics = self.calculate_stability_for_stock(
                        stock_id=stock.id,
                        save_to_db=True,
                        weights=weights
                    )

                    if metrics:
                        stats['successful'] += 1
                    else:
                        stats['skipped'] += 1

                except Exception as e:
                    self.logger.error(f"Error processing stock {stock.ticker}: {e}")
                    stats['failed'] += 1
                    stats['errors'].append({
                        'stock_id': stock.id,
                        'ticker': stock.ticker,
                        'error': str(e)
                    })

            self.logger.info(
                f"Outdated stocks calculation completed: {stats['successful']} successful, "
                f"{stats['failed']} failed, {stats['skipped']} skipped"
            )

            return stats

        except Exception as e:
            self.logger.error(f"Error calculating outdated stocks: {e}", exc_info=True)
            return {
                'total_stocks': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'errors': [str(e)]
            }

    def get_top_stable_stocks(
        self,
        limit: int = 50,
        min_score: float = 50.0
    ) -> List[Dict[str, Any]]:
        """
        Get top stable stocks based on stability score.

        Args:
            limit: Maximum number of stocks to return
            min_score: Minimum stability score threshold

        Returns:
            List of stock dictionaries with stability information
        """
        try:
            return self.repository.get_top_stable_stocks(limit=limit, min_score=min_score)
        except Exception as e:
            self.logger.error(f"Error getting top stable stocks: {e}")
            return []

    def get_stock_stability_details(
        self,
        stock_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed stability information for a stock.

        Args:
            stock_id: Stock ID

        Returns:
            Dictionary with detailed stability metrics or None
        """
        try:
            stock = self.repository.get_stock_by_id(stock_id)
            if not stock:
                return None

            stability_score = self.repository.get_latest_stability_score(stock_id)
            if not stability_score:
                return None

            return {
                'stock_id': stock.id,
                'ticker': stock.ticker,
                'name_kr': stock.name_kr,
                'name_en': stock.name_en,
                'market': stock.market,
                'sector': stock.sector,
                'calculation_date': stability_score.date,
                'overall_score': stability_score.stability_score,
                'components': {
                    'price_volatility': {
                        'score': stability_score.price_volatility_score,
                        'volatility': stability_score.price_volatility,
                        'returns_mean': stability_score.returns_mean,
                        'returns_std': stability_score.returns_std,
                        'weight': stability_score.weight_price,
                    },
                    'beta': {
                        'score': stability_score.beta_score,
                        'beta': stability_score.beta,
                        'market_correlation': stability_score.market_correlation,
                        'weight': stability_score.weight_beta,
                    },
                    'volume_stability': {
                        'score': stability_score.volume_stability_score,
                        'coefficient_of_variation': stability_score.volume_stability,
                        'volume_mean': stability_score.volume_mean,
                        'volume_std': stability_score.volume_std,
                        'weight': stability_score.weight_volume,
                    },
                    'earnings_consistency': {
                        'score': stability_score.earnings_consistency_score,
                        'coefficient_of_variation': stability_score.earnings_consistency,
                        'trend': stability_score.earnings_trend,
                        'weight': stability_score.weight_earnings,
                    },
                    'debt_stability': {
                        'score': stability_score.debt_stability_score,
                        'trend': stability_score.debt_trend,
                        'current_debt_ratio': stability_score.debt_ratio_current,
                        'weight': stability_score.weight_debt,
                    },
                },
                'data_quality': {
                    'price_data_points': stability_score.data_points_price,
                    'earnings_data_points': stability_score.data_points_earnings,
                    'debt_data_points': stability_score.data_points_debt,
                    'calculation_period_days': stability_score.calculation_period_days,
                },
            }

        except Exception as e:
            self.logger.error(f"Error getting stability details for stock {stock_id}: {e}")
            return None
