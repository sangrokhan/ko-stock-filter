"""
Financial Indicator Calculation Service.

Orchestrates the calculation and storage of financial indicators for all stocks.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging

from shared.database.connection import SessionLocal
from shared.database.models import Stock
from services.indicator_calculator.financial_calculator import (
    FinancialCalculator,
    FinancialIndicator
)
from services.indicator_calculator.financial_repository import FinancialDataRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialIndicatorService:
    """Service for calculating and storing financial indicators."""

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the financial indicator service.

        Args:
            db_session: Optional database session. If not provided, will create one.
        """
        self.db = db_session
        self.calculator = FinancialCalculator()
        self.logger = logging.getLogger(__name__)

    def _get_repository(self) -> FinancialDataRepository:
        """
        Get repository instance with current session.

        Returns:
            FinancialDataRepository instance
        """
        return FinancialDataRepository(self.db)

    def calculate_indicators_for_stock(
        self,
        stock_id: int,
        calculation_date: Optional[datetime] = None,
        save_to_db: bool = True
    ) -> Optional[FinancialIndicator]:
        """
        Calculate financial indicators for a single stock.

        Args:
            stock_id: Stock ID
            calculation_date: Date for calculation (default: today)
            save_to_db: Whether to save results to database (default: True)

        Returns:
            FinancialIndicator object or None if calculation failed
        """
        try:
            repository = self._get_repository()

            # Get stock information
            stock = repository.get_stock_by_id(stock_id)
            if not stock:
                self.logger.warning(f"Stock {stock_id} not found")
                return None

            # Get current financial data
            current_data = repository.get_current_financial_data(
                stock_id, stock, calculation_date
            )
            if not current_data:
                self.logger.warning(
                    f"Insufficient current data for stock {stock_id} ({stock.ticker})"
                )
                return None

            # Get previous period data for growth calculations
            previous_data = repository.get_previous_period_data(
                stock_id,
                calculation_date or datetime.utcnow()
            )
            if not previous_data:
                self.logger.info(
                    f"No previous period data for stock {stock_id} ({stock.ticker}), "
                    "growth metrics will not be calculated"
                )

            # Calculate all indicators
            indicators = self.calculator.calculate_all_indicators(
                current_data, previous_data
            )

            # Log calculation summary
            self._log_calculation_summary(stock, indicators)

            # Save to database if requested
            if save_to_db:
                indicators_dict = indicators.to_dict()
                success = repository.save_fundamental_indicators(
                    stock_id, indicators_dict, calculation_date
                )
                if not success:
                    self.logger.error(
                        f"Failed to save indicators for stock {stock_id} ({stock.ticker})"
                    )
                    return None

            return indicators

        except Exception as e:
            self.logger.error(
                f"Error calculating indicators for stock {stock_id}: {e}",
                exc_info=True
            )
            return None

    def calculate_indicators_for_all_stocks(
        self,
        calculation_date: Optional[datetime] = None,
        only_missing: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate financial indicators for all active stocks.

        Args:
            calculation_date: Date for calculation (default: today)
            only_missing: Only calculate for stocks without recent indicators

        Returns:
            Dictionary with calculation statistics
        """
        try:
            repository = self._get_repository()

            # Get stocks to process
            if only_missing:
                stocks = repository.get_stocks_without_recent_indicators(days_threshold=1)
            else:
                stocks = repository.get_active_stocks()

            if not stocks:
                self.logger.info("No stocks to process")
                return {
                    'total_stocks': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0
                }

            self.logger.info(f"Processing {len(stocks)} stocks")

            stats = {
                'total_stocks': len(stocks),
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'failed_stocks': []
            }

            for stock in stocks:
                try:
                    indicators = self.calculate_indicators_for_stock(
                        stock.id,
                        calculation_date=calculation_date,
                        save_to_db=True
                    )

                    if indicators:
                        stats['successful'] += 1
                    else:
                        stats['skipped'] += 1
                        self.logger.debug(f"Skipped stock {stock.ticker} due to insufficient data")

                except Exception as e:
                    stats['failed'] += 1
                    stats['failed_stocks'].append({
                        'ticker': stock.ticker,
                        'error': str(e)
                    })
                    self.logger.error(
                        f"Error processing stock {stock.ticker}: {e}",
                        exc_info=True
                    )

            # Log summary
            self.logger.info(
                f"Calculation complete - "
                f"Total: {stats['total_stocks']}, "
                f"Successful: {stats['successful']}, "
                f"Skipped: {stats['skipped']}, "
                f"Failed: {stats['failed']}"
            )

            return stats

        except Exception as e:
            self.logger.error(f"Error in batch calculation: {e}", exc_info=True)
            raise

    def calculate_indicators_for_tickers(
        self,
        tickers: List[str],
        calculation_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate financial indicators for specific tickers.

        Args:
            tickers: List of stock tickers
            calculation_date: Date for calculation (default: today)

        Returns:
            Dictionary with calculation statistics
        """
        try:
            repository = self._get_repository()

            stats = {
                'total_stocks': len(tickers),
                'successful': 0,
                'failed': 0,
                'not_found': 0,
                'results': {}
            }

            for ticker in tickers:
                try:
                    # Find stock by ticker
                    stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
                    if not stock:
                        stats['not_found'] += 1
                        self.logger.warning(f"Stock with ticker {ticker} not found")
                        stats['results'][ticker] = {'status': 'not_found'}
                        continue

                    # Calculate indicators
                    indicators = self.calculate_indicators_for_stock(
                        stock.id,
                        calculation_date=calculation_date,
                        save_to_db=True
                    )

                    if indicators:
                        stats['successful'] += 1
                        stats['results'][ticker] = {
                            'status': 'success',
                            'indicators': indicators.to_dict()
                        }
                    else:
                        stats['failed'] += 1
                        stats['results'][ticker] = {
                            'status': 'failed',
                            'reason': 'insufficient_data'
                        }

                except Exception as e:
                    stats['failed'] += 1
                    stats['results'][ticker] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    self.logger.error(f"Error processing ticker {ticker}: {e}")

            return stats

        except Exception as e:
            self.logger.error(f"Error in ticker-based calculation: {e}", exc_info=True)
            raise

    def _log_calculation_summary(self, stock, indicators: FinancialIndicator):
        """
        Log a summary of calculated indicators.

        Args:
            stock: Stock object
            indicators: FinancialIndicator object
        """
        metrics = []
        if indicators.per is not None:
            metrics.append(f"PER={indicators.per:.2f}")
        if indicators.pbr is not None:
            metrics.append(f"PBR={indicators.pbr:.2f}")
        if indicators.roe is not None:
            metrics.append(f"ROE={indicators.roe:.2f}%")
        if indicators.debt_ratio is not None:
            metrics.append(f"Debt={indicators.debt_ratio:.2f}%")
        if indicators.operating_margin is not None:
            metrics.append(f"OpMargin={indicators.operating_margin:.2f}%")
        if indicators.revenue_growth is not None:
            metrics.append(f"RevGrowth={indicators.revenue_growth:.2f}%")
        if indicators.eps_growth is not None:
            metrics.append(f"EPSGrowth={indicators.eps_growth:.2f}%")

        if metrics:
            self.logger.info(
                f"Stock {stock.ticker} ({stock.name_kr}): {', '.join(metrics)}"
            )
        else:
            self.logger.warning(f"Stock {stock.ticker} ({stock.name_kr}): No metrics calculated")


def run_daily_calculation():
    """
    Run daily financial indicator calculation for all stocks.
    This function can be called by a scheduler.
    """
    logger.info("Starting daily financial indicator calculation")

    db = SessionLocal()
    try:
        service = FinancialIndicatorService(db_session=db)
        stats = service.calculate_indicators_for_all_stocks(only_missing=False)

        logger.info(f"Daily calculation completed: {stats}")

        # Log any failures
        if stats.get('failed_stocks'):
            logger.warning(f"Failed stocks: {stats['failed_stocks']}")

        return stats

    except Exception as e:
        logger.error(f"Error in daily calculation: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Run calculation when script is executed directly
    run_daily_calculation()
