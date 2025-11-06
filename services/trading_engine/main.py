"""
Trading Engine Service - Main Entry Point.

Comprehensive trading engine that:
- Generates entry and exit signals based on fundamental and technical analysis
- Validates signals against risk limits and portfolio constraints
- Executes orders with proper position sizing
- Monitors positions for stop-loss and take-profit triggers
- Logs all trading activity

Usage:
    python -m services.trading_engine.main --user-id USER_ID --mode [signals|monitor|execute]
"""
import logging
import argparse
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.database.connection import SessionLocal
from shared.database.models import Portfolio, PortfolioRiskMetrics, Stock
from services.trading_engine.signal_generator import TradingSignalGenerator, TradingSignal, SignalType
from services.trading_engine.signal_validator import SignalValidator
from services.trading_engine.order_executor import OrderExecutor
from services.stock_screener.screening_engine import StockScreeningEngine, ScreeningCriteria

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingEngineService:
    """
    Comprehensive Trading Engine Service.

    Orchestrates the complete trading workflow:
    1. Screen stocks for candidates
    2. Generate entry/exit signals
    3. Validate signals
    4. Execute orders
    5. Monitor positions
    """

    def __init__(
        self,
        user_id: str,
        db: Session,
        dry_run: bool = True,
        portfolio_value: Optional[float] = None
    ):
        """
        Initialize trading engine.

        Args:
            user_id: User identifier
            db: Database session
            dry_run: If True, log orders without execution
            portfolio_value: Current portfolio value (auto-calculated if None)
        """
        self.user_id = user_id
        self.db = db
        self.dry_run = dry_run
        from shared.configs.config import settings
        self.settings = settings

        # Calculate portfolio value
        if portfolio_value is None:
            portfolio_value = self._calculate_portfolio_value()

        self.portfolio_value = portfolio_value

        # Initialize components
        self.signal_generator = TradingSignalGenerator(
            db=db,
            user_id=user_id,
            portfolio_value=portfolio_value,
            risk_tolerance=2.0,
            max_position_size_pct=10.0,
            min_conviction_score=60.0,
            use_limit_orders=True
        )

        self.signal_validator = SignalValidator(
            db=db,
            user_id=user_id,
            max_positions=20,
            max_concentration_pct=30.0,
            max_sector_concentration_pct=40.0
        )

        self.order_executor = OrderExecutor(
            db=db,
            user_id=user_id,
            dry_run=dry_run
        )

        self.screening_engine = StockScreeningEngine(
            db_session=db,
            settings=self.settings
        )

        logger.info(f"Trading Engine initialized for user {user_id} "
                   f"(portfolio: {portfolio_value:,.0f}, dry_run: {dry_run})")

    def run_trading_cycle(self) -> Dict:
        """
        Run complete trading cycle.

        Steps:
        1. Generate exit signals for existing positions
        2. Execute exit signals
        3. Screen for new candidates
        4. Generate entry signals
        5. Validate and execute entry signals

        Returns:
            Dictionary with cycle summary
        """
        logger.info("=" * 80)
        logger.info("Starting trading cycle")
        logger.info("=" * 80)

        results = {
            'timestamp': datetime.now(),
            'exit_signals': [],
            'entry_signals': [],
            'executed_exits': [],
            'executed_entries': [],
            'errors': []
        }

        try:
            # Step 1: Check for exit signals
            logger.info("\n--- Step 1: Checking Exit Signals ---")
            exit_signals = self.signal_generator.generate_exit_signals()
            results['exit_signals'] = [s.to_dict() for s in exit_signals]

            logger.info(f"Generated {len(exit_signals)} exit signals")

            # Step 2: Execute exit signals
            if exit_signals:
                logger.info("\n--- Step 2: Executing Exit Signals ---")
                valid_exits = self.signal_validator.validate_signals_batch(exit_signals)
                executed_exits = self.order_executor.execute_signals_batch(valid_exits)
                results['executed_exits'] = [
                    {'order_id': t.order_id, 'ticker': t.ticker, 'quantity': t.quantity}
                    for t in executed_exits
                ]
                logger.info(f"Executed {len(executed_exits)} exit orders")

            # Step 3: Screen for entry candidates
            logger.info("\n--- Step 3: Screening for Entry Candidates ---")
            candidates = self._screen_for_candidates()
            logger.info(f"Found {len(candidates)} candidate stocks")

            # Step 4: Generate entry signals
            if candidates:
                logger.info("\n--- Step 4: Generating Entry Signals ---")
                entry_signals = self.signal_generator.generate_entry_signals(
                    candidate_tickers=candidates,
                    min_composite_score=65.0,
                    min_momentum_score=55.0
                )
                results['entry_signals'] = [s.to_dict() for s in entry_signals]

                logger.info(f"Generated {len(entry_signals)} entry signals")

                # Step 5: Validate and execute entry signals
                if entry_signals:
                    logger.info("\n--- Step 5: Executing Entry Signals ---")
                    valid_entries = self.signal_validator.validate_signals_batch(entry_signals)

                    # Limit to top N signals by conviction
                    max_new_positions = 5
                    valid_entries = valid_entries[:max_new_positions]

                    executed_entries = self.order_executor.execute_signals_batch(valid_entries)
                    results['executed_entries'] = [
                        {'order_id': t.order_id, 'ticker': t.ticker, 'quantity': t.quantity}
                        for t in executed_entries
                    ]
                    logger.info(f"Executed {len(executed_entries)} entry orders")

            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("Trading Cycle Summary")
            logger.info("=" * 80)
            logger.info(f"Exit Signals: {len(results['exit_signals'])}")
            logger.info(f"Executed Exits: {len(results['executed_exits'])}")
            logger.info(f"Entry Signals: {len(results['entry_signals'])}")
            logger.info(f"Executed Entries: {len(results['executed_entries'])}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            results['errors'].append(str(e))

        return results

    def generate_signals_only(self) -> Dict:
        """
        Generate signals without executing.

        Returns:
            Dictionary with generated signals
        """
        logger.info("Generating signals (no execution)")

        results = {
            'timestamp': datetime.now(),
            'exit_signals': [],
            'entry_signals': []
        }

        # Generate exit signals
        exit_signals = self.signal_generator.generate_exit_signals()
        results['exit_signals'] = [s.to_dict() for s in exit_signals]

        # Screen and generate entry signals
        candidates = self._screen_for_candidates()
        if candidates:
            entry_signals = self.signal_generator.generate_entry_signals(
                candidate_tickers=candidates,
                min_composite_score=65.0,
                min_momentum_score=55.0
            )
            results['entry_signals'] = [s.to_dict() for s in entry_signals]

        logger.info(f"Generated {len(results['exit_signals'])} exit signals, "
                   f"{len(results['entry_signals'])} entry signals")

        return results

    def monitor_positions(self) -> Dict:
        """
        Monitor existing positions for triggers.

        Returns:
            Dictionary with monitoring results
        """
        logger.info("Monitoring positions")

        positions = self.db.query(Portfolio).filter(
            Portfolio.user_id == self.user_id
        ).all()

        results = {
            'timestamp': datetime.now(),
            'positions': [],
            'alerts': []
        }

        for position in positions:
            pos_info = {
                'ticker': position.ticker,
                'quantity': position.quantity,
                'avg_price': float(position.avg_price),
                'current_price': float(position.current_price or 0),
                'unrealized_pnl': float(position.unrealized_pnl or 0),
                'unrealized_pnl_pct': float(position.unrealized_pnl_pct or 0),
                'stop_loss_price': float(position.stop_loss_price or 0),
                'take_profit_price': float(position.take_profit_price or 0),
                'trailing_stop_price': float(position.trailing_stop_price or 0)
            }

            # Check for alerts
            if position.current_price:
                current = float(position.current_price)
                stop_loss = float(position.stop_loss_price or 0)
                take_profit = float(position.take_profit_price or 0)

                if stop_loss > 0 and current <= stop_loss:
                    pos_info['alert'] = "STOP_LOSS_TRIGGERED"
                    results['alerts'].append(f"{position.ticker}: Stop-loss triggered")

                if take_profit > 0 and current >= take_profit:
                    pos_info['alert'] = "TAKE_PROFIT_TRIGGERED"
                    results['alerts'].append(f"{position.ticker}: Take-profit triggered")

            results['positions'].append(pos_info)

        logger.info(f"Monitored {len(positions)} positions, {len(results['alerts'])} alerts")

        return results

    def _screen_for_candidates(self) -> List[str]:
        """
        Screen stocks for entry candidates.

        Returns:
            List of ticker symbols
        """
        criteria = ScreeningCriteria(
            max_volatility_pct=30.0,
            max_per=25.0,
            max_pbr=3.0,
            max_debt_ratio_pct=60.0,
            min_avg_volume=100000,
            undervalued_pbr_threshold=1.5,
            min_price_history_days=60,
            min_volume_history_days=20
        )

        screening_results = self.screening_engine.screen_stocks(criteria)

        # Prioritize undervalued stocks
        undervalued = [r for r in screening_results if r.is_undervalued]
        other = [r for r in screening_results if not r.is_undervalued]

        # Combine and get tickers
        all_results = undervalued + other
        tickers = [r.ticker for r in all_results[:50]]  # Top 50 candidates

        return tickers

    def _calculate_portfolio_value(self) -> float:
        """Calculate current portfolio value."""
        # Get latest risk metrics
        risk_metrics = self.db.query(PortfolioRiskMetrics).filter(
            PortfolioRiskMetrics.user_id == self.user_id
        ).order_by(PortfolioRiskMetrics.date.desc()).first()

        if risk_metrics:
            return float(risk_metrics.total_value)

        # Fallback: sum up positions
        positions = self.db.query(Portfolio).filter(
            Portfolio.user_id == self.user_id
        ).all()

        total = sum(float(p.current_value or 0) for p in positions)
        return total if total > 0 else 100_000_000  # Default 100M KRW

    def get_status(self) -> Dict:
        """Get trading engine status."""
        positions = self.db.query(Portfolio).filter(
            Portfolio.user_id == self.user_id
        ).all()

        return {
            'user_id': self.user_id,
            'portfolio_value': self.portfolio_value,
            'position_count': len(positions),
            'dry_run': self.dry_run,
            'tickers': [p.ticker for p in positions]
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Trading Engine Service')
    parser.add_argument('--user-id', type=str, default='default_user',
                       help='User ID')
    parser.add_argument('--mode', type=str, default='signals',
                       choices=['signals', 'monitor', 'execute', 'cycle'],
                       help='Operation mode')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Dry run mode (no actual execution)')
    parser.add_argument('--portfolio-value', type=float, default=None,
                       help='Portfolio value (auto-calculated if not provided)')

    args = parser.parse_args()

    logger.info(f"Starting Trading Engine: mode={args.mode}, user={args.user_id}, dry_run={args.dry_run}")

    db = SessionLocal()
    try:
        engine = TradingEngineService(
            user_id=args.user_id,
            db=db,
            dry_run=args.dry_run,
            portfolio_value=args.portfolio_value
        )

        if args.mode == 'signals':
            results = engine.generate_signals_only()
            print("\n=== Generated Signals ===")
            print(f"Exit Signals: {len(results['exit_signals'])}")
            print(f"Entry Signals: {len(results['entry_signals'])}")

        elif args.mode == 'monitor':
            results = engine.monitor_positions()
            print("\n=== Position Monitoring ===")
            print(f"Positions: {len(results['positions'])}")
            print(f"Alerts: {len(results['alerts'])}")
            for alert in results['alerts']:
                print(f"  - {alert}")

        elif args.mode == 'cycle':
            results = engine.run_trading_cycle()
            print("\n=== Trading Cycle Complete ===")
            print(f"Executed Exits: {len(results['executed_exits'])}")
            print(f"Executed Entries: {len(results['executed_entries'])}")

        else:
            print(f"Unknown mode: {args.mode}")

    except Exception as e:
        logger.error(f"Error running trading engine: {e}", exc_info=True)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
