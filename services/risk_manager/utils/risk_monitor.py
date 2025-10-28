"""
Risk monitoring utility script.
Continuously monitors portfolio risk and sends alerts when limits are approached.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import logging
import time
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session

from shared.database.connection import SessionLocal
from services.risk_manager.main import RiskManagerService
from shared.database.models import Portfolio, PortfolioRiskMetrics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiskMonitor:
    """Continuous risk monitoring service."""

    def __init__(self, check_interval: int = 60):
        """
        Initialize risk monitor.

        Args:
            check_interval: Interval between checks in seconds
        """
        self.risk_manager = RiskManagerService()
        self.check_interval = check_interval
        self.running = False

    def get_all_users(self, db: Session) -> List[str]:
        """Get all users with portfolios."""
        users = db.query(Portfolio.user_id).distinct().all()
        return [user[0] for user in users]

    def check_user_risk(self, user_id: str, db: Session) -> Dict:
        """
        Check risk for a specific user and return status.

        Args:
            user_id: User identifier
            db: Database session

        Returns:
            Dictionary with risk status and alerts
        """
        alerts = []
        critical_alerts = []

        # Get current metrics
        metrics = self.risk_manager.calculate_portfolio_metrics(user_id, db)

        # Check for trading halt
        if metrics.is_trading_halted:
            critical_alerts.append({
                'level': 'CRITICAL',
                'type': 'TRADING_HALTED',
                'message': (
                    f"Trading is HALTED for user {user_id}. "
                    f"Loss: {metrics.total_loss_from_initial_pct:.2f}%"
                ),
                'value': metrics.total_loss_from_initial_pct,
                'limit': self.risk_manager.risk_params.max_total_loss
            })

        # Check loss approaching limit (80% threshold)
        elif metrics.total_loss_from_initial_pct > self.risk_manager.risk_params.max_total_loss * 0.8:
            critical_alerts.append({
                'level': 'WARNING',
                'type': 'LOSS_APPROACHING_LIMIT',
                'message': (
                    f"User {user_id} loss approaching limit. "
                    f"Current: {metrics.total_loss_from_initial_pct:.2f}%, "
                    f"Limit: {self.risk_manager.risk_params.max_total_loss}%"
                ),
                'value': metrics.total_loss_from_initial_pct,
                'limit': self.risk_manager.risk_params.max_total_loss
            })

        # Check drawdown
        if metrics.current_drawdown > self.risk_manager.risk_params.max_drawdown:
            alerts.append({
                'level': 'WARNING',
                'type': 'DRAWDOWN_EXCEEDED',
                'message': (
                    f"User {user_id} drawdown exceeded. "
                    f"Current: {metrics.current_drawdown:.2f}%, "
                    f"Limit: {self.risk_manager.risk_params.max_drawdown}%"
                ),
                'value': metrics.current_drawdown,
                'limit': self.risk_manager.risk_params.max_drawdown
            })

        # Check position concentration
        if metrics.largest_position_pct > self.risk_manager.risk_params.max_position_size:
            alerts.append({
                'level': 'WARNING',
                'type': 'POSITION_SIZE_EXCEEDED',
                'message': (
                    f"User {user_id} position {metrics.largest_position_ticker} "
                    f"exceeds size limit. "
                    f"Current: {metrics.largest_position_pct:.2f}%, "
                    f"Limit: {self.risk_manager.risk_params.max_position_size}%"
                ),
                'value': metrics.largest_position_pct,
                'limit': self.risk_manager.risk_params.max_position_size,
                'ticker': metrics.largest_position_ticker
            })

        return {
            'user_id': user_id,
            'timestamp': datetime.utcnow(),
            'metrics': {
                'total_value': metrics.total_value,
                'total_pnl': metrics.total_pnl,
                'total_pnl_pct': metrics.total_pnl_pct,
                'current_drawdown': metrics.current_drawdown,
                'total_loss_from_initial_pct': metrics.total_loss_from_initial_pct,
                'is_trading_halted': metrics.is_trading_halted
            },
            'alerts': alerts,
            'critical_alerts': critical_alerts
        }

    def monitor_all_users(self):
        """Monitor all users and log alerts."""
        db = SessionLocal()
        try:
            users = self.get_all_users(db)

            if not users:
                logger.info("No users with portfolios found")
                return

            logger.info(f"Monitoring {len(users)} users...")

            total_alerts = 0
            total_critical = 0

            for user_id in users:
                try:
                    status = self.check_user_risk(user_id, db)

                    # Log critical alerts
                    for alert in status['critical_alerts']:
                        if alert['level'] == 'CRITICAL':
                            logger.critical(alert['message'])
                        else:
                            logger.warning(alert['message'])
                        total_critical += 1

                    # Log standard alerts
                    for alert in status['alerts']:
                        logger.warning(alert['message'])
                        total_alerts += 1

                    # Update metrics in database
                    metrics = self.risk_manager.calculate_portfolio_metrics(user_id, db)
                    self.risk_manager.update_risk_metrics(metrics, db)

                except Exception as e:
                    logger.error(f"Error monitoring user {user_id}: {str(e)}")

            logger.info(
                f"Monitoring complete. "
                f"Critical alerts: {total_critical}, "
                f"Warnings: {total_alerts}"
            )

        finally:
            db.close()

    def start(self):
        """Start continuous monitoring."""
        logger.info("Starting Risk Monitor Service")
        logger.info(f"Check interval: {self.check_interval} seconds")

        self.running = True

        try:
            while self.running:
                self.monitor_all_users()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.stop()

    def stop(self):
        """Stop monitoring."""
        logger.info("Stopping Risk Monitor Service")
        self.running = False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Risk Monitoring Service")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (no continuous monitoring)"
    )

    args = parser.parse_args()

    monitor = RiskMonitor(check_interval=args.interval)

    if args.once:
        logger.info("Running single risk check...")
        monitor.monitor_all_users()
        logger.info("Risk check complete")
    else:
        monitor.start()


if __name__ == "__main__":
    main()
