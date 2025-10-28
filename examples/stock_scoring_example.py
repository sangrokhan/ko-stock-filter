"""
Stock Scoring System Example.

This example demonstrates how to:
1. Calculate composite scores for stocks
2. Rank stocks by composite score
3. Add top-scoring stocks to a watchlist
4. Get detailed score breakdowns

Usage:
    python examples/stock_scoring_example.py
"""
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.config.settings import Settings
from services.stock_scorer import ScoreService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def get_db_session():
    """Create and return a database session."""
    settings = Settings()
    engine = create_engine(settings.get_database_url())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def example_1_calculate_scores():
    """
    Example 1: Calculate composite scores for all stocks.

    This will calculate value, growth, quality, and momentum scores
    for each stock and combine them into a composite score.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 1: Calculate Composite Scores")
    logger.info("=" * 80)

    db = get_db_session()

    try:
        # Create service with default weights (25% each)
        service = ScoreService(db)

        # Calculate scores for first 10 stocks (for testing)
        logger.info("Calculating scores for first 10 stocks...")
        results = service.calculate_scores_for_all_stocks(
            limit=10,
            update_percentiles=True
        )

        # Display results
        logger.info("\nResults:")
        logger.info(f"  Total stocks processed: {results['total_stocks']}")
        logger.info(f"  Successful: {results['successful']}")
        logger.info(f"  Failed: {results['failed']}")
        logger.info(f"  Skipped: {results['skipped']}")

        if results['scores']:
            logger.info("\nTop 5 scores calculated:")
            sorted_scores = sorted(
                results['scores'],
                key=lambda x: x['composite_score'],
                reverse=True
            )[:5]

            for stock in sorted_scores:
                logger.info(
                    f"  {stock['ticker']}: {stock['composite_score']:.1f} "
                    f"(V:{stock['value_score']:.1f}, G:{stock['growth_score']:.1f}, "
                    f"Q:{stock['quality_score']:.1f}, M:{stock['momentum_score']:.1f})"
                )

    finally:
        db.close()


def example_2_get_top_stocks():
    """
    Example 2: Get top-scoring stocks.

    Retrieve and display the stocks with the highest composite scores.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 2: Get Top-Scoring Stocks")
    logger.info("=" * 80)

    db = get_db_session()

    try:
        service = ScoreService(db)

        # Get top 20 stocks with minimum score of 60
        logger.info("Retrieving top 20 stocks with score >= 60...")
        top_stocks = service.get_top_stocks(limit=20, min_score=60.0)

        if not top_stocks:
            logger.warning("No stocks found matching criteria")
            return

        # Display results in a table
        logger.info(f"\nFound {len(top_stocks)} stocks:\n")
        logger.info(f"{'Rank':<5} {'Ticker':<8} {'Name':<25} {'Score':<8} {'Percentile':<10} {'Sector':<20}")
        logger.info("-" * 90)

        for idx, stock in enumerate(top_stocks, 1):
            logger.info(
                f"{idx:<5} "
                f"{stock['ticker']:<8} "
                f"{stock['name_kr'][:23]:<25} "
                f"{stock['composite_score']:>6.1f}  "
                f"{stock['percentile_rank']:>6.1f}%    "
                f"{stock['sector'][:18] if stock['sector'] else 'N/A':<20}"
            )

        # Show average scores
        avg_composite = sum(s['composite_score'] for s in top_stocks) / len(top_stocks)
        avg_value = sum(s['value_score'] for s in top_stocks if s['value_score']) / len(top_stocks)
        avg_growth = sum(s['growth_score'] for s in top_stocks if s['growth_score']) / len(top_stocks)
        avg_quality = sum(s['quality_score'] for s in top_stocks if s['quality_score']) / len(top_stocks)
        avg_momentum = sum(s['momentum_score'] for s in top_stocks if s['momentum_score']) / len(top_stocks)

        logger.info(f"\nAverage Scores:")
        logger.info(f"  Composite: {avg_composite:.1f}")
        logger.info(f"  Value: {avg_value:.1f}")
        logger.info(f"  Growth: {avg_growth:.1f}")
        logger.info(f"  Quality: {avg_quality:.1f}")
        logger.info(f"  Momentum: {avg_momentum:.1f}")

    finally:
        db.close()


def example_3_custom_weights():
    """
    Example 3: Calculate scores with custom weights.

    This example shows how to customize the importance of each component.
    For example, emphasize value and quality over growth and momentum.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 3: Custom Weight Configuration")
    logger.info("=" * 80)

    db = get_db_session()

    try:
        # Create service with custom weights
        # Emphasize value and quality (40% each), lower weight for growth and momentum (10% each)
        logger.info("Creating scorer with custom weights:")
        logger.info("  Value: 40%")
        logger.info("  Quality: 40%")
        logger.info("  Growth: 10%")
        logger.info("  Momentum: 10%")

        service = ScoreService(
            db,
            weight_value=0.40,
            weight_quality=0.40,
            weight_growth=0.10,
            weight_momentum=0.10
        )

        # Calculate score for a specific stock
        # First, get a stock
        stocks = service.repository.get_active_stocks(limit=1)
        if not stocks:
            logger.warning("No stocks found")
            return

        stock = stocks[0]
        logger.info(f"\nCalculating custom score for {stock.ticker}...")

        metrics = service.calculate_score_for_stock(stock.id)
        if metrics:
            logger.info(f"\nCustom Score Results for {stock.ticker}:")
            logger.info(f"  Composite Score: {metrics.composite_score:.1f}")
            logger.info(f"  Value Score: {metrics.value_score:.1f} (weight: 40%)")
            logger.info(f"  Quality Score: {metrics.quality_score:.1f} (weight: 40%)")
            logger.info(f"  Growth Score: {metrics.growth_score:.1f} (weight: 10%)")
            logger.info(f"  Momentum Score: {metrics.momentum_score:.1f} (weight: 10%)")
        else:
            logger.warning(f"Could not calculate score for {stock.ticker}")

    finally:
        db.close()


def example_4_add_to_watchlist():
    """
    Example 4: Add top stocks to watchlist.

    This example shows how to automatically add the top-scoring stocks
    to a user's watchlist.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 4: Add Top Stocks to Watchlist")
    logger.info("=" * 80)

    db = get_db_session()

    try:
        service = ScoreService(db)

        # Add top 30 stocks with score >= 65 to watchlist
        user_id = "example_user"
        logger.info(f"Adding top 30 stocks (score >= 65) to watchlist for user '{user_id}'...")

        results = service.add_top_stocks_to_watchlist(
            user_id=user_id,
            limit=30,
            min_score=65.0,
            tags="top-scored,example,high-quality"
        )

        # Display results
        logger.info("\nWatchlist Update Results:")
        logger.info(f"  Total stocks processed: {results['total']}")
        logger.info(f"  Successfully added: {results['added']}")
        logger.info(f"  Failed: {results['failed']}")

        if results.get('stocks'):
            logger.info(f"\nTop 10 stocks added to watchlist:")
            for stock in results['stocks'][:10]:
                logger.info(
                    f"  {stock['ticker']}: {stock['name']} "
                    f"(Score: {stock['score']:.1f}, Percentile: {stock['percentile']:.0f}%)"
                )

            if len(results['stocks']) > 10:
                logger.info(f"  ... and {len(results['stocks']) - 10} more")

    finally:
        db.close()


def example_5_detailed_breakdown():
    """
    Example 5: Get detailed score breakdown.

    This example shows how to get a detailed breakdown of all score
    components for a specific stock.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 5: Detailed Score Breakdown")
    logger.info("=" * 80)

    db = get_db_session()

    try:
        service = ScoreService(db)

        # Get top stock
        top_stocks = service.get_top_stocks(limit=1)
        if not top_stocks:
            logger.warning("No stocks found")
            return

        ticker = top_stocks[0]['ticker']
        logger.info(f"Getting detailed breakdown for top stock: {ticker}...\n")

        # Get stock by ticker
        stock = service.repository.get_stock_by_ticker(ticker)
        if not stock:
            logger.warning(f"Stock {ticker} not found")
            return

        breakdown = service.get_stock_score_breakdown(stock.id)
        if not breakdown:
            logger.warning(f"No score data for {ticker}")
            return

        # Display detailed breakdown
        logger.info("=" * 80)
        logger.info(f"DETAILED SCORE BREAKDOWN: {ticker}")
        logger.info("=" * 80)

        stock_info = breakdown['stock']
        logger.info(f"\nStock Information:")
        logger.info(f"  Ticker: {stock_info['ticker']}")
        logger.info(f"  Name: {stock_info['name_kr']}")
        logger.info(f"  Market: {stock_info['market']}")
        logger.info(f"  Sector: {stock_info['sector']}")
        logger.info(f"  Industry: {stock_info['industry']}")

        logger.info(f"\nOverall Performance:")
        logger.info(f"  Composite Score: {breakdown['composite_score']:.1f}/100")
        logger.info(f"  Percentile Rank: {breakdown['percentile_rank']:.1f}%")
        logger.info(f"  (Better than {breakdown['percentile_rank']:.1f}% of all stocks)")

        # Component details
        logger.info(f"\nComponent Scores:")

        for component_name, component_data in breakdown['components'].items():
            score = component_data.get('score')
            weight = component_data.get('weight')

            logger.info(f"\n  {component_name.upper()}: {score:.1f}/100 (weight: {weight:.0%})")

            # Show sub-scores
            for metric, value in component_data.items():
                if metric not in ['score', 'weight'] and value is not None:
                    metric_name = metric.replace('_score', '').replace('_', ' ').title()
                    logger.info(f"    {metric_name}: {value:.1f}")

        # Data quality
        dq = breakdown['data_quality']
        logger.info(f"\nData Quality:")
        logger.info(f"  Overall: {dq['score']:.1f}%")
        logger.info(f"  Missing Metrics: {dq['missing_count']}/{dq['total_count']}")

        if breakdown.get('notes'):
            logger.info(f"\nNotes: {breakdown['notes']}")

    finally:
        db.close()


def main():
    """Run all examples."""
    try:
        logger.info("\n" + "=" * 80)
        logger.info("STOCK SCORING SYSTEM - EXAMPLES")
        logger.info("=" * 80)

        # Run examples
        example_1_calculate_scores()
        example_2_get_top_stocks()
        example_3_custom_weights()
        example_4_add_to_watchlist()
        example_5_detailed_breakdown()

        logger.info("\n" + "=" * 80)
        logger.info("ALL EXAMPLES COMPLETED")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
