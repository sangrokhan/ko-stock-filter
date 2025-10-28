"""
Example usage of Trading Signal Generator.

Demonstrates:
1. Signal generation for entry/exit
2. Signal validation
3. Order execution (dry-run mode)
4. Position monitoring
"""
import logging
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from shared.database.connection import SessionLocal
from services.trading_engine.signal_generator import TradingSignalGenerator
from services.trading_engine.signal_validator import SignalValidator
from services.trading_engine.order_executor import OrderExecutor
from services.stock_screener.screening_engine import StockScreeningEngine, ScreeningCriteria
from shared.configs.config import Settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run trading signal example."""
    logger.info("=" * 80)
    logger.info("Trading Signal Generator Example")
    logger.info("=" * 80)

    # User configuration
    user_id = 'demo_user'
    portfolio_value = 100_000_000  # 100M KRW
    dry_run = True  # Always use dry-run for examples

    # Initialize database
    db = SessionLocal()

    try:
        # Step 1: Screen for candidates
        logger.info("\n--- Step 1: Screening for Candidates ---")

        settings = Settings()
        screening_engine = StockScreeningEngine(db, settings)

        criteria = ScreeningCriteria(
            max_volatility_pct=30.0,
            max_per=25.0,
            max_pbr=3.0,
            max_debt_ratio_pct=60.0,
            min_avg_volume=100_000,
            undervalued_pbr_threshold=1.5,
            min_price_history_days=60
        )

        results = screening_engine.screen_stocks(criteria)
        logger.info(f"Found {len(results)} stocks passing filters")

        # Get undervalued stocks
        undervalued = [r for r in results if r.is_undervalued]
        logger.info(f"Found {len(undervalued)} undervalued stocks")

        if undervalued:
            logger.info("\nTop 5 undervalued stocks:")
            for i, stock in enumerate(undervalued[:5], 1):
                logger.info(f"{i}. {stock.ticker} ({stock.name_kr})")
                logger.info(f"   PER: {stock.per:.2f}, PBR: {stock.pbr:.2f}")
                logger.info(f"   Reasons: {', '.join(stock.undervalued_reasons)}")

        # Get candidate tickers
        candidate_tickers = [r.ticker for r in results[:50]]

        # Step 2: Initialize signal generator
        logger.info("\n--- Step 2: Initializing Signal Generator ---")

        signal_generator = TradingSignalGenerator(
            db=db,
            user_id=user_id,
            portfolio_value=portfolio_value,
            risk_tolerance=2.0,
            max_position_size_pct=10.0,
            min_conviction_score=60.0,
            use_limit_orders=True,
            limit_order_discount_pct=1.0
        )

        logger.info(f"Signal generator initialized for portfolio: {portfolio_value:,.0f} KRW")

        # Step 3: Generate entry signals
        logger.info("\n--- Step 3: Generating Entry Signals ---")

        entry_signals = signal_generator.generate_entry_signals(
            candidate_tickers=candidate_tickers,
            min_composite_score=65.0,
            min_momentum_score=55.0
        )

        logger.info(f"Generated {len(entry_signals)} entry signals")

        if entry_signals:
            logger.info("\nTop 5 Entry Signals:")
            for i, signal in enumerate(entry_signals[:5], 1):
                logger.info(f"\n{i}. {signal.ticker}")
                logger.info(f"   Signal Strength: {signal.signal_strength.value}")
                logger.info(f"   Conviction Score: {signal.conviction_score.total_score:.1f}/100")
                logger.info(f"   Current Price: {signal.current_price:,.0f} KRW")
                logger.info(f"   Recommended Shares: {signal.recommended_shares}")
                logger.info(f"   Position Value: {signal.position_value:,.0f} KRW ({signal.position_pct:.2f}%)")
                logger.info(f"   Stop-Loss: {signal.stop_loss_price:,.0f} KRW")
                logger.info(f"   Take-Profit: {signal.take_profit_price:,.0f} KRW")
                logger.info(f"   Expected Return: {signal.expected_return_pct:.1f}%")
                logger.info(f"   Risk/Reward: {signal.risk_reward_ratio:.2f}")
                logger.info(f"   Order Type: {signal.order_type.value}")
                if signal.limit_price:
                    logger.info(f"   Limit Price: {signal.limit_price:,.0f} KRW")
                logger.info(f"   Reasons: {', '.join(signal.reasons[:3])}")

        # Step 4: Validate signals
        logger.info("\n--- Step 4: Validating Signals ---")

        signal_validator = SignalValidator(
            db=db,
            user_id=user_id,
            max_positions=20,
            max_concentration_pct=30.0,
            max_sector_concentration_pct=40.0
        )

        valid_signals = signal_validator.validate_signals_batch(entry_signals)
        logger.info(f"Valid signals: {len(valid_signals)}/{len(entry_signals)}")

        validation_summary = signal_validator.get_validation_summary(entry_signals)
        logger.info(f"Validation rate: {validation_summary['validation_rate']:.1f}%")

        if validation_summary['error_breakdown']:
            logger.info("Validation errors:")
            for error, count in validation_summary['error_breakdown'].items():
                logger.info(f"  - {error}: {count}")

        # Step 5: Execute orders (dry-run)
        logger.info("\n--- Step 5: Executing Orders (Dry-Run) ---")

        order_executor = OrderExecutor(
            db=db,
            user_id=user_id,
            dry_run=dry_run
        )

        # Limit to top 3 signals
        top_signals = valid_signals[:3]
        executed_trades = order_executor.execute_signals_batch(top_signals)

        logger.info(f"Created {len(executed_trades)} orders")

        if executed_trades:
            logger.info("\nExecuted Orders:")
            for trade in executed_trades:
                logger.info(f"\n{trade.order_id}")
                logger.info(f"  Ticker: {trade.ticker}")
                logger.info(f"  Action: {trade.action}")
                logger.info(f"  Quantity: {trade.quantity}")
                logger.info(f"  Price: {trade.price:,.0f} KRW")
                logger.info(f"  Total: {trade.total_amount:,.0f} KRW")
                logger.info(f"  Commission: {trade.commission:,.0f} KRW")
                logger.info(f"  Status: {trade.status}")
                logger.info(f"  Reason: {trade.reason[:100]}...")

        execution_summary = order_executor.get_execution_summary(executed_trades)
        logger.info("\nExecution Summary:")
        logger.info(f"  Total Trades: {execution_summary['total_trades']}")
        logger.info(f"  Buy Orders: {execution_summary['buy_orders']}")
        logger.info(f"  Total Value: {execution_summary['total_value']:,.0f} KRW")
        logger.info(f"  Total Commission: {execution_summary['total_commission']:,.0f} KRW")
        logger.info(f"  Tickers: {', '.join(execution_summary['tickers'])}")

        # Step 6: Generate exit signals
        logger.info("\n--- Step 6: Checking for Exit Signals ---")

        exit_signals = signal_generator.generate_exit_signals()
        logger.info(f"Generated {len(exit_signals)} exit signals")

        if exit_signals:
            logger.info("\nExit Signals:")
            for signal in exit_signals:
                logger.info(f"\n{signal.ticker}")
                logger.info(f"  Signal Type: {signal.signal_type.value}")
                logger.info(f"  Urgency: {signal.urgency}")
                logger.info(f"  Current Price: {signal.current_price:,.0f} KRW")
                logger.info(f"  Shares to Sell: {signal.recommended_shares}")
                logger.info(f"  Reasons: {', '.join(signal.reasons)}")
        else:
            logger.info("No exit signals - all positions within parameters")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("Example Complete")
        logger.info("=" * 80)
        logger.info(f"Entry Signals Generated: {len(entry_signals)}")
        logger.info(f"Valid Signals: {len(valid_signals)}")
        logger.info(f"Orders Created: {len(executed_trades)}")
        logger.info(f"Exit Signals: {len(exit_signals)}")
        logger.info("\nNote: This was a dry-run. No actual trades were executed.")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error in example: {e}", exc_info=True)
        raise

    finally:
        db.close()


if __name__ == '__main__':
    main()
