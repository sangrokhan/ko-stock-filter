"""
Main entry point for Stability Calculator service.

This service calculates stability scores for Korean stocks based on:
- Price volatility (standard deviation of returns)
- Beta coefficient (systematic risk vs market)
- Volume stability
- Earnings consistency
- Debt stability trend

Usage:
    python -m services.stability_calculator.main [--all] [--stock TICKER] [--top N]
"""
import sys
import argparse
import logging
from datetime import datetime

from shared.database.connection import get_db_session
from shared.utilities.logger import setup_logger
from services.stability_calculator.stability_service import StabilityService


def main():
    """Main entry point for stability calculator."""
    parser = argparse.ArgumentParser(
        description='Calculate stability scores for Korean stocks'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Calculate stability for all active stocks'
    )
    parser.add_argument(
        '--outdated',
        action='store_true',
        help='Calculate stability for stocks with outdated scores'
    )
    parser.add_argument(
        '--stock',
        type=str,
        help='Calculate stability for a specific stock ticker'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=50,
        help='Show top N most stable stocks (default: 50)'
    )
    parser.add_argument(
        '--min-score',
        type=float,
        default=50.0,
        help='Minimum stability score for top stocks (default: 50.0)'
    )
    parser.add_argument(
        '--lookback-days',
        type=int,
        default=252,
        help='Number of days to look back for price data (default: 252)'
    )
    parser.add_argument(
        '--days-threshold',
        type=int,
        default=1,
        help='Days threshold for outdated scores (default: 1)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logger(
        'stability_calculator',
        log_level=getattr(logging, args.log_level)
    )

    logger.info("=" * 80)
    logger.info("Stability Calculator Service")
    logger.info("=" * 80)
    logger.info(f"Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    try:
        # Get database session
        db_session = get_db_session()

        # Initialize service
        service = StabilityService(
            db_session=db_session,
            lookback_days=args.lookback_days
        )

        # Execute requested operation
        if args.all:
            logger.info("Calculating stability scores for all active stocks...")
            stats = service.calculate_stability_for_all_stocks()
            print_calculation_stats(stats, logger)

        elif args.outdated:
            logger.info(f"Calculating stability scores for outdated stocks (>{args.days_threshold} days)...")
            stats = service.calculate_stability_for_outdated_stocks(
                days_threshold=args.days_threshold
            )
            print_calculation_stats(stats, logger)

        elif args.stock:
            logger.info(f"Calculating stability score for stock: {args.stock}")

            # Find stock by ticker
            from shared.database.models import Stock
            stock = db_session.query(Stock).filter(Stock.ticker == args.stock).first()

            if not stock:
                logger.error(f"Stock {args.stock} not found")
                return 1

            metrics = service.calculate_stability_for_stock(
                stock_id=stock.id,
                save_to_db=True
            )

            if metrics:
                print_stock_stability(stock, metrics, logger)
            else:
                logger.error(f"Failed to calculate stability for {args.stock}")
                return 1

        else:
            # Default: show top stable stocks
            logger.info(f"Retrieving top {args.top} stable stocks (min score: {args.min_score})...")
            top_stocks = service.get_top_stable_stocks(
                limit=args.top,
                min_score=args.min_score
            )
            print_top_stocks(top_stocks, logger)

        logger.info("=" * 80)
        logger.info(f"Completed at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("=" * 80)

        return 0

    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user")
        return 130

    except Exception as e:
        logger.error(f"Error in stability calculator: {e}", exc_info=True)
        return 1

    finally:
        if 'db_session' in locals():
            db_session.close()


def print_calculation_stats(stats: dict, logger: logging.Logger):
    """Print calculation statistics."""
    logger.info("-" * 80)
    logger.info("Calculation Statistics:")
    logger.info(f"  Total stocks:      {stats['total_stocks']}")
    logger.info(f"  Successful:        {stats['successful']}")
    logger.info(f"  Failed:            {stats['failed']}")
    logger.info(f"  Skipped:           {stats['skipped']}")

    if stats.get('errors'):
        logger.warning(f"\nErrors encountered ({len(stats['errors'])}):")
        for error in stats['errors'][:10]:  # Show first 10 errors
            logger.warning(f"  {error['ticker']}: {error['error']}")
        if len(stats['errors']) > 10:
            logger.warning(f"  ... and {len(stats['errors']) - 10} more errors")


def print_stock_stability(stock, metrics, logger: logging.Logger):
    """Print detailed stability information for a stock."""
    logger.info("-" * 80)
    logger.info(f"Stock: {stock.ticker} - {stock.name_kr}")
    logger.info(f"Market: {stock.market} | Sector: {stock.sector}")
    logger.info("-" * 80)
    logger.info(f"Overall Stability Score: {metrics.stability_score:.2f}/100")
    logger.info("")
    logger.info("Component Scores:")

    if metrics.price_volatility_score is not None:
        logger.info(f"  Price Volatility:       {metrics.price_volatility_score:.2f}/100 "
                   f"(Volatility: {metrics.price_volatility:.2%}, Weight: {metrics.weight_price:.1%})")

    if metrics.beta_score is not None:
        logger.info(f"  Beta Coefficient:       {metrics.beta_score:.2f}/100 "
                   f"(Beta: {metrics.beta:.3f}, Weight: {metrics.weight_beta:.1%})")

    if metrics.volume_stability_score is not None:
        logger.info(f"  Volume Stability:       {metrics.volume_stability_score:.2f}/100 "
                   f"(CV: {metrics.volume_stability:.3f}, Weight: {metrics.weight_volume:.1%})")

    if metrics.earnings_consistency_score is not None:
        logger.info(f"  Earnings Consistency:   {metrics.earnings_consistency_score:.2f}/100 "
                   f"(CV: {metrics.earnings_consistency:.3f}, Weight: {metrics.weight_earnings:.1%})")

    if metrics.debt_stability_score is not None:
        logger.info(f"  Debt Stability:         {metrics.debt_stability_score:.2f}/100 "
                   f"(Debt Ratio: {metrics.debt_ratio_current:.1f}%, Weight: {metrics.weight_debt:.1%})")

    logger.info("")
    logger.info("Data Quality:")
    logger.info(f"  Price data points:      {metrics.data_points_price}")
    logger.info(f"  Earnings data points:   {metrics.data_points_earnings}")
    logger.info(f"  Debt data points:       {metrics.data_points_debt}")
    logger.info(f"  Calculation period:     {metrics.calculation_period_days} days")


def print_top_stocks(stocks: list, logger: logging.Logger):
    """Print top stable stocks."""
    logger.info("-" * 80)
    logger.info(f"Top {len(stocks)} Most Stable Stocks")
    logger.info("-" * 80)

    if not stocks:
        logger.info("No stocks found matching criteria")
        return

    # Print header
    header = f"{'Rank':<6} {'Ticker':<10} {'Name':<20} {'Score':<8} {'Price':<8} {'Beta':<8} {'Volume':<8} {'Earnings':<8} {'Debt':<8}"
    logger.info(header)
    logger.info("-" * len(header))

    # Print stocks
    for idx, stock in enumerate(stocks, 1):
        row = (
            f"{idx:<6} "
            f"{stock['ticker']:<10} "
            f"{stock['name_kr'][:18]:<20} "
            f"{stock['stability_score']:>6.2f}  "
            f"{stock.get('price_volatility_score') or 'N/A':>6}  "
            f"{stock.get('beta_score') or 'N/A':>6}  "
            f"{stock.get('volume_stability_score') or 'N/A':>6}  "
            f"{stock.get('earnings_consistency_score') or 'N/A':>6}  "
            f"{stock.get('debt_stability_score') or 'N/A':>6}  "
        )
        logger.info(row)


if __name__ == '__main__':
    sys.exit(main())
