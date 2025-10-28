"""
Risk reporting utility script.
Generate comprehensive risk reports for portfolios.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.database.connection import SessionLocal
from services.risk_manager.main import RiskManagerService
from shared.database.models import Portfolio, PortfolioRiskMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskReporter:
    """Generate risk reports for portfolios."""

    def __init__(self):
        """Initialize risk reporter."""
        self.risk_manager = RiskManagerService()

    def generate_user_report(self, user_id: str, db: Session) -> Dict:
        """
        Generate comprehensive risk report for a user.

        Args:
            user_id: User identifier
            db: Database session

        Returns:
            Dictionary with risk report
        """
        # Get current metrics
        metrics = self.risk_manager.calculate_portfolio_metrics(user_id, db)

        # Get risk status
        risk_status = self.risk_manager.check_portfolio_risk(user_id, db)

        # Get historical metrics (last 30 days)
        historical = db.query(PortfolioRiskMetrics).filter(
            PortfolioRiskMetrics.user_id == user_id,
            PortfolioRiskMetrics.date >= datetime.utcnow() - timedelta(days=30)
        ).order_by(desc(PortfolioRiskMetrics.date)).all()

        # Calculate trends
        trends = self._calculate_trends(historical)

        # Generate position analysis
        position_analysis = self._analyze_positions(metrics.positions, metrics.total_value)

        report = {
            'report_date': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'portfolio_summary': {
                'total_value': metrics.total_value,
                'cash_balance': metrics.cash_balance,
                'invested_amount': metrics.invested_amount,
                'position_count': metrics.position_count
            },
            'pnl_summary': {
                'total_pnl': metrics.total_pnl,
                'total_pnl_pct': round(metrics.total_pnl_pct, 2),
                'realized_pnl': metrics.realized_pnl,
                'unrealized_pnl': metrics.unrealized_pnl
            },
            'risk_metrics': {
                'current_drawdown': round(metrics.current_drawdown, 2),
                'peak_value': metrics.peak_value,
                'total_loss_from_initial': metrics.initial_capital - metrics.total_value,
                'total_loss_from_initial_pct': round(metrics.total_loss_from_initial_pct, 2),
                'largest_position_pct': round(metrics.largest_position_pct, 2),
                'largest_position_ticker': metrics.largest_position_ticker
            },
            'risk_status': {
                'status': risk_status['status'],
                'is_trading_halted': metrics.is_trading_halted,
                'violations': risk_status['violations'],
                'warnings': risk_status['warnings']
            },
            'risk_limits': risk_status['limits'],
            'trends': trends,
            'position_analysis': position_analysis,
            'recommendations': self._generate_recommendations(metrics, risk_status)
        }

        return report

    def _calculate_trends(self, historical: List[PortfolioRiskMetrics]) -> Dict:
        """Calculate trends from historical data."""
        if len(historical) < 2:
            return {
                'data_points': len(historical),
                'pnl_trend': 'insufficient_data',
                'drawdown_trend': 'insufficient_data'
            }

        # Sort by date (oldest first)
        historical = sorted(historical, key=lambda x: x.date)

        # Calculate P&L trend
        pnl_values = [h.total_pnl_pct or 0 for h in historical]
        pnl_change = pnl_values[-1] - pnl_values[0] if len(pnl_values) >= 2 else 0

        # Calculate drawdown trend
        drawdown_values = [h.current_drawdown for h in historical]
        drawdown_change = drawdown_values[-1] - drawdown_values[0] if len(drawdown_values) >= 2 else 0

        return {
            'data_points': len(historical),
            'period_days': (historical[-1].date - historical[0].date).days,
            'pnl_trend': 'improving' if pnl_change > 0 else 'declining',
            'pnl_change_pct': round(pnl_change, 2),
            'drawdown_trend': 'improving' if drawdown_change < 0 else 'worsening',
            'drawdown_change_pct': round(drawdown_change, 2),
            'avg_daily_pnl': round(sum(h.daily_pnl or 0 for h in historical) / len(historical), 2),
            'best_day_pnl': max((h.daily_pnl or 0) for h in historical),
            'worst_day_pnl': min((h.daily_pnl or 0) for h in historical)
        }

    def _analyze_positions(self, positions: List[Dict], total_value: int) -> Dict:
        """Analyze position concentration and risk."""
        if not positions or total_value == 0:
            return {
                'position_count': 0,
                'concentration_risk': 'none',
                'top_positions': []
            }

        # Sort by position size
        sorted_positions = sorted(
            positions,
            key=lambda x: x['current_value'],
            reverse=True
        )

        # Calculate concentration
        top_3_pct = sum(p['position_pct'] for p in sorted_positions[:3])
        top_5_pct = sum(p['position_pct'] for p in sorted_positions[:5])

        # Determine concentration risk
        if top_3_pct > 50:
            concentration_risk = 'high'
        elif top_3_pct > 30:
            concentration_risk = 'moderate'
        else:
            concentration_risk = 'low'

        # Get winners and losers
        winners = [p for p in positions if p['unrealized_pnl'] > 0]
        losers = [p for p in positions if p['unrealized_pnl'] < 0]

        return {
            'position_count': len(positions),
            'concentration_risk': concentration_risk,
            'top_3_concentration_pct': round(top_3_pct, 2),
            'top_5_concentration_pct': round(top_5_pct, 2),
            'top_positions': sorted_positions[:5],
            'winners_count': len(winners),
            'losers_count': len(losers),
            'winners_total_pnl': sum(p['unrealized_pnl'] for p in winners),
            'losers_total_pnl': sum(p['unrealized_pnl'] for p in losers)
        }

    def _generate_recommendations(self, metrics, risk_status: Dict) -> List[str]:
        """Generate actionable recommendations based on risk analysis."""
        recommendations = []

        # Check trading halt
        if metrics.is_trading_halted:
            recommendations.append(
                "CRITICAL: Trading is halted due to 30% loss limit. "
                "Review portfolio strategy before resuming trading."
            )
            recommendations.append(
                "Consider: Re-evaluate risk management approach and position sizing strategy."
            )

        # Check drawdown
        if metrics.current_drawdown > self.risk_manager.risk_params.max_drawdown:
            recommendations.append(
                f"Drawdown of {metrics.current_drawdown:.2f}% exceeds limit. "
                "Consider reducing position sizes or taking defensive action."
            )

        # Check position concentration
        if metrics.largest_position_pct > self.risk_manager.risk_params.max_position_size:
            recommendations.append(
                f"Position {metrics.largest_position_ticker} ({metrics.largest_position_pct:.2f}%) "
                f"exceeds maximum size of {self.risk_manager.risk_params.max_position_size}%. "
                "Consider trimming this position."
            )

        # Check loss approaching limit
        if metrics.total_loss_from_initial_pct > self.risk_manager.risk_params.max_total_loss * 0.8:
            recommendations.append(
                f"Loss of {metrics.total_loss_from_initial_pct:.2f}% approaching "
                f"{self.risk_manager.risk_params.max_total_loss}% limit. "
                "Urgent action needed to prevent trading halt."
            )

        # Positive performance
        if metrics.total_pnl_pct > 10:
            recommendations.append(
                "Portfolio showing strong performance. "
                "Consider taking partial profits to lock in gains."
            )

        # No major issues
        if not recommendations and risk_status['status'] == 'OK':
            recommendations.append(
                "Portfolio within acceptable risk parameters. Continue monitoring."
            )

        return recommendations

    def print_report(self, report: Dict):
        """Print formatted report to console."""
        print("\n" + "=" * 80)
        print(f"RISK MANAGEMENT REPORT - {report['user_id']}")
        print(f"Generated: {report['report_date']}")
        print("=" * 80)

        # Portfolio Summary
        ps = report['portfolio_summary']
        print("\nPORTFOLIO SUMMARY:")
        print(f"  Total Value:      {ps['total_value']:>15,} KRW")
        print(f"  Cash Balance:     {ps['cash_balance']:>15,} KRW")
        print(f"  Invested:         {ps['invested_amount']:>15,} KRW")
        print(f"  Positions:        {ps['position_count']:>15}")

        # P&L Summary
        pnl = report['pnl_summary']
        print("\nP&L SUMMARY:")
        print(f"  Total P&L:        {pnl['total_pnl']:>15,} KRW ({pnl['total_pnl_pct']:>6.2f}%)")
        print(f"  Realized P&L:     {pnl['realized_pnl']:>15,} KRW")
        print(f"  Unrealized P&L:   {pnl['unrealized_pnl']:>15,} KRW")

        # Risk Metrics
        rm = report['risk_metrics']
        print("\nRISK METRICS:")
        print(f"  Current Drawdown: {rm['current_drawdown']:>15.2f}%")
        print(f"  Peak Value:       {rm['peak_value']:>15,} KRW")
        print(f"  Loss from Initial:{rm['total_loss_from_initial_pct']:>15.2f}%")
        print(f"  Largest Position: {rm['largest_position_ticker']:>10} ({rm['largest_position_pct']:.2f}%)")

        # Risk Status
        rs = report['risk_status']
        print(f"\nRISK STATUS: {rs['status']}")
        print(f"  Trading Halted: {'YES' if rs['is_trading_halted'] else 'NO'}")

        if rs['violations']:
            print("\n  VIOLATIONS:")
            for v in rs['violations']:
                print(f"    - {v}")

        if rs['warnings']:
            print("\n  WARNINGS:")
            for w in rs['warnings']:
                print(f"    - {w}")

        # Recommendations
        print("\nRECOMMENDATIONS:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")

        print("\n" + "=" * 80 + "\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Risk Report Generator")
    parser.add_argument(
        "--user",
        type=str,
        help="User ID to generate report for (default: all users)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON"
    )

    args = parser.parse_args()

    reporter = RiskReporter()
    db = SessionLocal()

    try:
        if args.user:
            # Generate report for specific user
            report = reporter.generate_user_report(args.user, db)

            if args.json:
                import json
                print(json.dumps(report, indent=2, default=str))
            else:
                reporter.print_report(report)
        else:
            # Generate reports for all users
            users = db.query(Portfolio.user_id).distinct().all()

            for user_tuple in users:
                user_id = user_tuple[0]
                report = reporter.generate_user_report(user_id, db)

                if args.json:
                    import json
                    print(json.dumps(report, indent=2, default=str))
                else:
                    reporter.print_report(report)

    finally:
        db.close()


if __name__ == "__main__":
    main()
