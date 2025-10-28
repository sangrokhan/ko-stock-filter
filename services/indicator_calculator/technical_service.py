"""
Technical Indicator Calculation Service.

Orchestrates the calculation and storage of technical indicators for all stocks.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging

from shared.database.connection import SessionLocal
from shared.database.models import Stock
from services.indicator_calculator.technical_calculator import (
    TechnicalIndicatorCalculator,
    TechnicalIndicatorData
)
from services.indicator_calculator.technical_repository import TechnicalDataRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TechnicalIndicatorService:
    """Service for calculating and storing technical indicators."""

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the technical indicator service.

        Args:
            db_session: Optional database session. If not provided, will create one.
        """
        self.db = db_session
        self.calculator = TechnicalIndicatorCalculator()
        self.logger = logging.getLogger(__name__)

    def _get_repository(self) -> TechnicalDataRepository:
        """
        Get repository instance with current session.

        Returns:
            TechnicalDataRepository instance
        """
        return TechnicalDataRepository(self.db)

    def calculate_indicators_for_stock(
        self,
        stock_id: int,
        days_history: int = 250,
        calculation_date: Optional[datetime] = None,
        save_to_db: bool = True
    ) -> Optional[TechnicalIndicatorData]:
        """
        Calculate technical indicators for a single stock.

        Args:
            stock_id: Stock ID
            days_history: Number of days of price history to use (default: 250)
            calculation_date: Date for calculation (default: today)
            save_to_db: Whether to save results to database (default: True)

        Returns:
            TechnicalIndicatorData object or None if calculation failed
        """
        try:
            repository = self._get_repository()

            # Get stock information
            stock = repository.get_stock_by_id(stock_id)
            if not stock:
                self.logger.warning(f"Stock {stock_id} not found")
                return None

            # Check if stock has sufficient price data
            if not repository.has_sufficient_price_data(stock_id, min_days=20):
                self.logger.warning(
                    f"Insufficient price data for stock {stock_id} ({stock.ticker})"
                )
                return None

            # Get price history as DataFrame
            price_df = repository.get_price_history(
                stock_id,
                days=days_history,
                as_of_date=calculation_date
            )

            if price_df.empty:
                self.logger.warning(
                    f"No price data available for stock {stock_id} ({stock.ticker})"
                )
                return None

            # Get the calculation date (latest date in the data)
            if calculation_date is None:
                calculation_date = price_df.index[-1]

            # Calculate all indicators
            indicators = self.calculator.calculate_all_indicators(
                price_df,
                calculation_date
            )

            # Log calculation summary
            self._log_calculation_summary(stock, indicators)

            # Save to database if requested
            if save_to_db:
                indicators_dict = indicators.to_dict()
                success = repository.save_technical_indicators(
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
        only_missing: bool = False,
        days_history: int = 250
    ) -> Dict[str, Any]:
        """
        Calculate technical indicators for all active stocks.

        Args:
            calculation_date: Date for calculation (default: today)
            only_missing: Only calculate for stocks without recent indicators
            days_history: Number of days of price history to use (default: 250)

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
                    'skipped': 0,
                    'errors': []
                }

            self.logger.info(f"Processing {len(stocks)} stocks for technical indicators")

            successful = 0
            failed = 0
            skipped = 0
            errors = []

            for i, stock in enumerate(stocks, 1):
                try:
                    self.logger.info(
                        f"[{i}/{len(stocks)}] Processing {stock.ticker} ({stock.name_kr})"
                    )

                    # Check if stock has sufficient data
                    if not repository.has_sufficient_price_data(stock.id, min_days=20):
                        self.logger.info(
                            f"Skipping {stock.ticker} - insufficient price data"
                        )
                        skipped += 1
                        continue

                    # Calculate indicators
                    result = self.calculate_indicators_for_stock(
                        stock.id,
                        days_history=days_history,
                        calculation_date=calculation_date,
                        save_to_db=True
                    )

                    if result:
                        successful += 1
                    else:
                        failed += 1
                        errors.append({
                            'ticker': stock.ticker,
                            'error': 'Calculation returned None'
                        })

                except Exception as e:
                    failed += 1
                    error_msg = f"Error processing {stock.ticker}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append({
                        'ticker': stock.ticker,
                        'error': str(e)
                    })

            # Summary
            summary = {
                'total_stocks': len(stocks),
                'successful': successful,
                'failed': failed,
                'skipped': skipped,
                'errors': errors[:10]  # Limit to first 10 errors
            }

            self.logger.info(
                f"Technical indicator calculation complete: "
                f"{successful} successful, {failed} failed, {skipped} skipped"
            )

            return summary

        except Exception as e:
            self.logger.error(
                f"Error in batch calculation: {e}",
                exc_info=True
            )
            return {
                'total_stocks': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'errors': [str(e)]
            }

    def calculate_indicators_for_tickers(
        self,
        tickers: List[str],
        calculation_date: Optional[datetime] = None,
        days_history: int = 250
    ) -> Dict[str, Any]:
        """
        Calculate technical indicators for specific stocks by ticker.

        Args:
            tickers: List of stock ticker codes
            calculation_date: Date for calculation (default: today)
            days_history: Number of days of price history to use (default: 250)

        Returns:
            Dictionary with calculation statistics
        """
        try:
            repository = self._get_repository()

            # Get stocks by tickers
            stocks = repository.get_stocks_by_tickers(tickers)

            if not stocks:
                self.logger.warning(f"No stocks found for tickers: {tickers}")
                return {
                    'total_stocks': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0,
                    'errors': []
                }

            self.logger.info(f"Processing {len(stocks)} stocks from ticker list")

            successful = 0
            failed = 0
            skipped = 0
            errors = []

            for stock in stocks:
                try:
                    self.logger.info(f"Processing {stock.ticker} ({stock.name_kr})")

                    # Check if stock has sufficient data
                    if not repository.has_sufficient_price_data(stock.id, min_days=20):
                        self.logger.info(
                            f"Skipping {stock.ticker} - insufficient price data"
                        )
                        skipped += 1
                        continue

                    # Calculate indicators
                    result = self.calculate_indicators_for_stock(
                        stock.id,
                        days_history=days_history,
                        calculation_date=calculation_date,
                        save_to_db=True
                    )

                    if result:
                        successful += 1
                    else:
                        failed += 1
                        errors.append({
                            'ticker': stock.ticker,
                            'error': 'Calculation returned None'
                        })

                except Exception as e:
                    failed += 1
                    error_msg = f"Error processing {stock.ticker}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append({
                        'ticker': stock.ticker,
                        'error': str(e)
                    })

            # Summary
            summary = {
                'total_stocks': len(stocks),
                'successful': successful,
                'failed': failed,
                'skipped': skipped,
                'errors': errors
            }

            self.logger.info(
                f"Technical indicator calculation complete: "
                f"{successful} successful, {failed} failed, {skipped} skipped"
            )

            return summary

        except Exception as e:
            self.logger.error(
                f"Error in ticker-based calculation: {e}",
                exc_info=True
            )
            return {
                'total_stocks': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'errors': [str(e)]
            }

    def _log_calculation_summary(
        self,
        stock: Stock,
        indicators: TechnicalIndicatorData
    ) -> None:
        """
        Log a summary of calculated indicators.

        Args:
            stock: Stock object
            indicators: Calculated indicators
        """
        summary_parts = [
            f"Technical indicators for {stock.ticker} ({stock.name_kr}):"
        ]

        # Moving Averages
        if indicators.sma_20 is not None:
            summary_parts.append(f"SMA20={indicators.sma_20:.2f}")
        if indicators.sma_60 is not None:
            summary_parts.append(f"SMA60={indicators.sma_60:.2f}")
        if indicators.sma_120 is not None:
            summary_parts.append(f"SMA120={indicators.sma_120:.2f}")

        # RSI
        if indicators.rsi_14 is not None:
            summary_parts.append(f"RSI={indicators.rsi_14:.2f}")

        # MACD
        if indicators.macd is not None:
            summary_parts.append(f"MACD={indicators.macd:.2f}")

        # Bollinger Bands
        if indicators.bollinger_upper is not None:
            summary_parts.append(
                f"BB=[{indicators.bollinger_lower:.2f}, "
                f"{indicators.bollinger_middle:.2f}, "
                f"{indicators.bollinger_upper:.2f}]"
            )

        self.logger.info(" ".join(summary_parts))


def main():
    """Main function for running technical indicator calculations."""
    import sys
    from shared.database.connection import get_db_session

    # Parse command line arguments
    mode = 'all'  # default mode
    tickers = []

    if len(sys.argv) > 1:
        if sys.argv[1] == '--missing':
            mode = 'missing'
        elif sys.argv[1] == '--tickers':
            mode = 'tickers'
            tickers = sys.argv[2:] if len(sys.argv) > 2 else []

    logger.info(f"Starting technical indicator calculation in '{mode}' mode")

    # Create service with database session
    with get_db_session() as db:
        service = TechnicalIndicatorService(db_session=db)

        if mode == 'tickers' and tickers:
            summary = service.calculate_indicators_for_tickers(tickers)
        elif mode == 'missing':
            summary = service.calculate_indicators_for_all_stocks(only_missing=True)
        else:
            summary = service.calculate_indicators_for_all_stocks(only_missing=False)

        # Print summary
        print("\n" + "="*60)
        print("TECHNICAL INDICATOR CALCULATION SUMMARY")
        print("="*60)
        print(f"Total stocks: {summary['total_stocks']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Skipped: {summary['skipped']}")

        if summary['errors']:
            print(f"\nErrors ({len(summary['errors'])} shown):")
            for error in summary['errors']:
                print(f"  - {error['ticker']}: {error['error']}")

        print("="*60)


if __name__ == "__main__":
    main()
