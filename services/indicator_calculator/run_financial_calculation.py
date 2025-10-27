#!/usr/bin/env python3
"""
CLI script for running financial indicator calculations.

Usage:
    python run_financial_calculation.py --all                    # Calculate for all stocks
    python run_financial_calculation.py --missing                # Calculate for stocks without recent data
    python run_financial_calculation.py --tickers 005930 000660  # Calculate for specific tickers
"""
import argparse
import sys
import logging
from datetime import datetime

from shared.database.connection import SessionLocal
from services.indicator_calculator.financial_service import FinancialIndicatorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('financial_calculation.log')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the CLI script."""
    parser = argparse.ArgumentParser(
        description='Calculate financial indicators for Korean stocks'
    )

    # Mutually exclusive group for calculation mode
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--all',
        action='store_true',
        help='Calculate indicators for all active stocks'
    )
    mode_group.add_argument(
        '--missing',
        action='store_true',
        help='Calculate indicators only for stocks without recent data'
    )
    mode_group.add_argument(
        '--tickers',
        nargs='+',
        metavar='TICKER',
        help='Calculate indicators for specific stock tickers (e.g., 005930 000660)'
    )

    # Optional date argument
    parser.add_argument(
        '--date',
        type=str,
        metavar='YYYY-MM-DD',
        help='Calculation date (default: today)'
    )

    args = parser.parse_args()

    # Parse date if provided
    calculation_date = None
    if args.date:
        try:
            calculation_date = datetime.strptime(args.date, '%Y-%m-%d')
            logger.info(f"Using calculation date: {calculation_date.date()}")
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD format.")
            sys.exit(1)

    # Create database session
    db = SessionLocal()

    try:
        # Create service
        service = FinancialIndicatorService(db_session=db)

        # Execute calculation based on mode
        if args.all:
            logger.info("Calculating indicators for all active stocks...")
            stats = service.calculate_indicators_for_all_stocks(
                calculation_date=calculation_date,
                only_missing=False
            )

        elif args.missing:
            logger.info("Calculating indicators for stocks without recent data...")
            stats = service.calculate_indicators_for_all_stocks(
                calculation_date=calculation_date,
                only_missing=True
            )

        elif args.tickers:
            logger.info(f"Calculating indicators for {len(args.tickers)} ticker(s)...")
            stats = service.calculate_indicators_for_tickers(
                tickers=args.tickers,
                calculation_date=calculation_date
            )

        # Print summary
        print("\n" + "="*60)
        print("CALCULATION SUMMARY")
        print("="*60)

        if args.tickers:
            print(f"Total Tickers: {stats['total_stocks']}")
            print(f"Successful: {stats['successful']}")
            print(f"Failed: {stats['failed']}")
            print(f"Not Found: {stats['not_found']}")
            print("\nDetails:")
            for ticker, result in stats.get('results', {}).items():
                print(f"  {ticker}: {result['status']}")
        else:
            print(f"Total Stocks: {stats['total_stocks']}")
            print(f"Successful: {stats['successful']}")
            print(f"Skipped: {stats['skipped']}")
            print(f"Failed: {stats['failed']}")

            if stats.get('failed_stocks'):
                print("\nFailed Stocks:")
                for failed in stats['failed_stocks']:
                    print(f"  {failed['ticker']}: {failed['error']}")

        print("="*60)

        # Exit with appropriate status code
        if stats['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error during calculation: {e}", exc_info=True)
        sys.exit(2)

    finally:
        db.close()


if __name__ == "__main__":
    main()
