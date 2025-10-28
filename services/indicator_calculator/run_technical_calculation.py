#!/usr/bin/env python3
"""
CLI tool for running technical indicator calculations.

Usage:
    python run_technical_calculation.py --all              # Calculate for all stocks
    python run_technical_calculation.py --missing          # Calculate only for stocks with missing indicators
    python run_technical_calculation.py --tickers 005930 000660  # Calculate for specific tickers
    python run_technical_calculation.py --help             # Show help
"""
import sys
import os
import argparse
import logging
from datetime import datetime

# Add parent directory to path to import shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.database.connection import get_db_session
from services.indicator_calculator.technical_service import TechnicalIndicatorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('technical_calculation.log')
    ]
)

logger = logging.getLogger(__name__)


def print_banner():
    """Print application banner."""
    print("\n" + "="*70)
    print(" " * 15 + "TECHNICAL INDICATOR CALCULATOR")
    print(" " * 20 + "Korean Stock Trading System")
    print("="*70 + "\n")


def print_summary(summary: dict):
    """
    Print calculation summary.

    Args:
        summary: Summary dictionary from service
    """
    print("\n" + "="*70)
    print(" " * 20 + "CALCULATION SUMMARY")
    print("="*70)
    print(f"Total stocks processed:  {summary['total_stocks']}")
    print(f"Successful:              {summary['successful']} ✓")
    print(f"Failed:                  {summary['failed']} ✗")
    print(f"Skipped:                 {summary['skipped']} -")
    print(f"Success rate:            {summary['successful']/max(summary['total_stocks'], 1)*100:.1f}%")

    if summary['errors']:
        print(f"\nErrors ({min(len(summary['errors']), 10)} of {len(summary['errors'])} shown):")
        for i, error in enumerate(summary['errors'][:10], 1):
            print(f"  {i}. {error['ticker']}: {error['error']}")

    print("="*70 + "\n")


def run_all_stocks(service: TechnicalIndicatorService):
    """
    Calculate indicators for all active stocks.

    Args:
        service: TechnicalIndicatorService instance
    """
    logger.info("Starting calculation for ALL active stocks")
    print("Calculating technical indicators for all active stocks...")
    print("This may take several minutes...\n")

    start_time = datetime.now()
    summary = service.calculate_indicators_for_all_stocks(only_missing=False)
    end_time = datetime.now()

    duration = (end_time - start_time).total_seconds()
    print(f"\nCalculation completed in {duration:.1f} seconds")

    print_summary(summary)


def run_missing_stocks(service: TechnicalIndicatorService):
    """
    Calculate indicators only for stocks with missing indicators.

    Args:
        service: TechnicalIndicatorService instance
    """
    logger.info("Starting calculation for stocks with MISSING indicators")
    print("Calculating technical indicators for stocks with missing data...")
    print("This will only process stocks without recent indicators.\n")

    start_time = datetime.now()
    summary = service.calculate_indicators_for_all_stocks(only_missing=True)
    end_time = datetime.now()

    duration = (end_time - start_time).total_seconds()
    print(f"\nCalculation completed in {duration:.1f} seconds")

    print_summary(summary)


def run_specific_tickers(service: TechnicalIndicatorService, tickers: list):
    """
    Calculate indicators for specific ticker codes.

    Args:
        service: TechnicalIndicatorService instance
        tickers: List of ticker codes
    """
    logger.info(f"Starting calculation for SPECIFIC tickers: {', '.join(tickers)}")
    print(f"Calculating technical indicators for {len(tickers)} specific stocks...")
    print(f"Tickers: {', '.join(tickers)}\n")

    start_time = datetime.now()
    summary = service.calculate_indicators_for_tickers(tickers)
    end_time = datetime.now()

    duration = (end_time - start_time).total_seconds()
    print(f"\nCalculation completed in {duration:.1f} seconds")

    print_summary(summary)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Calculate technical indicators for Korean stocks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                    Calculate for all active stocks
  %(prog)s --missing                Calculate only for stocks with missing indicators
  %(prog)s --tickers 005930         Calculate for Samsung Electronics (005930)
  %(prog)s --tickers 005930 000660  Calculate for Samsung and SK Hynix

Technical Indicators Calculated:
  - Moving Averages: SMA (5, 20, 50, 120, 200), EMA (12, 26)
  - Momentum: RSI (9, 14), Stochastic Oscillator
  - Trend: MACD, ADX
  - Volatility: Bollinger Bands, ATR
  - Volume: OBV, Volume MA(20)
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--all',
        action='store_true',
        help='Calculate indicators for all active stocks'
    )
    group.add_argument(
        '--missing',
        action='store_true',
        help='Calculate indicators only for stocks with missing data'
    )
    group.add_argument(
        '--tickers',
        nargs='+',
        metavar='TICKER',
        help='Calculate indicators for specific ticker codes (e.g., 005930 000660)'
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    # Log start
    logger.info("="*70)
    logger.info("Technical Indicator Calculation Started")
    logger.info(f"Mode: {('all' if args.all else 'missing' if args.missing else 'tickers')}")
    if args.tickers:
        logger.info(f"Tickers: {', '.join(args.tickers)}")
    logger.info("="*70)

    try:
        # Create service with database session
        with get_db_session() as db:
            service = TechnicalIndicatorService(db_session=db)

            if args.all:
                run_all_stocks(service)
            elif args.missing:
                run_missing_stocks(service)
            elif args.tickers:
                run_specific_tickers(service, args.tickers)

        logger.info("Technical indicator calculation completed successfully")
        return 0

    except KeyboardInterrupt:
        print("\n\nCalculation interrupted by user")
        logger.warning("Calculation interrupted by user")
        return 130

    except Exception as e:
        print(f"\n\nERROR: {str(e)}")
        logger.error(f"Calculation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
