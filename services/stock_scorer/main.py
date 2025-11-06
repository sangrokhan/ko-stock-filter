"""
Stock Scorer Service - Main Entry Point.

Provides functionality to:
- Calculate composite scores for all stocks
- Get top-scoring stocks
- Add top stocks to watchlist
- Get detailed score breakdowns
"""
import argparse
import logging
import sys
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.stock_scorer.score_service import ScoreService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('stock_scorer.log')
    ]
)

logger = logging.getLogger(__name__)


def get_db_session():
    """Create and return a database session."""
    from shared.configs.config import settings
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def calculate_all_scores(limit: int = None):
    """Calculate scores for all stocks."""
    logger.info("Starting score calculation for all stocks")
    db = get_db_session()

    try:
        service = ScoreService(db)
        results = service.calculate_scores_for_all_stocks(limit=limit, update_percentiles=True)

        logger.info("\n=== Score Calculation Results ===")
        logger.info(f"Total stocks: {results['total_stocks']}")
        logger.info(f"Successful: {results['successful']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info(f"Skipped: {results['skipped']}")

        if results.get('errors'):
            logger.error("\nErrors encountered:")
            for error in results['errors'][:10]:  # Show first 10 errors
                logger.error(f"  {error['ticker']}: {error['error']}")

        return results

    except Exception as e:
        logger.error(f"Error in score calculation: {e}", exc_info=True)
        return None
    finally:
        db.close()


def show_top_stocks(limit: int = 50, min_score: float = None):
    """Display top-scoring stocks."""
    logger.info(f"Getting top {limit} stocks")
    db = get_db_session()

    try:
        service = ScoreService(db)
        top_stocks = service.get_top_stocks(limit=limit, min_score=min_score)

        if not top_stocks:
            logger.warning("No stocks found")
            return

        logger.info(f"\n=== Top {len(top_stocks)} Stocks by Composite Score ===\n")
        logger.info(f"{'Rank':<5} {'Ticker':<8} {'Name':<30} {'Score':<8} {'Value':<7} {'Growth':<7} {'Quality':<7} {'Momentum':<7} {'Percentile':<10}")
        logger.info("=" * 110)

        for idx, stock in enumerate(top_stocks, 1):
            logger.info(
                f"{idx:<5} "
                f"{stock['ticker']:<8} "
                f"{stock['name_kr'][:28]:<30} "
                f"{stock['composite_score']:>6.1f}  "
                f"{stock['value_score']:>6.1f} "
                f"{stock['growth_score']:>6.1f} "
                f"{stock['quality_score']:>6.1f} "
                f"{stock['momentum_score']:>6.1f}  "
                f"{stock['percentile_rank']:>6.1f}%"
            )

        return top_stocks

    except Exception as e:
        logger.error(f"Error getting top stocks: {e}", exc_info=True)
        return None
    finally:
        db.close()


def add_to_watchlist(user_id: str, limit: int = 50, min_score: float = 60.0):
    """Add top-scoring stocks to watchlist."""
    logger.info(f"Adding top {limit} stocks to watchlist for user {user_id}")
    db = get_db_session()

    try:
        service = ScoreService(db)
        results = service.add_top_stocks_to_watchlist(
            user_id=user_id,
            limit=limit,
            min_score=min_score,
            tags="top-scored,auto-added"
        )

        logger.info("\n=== Watchlist Update Results ===")
        logger.info(f"Total stocks processed: {results['total']}")
        logger.info(f"Successfully added: {results['added']}")
        logger.info(f"Failed: {results['failed']}")

        if results.get('stocks'):
            logger.info("\nAdded stocks:")
            for stock in results['stocks']:
                logger.info(
                    f"  {stock['ticker']}: {stock['name']} "
                    f"(Score: {stock['score']:.1f}, Percentile: {stock['percentile']:.0f}%)"
                )

        return results

    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}", exc_info=True)
        return None
    finally:
        db.close()


def show_stock_breakdown(ticker: str):
    """Show detailed score breakdown for a specific stock."""
    logger.info(f"Getting score breakdown for {ticker}")
    db = get_db_session()

    try:
        service = ScoreService(db)

        # Get stock by ticker
        stock = service.repository.get_stock_by_ticker(ticker)
        if not stock:
            logger.error(f"Stock {ticker} not found")
            return None

        breakdown = service.get_stock_score_breakdown(stock.id)
        if not breakdown:
            logger.error(f"No score data found for {ticker}")
            return None

        logger.info(f"\n=== Score Breakdown for {ticker} ===")
        logger.info(f"Name: {breakdown['stock']['name_kr']}")
        logger.info(f"Market: {breakdown['stock']['market']}")
        logger.info(f"Sector: {breakdown['stock']['sector']}")
        logger.info(f"Industry: {breakdown['stock']['industry']}")
        logger.info(f"\nComposite Score: {breakdown['composite_score']:.1f}")
        logger.info(f"Percentile Rank: {breakdown['percentile_rank']:.1f}%")
        logger.info(f"Date: {breakdown['date']}")

        logger.info("\n--- Component Scores ---")
        for component_name, component_data in breakdown['components'].items():
            score = component_data['score']
            weight = component_data['weight']
            logger.info(f"\n{component_name.capitalize()} Score: {score:.1f} (weight: {weight:.0%})")
            for metric, value in component_data.items():
                if metric not in ['score', 'weight'] and value is not None:
                    logger.info(f"  {metric}: {value:.1f}")

        logger.info(f"\n--- Data Quality ---")
        logger.info(f"Data Quality Score: {breakdown['data_quality']['score']:.1f}%")
        logger.info(f"Missing Metrics: {breakdown['data_quality']['missing_count']}/{breakdown['data_quality']['total_count']}")

        if breakdown.get('notes'):
            logger.info(f"\nNotes: {breakdown['notes']}")

        return breakdown

    except Exception as e:
        logger.error(f"Error getting breakdown: {e}", exc_info=True)
        return None
    finally:
        db.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Stock Scorer Service')
    parser.add_argument('command', choices=['calculate', 'top', 'watchlist', 'breakdown'],
                       help='Command to execute')
    parser.add_argument('--limit', type=int, default=50,
                       help='Number of stocks to process/display')
    parser.add_argument('--min-score', type=float,
                       help='Minimum score threshold')
    parser.add_argument('--user-id', default='default',
                       help='User ID for watchlist operations')
    parser.add_argument('--ticker', help='Stock ticker for breakdown')

    args = parser.parse_args()

    try:
        if args.command == 'calculate':
            calculate_all_scores(limit=args.limit)

        elif args.command == 'top':
            show_top_stocks(limit=args.limit, min_score=args.min_score)

        elif args.command == 'watchlist':
            add_to_watchlist(
                user_id=args.user_id,
                limit=args.limit,
                min_score=args.min_score or 60.0
            )

        elif args.command == 'breakdown':
            if not args.ticker:
                logger.error("--ticker is required for breakdown command")
                sys.exit(1)
            show_stock_breakdown(args.ticker)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
