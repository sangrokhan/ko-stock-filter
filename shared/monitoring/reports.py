"""
Report Generation Module

Generates daily summary reports with trading activity, performance metrics,
and system health. Sends via email or Slack.
"""

import asyncio
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import aiohttp
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Import database models (assuming they exist)
try:
    from shared.database.models import Trade, Portfolio, RiskMetric, Stock
except ImportError:
    # Fallback if models aren't available yet
    Trade = Portfolio = RiskMetric = Stock = None


class DailySummary(BaseModel):
    """Daily summary report data"""
    date: str
    trading_stats: Dict[str, Any]
    portfolio_stats: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    system_health: Dict[str, Any]
    top_performers: List[Dict[str, Any]]
    alerts_summary: Dict[str, Any]


@dataclass
class ReportGenerator:
    """
    Daily report generator

    Usage:
        generator = ReportGenerator(
            email_config={...},
            slack_webhook_url="https://..."
        )

        # Generate and send daily report
        await generator.generate_daily_report(db_session)
    """

    # Email configuration
    email_config: Optional[Dict[str, Any]] = None

    # Slack configuration
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None

    # Report history
    reports_sent: int = 0

    async def collect_trading_stats(
        self,
        db_session: AsyncSession,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Collect trading statistics for the period"""
        if Trade is None:
            return self._mock_trading_stats()

        try:
            # Query trades
            result = await db_session.execute(
                select(
                    func.count(Trade.id).label('total_trades'),
                    func.sum(Trade.quantity * Trade.price).label('total_volume'),
                    func.sum(Trade.realized_pnl).label('total_pnl'),
                    func.count(Trade.id).filter(Trade.side == 'buy').label('buy_count'),
                    func.count(Trade.id).filter(Trade.side == 'sell').label('sell_count')
                ).where(
                    and_(
                        Trade.executed_at >= start_date,
                        Trade.executed_at < end_date
                    )
                )
            )

            row = result.first()

            return {
                'total_trades': row.total_trades or 0,
                'total_volume_krw': float(row.total_volume or 0),
                'total_pnl_krw': float(row.total_pnl or 0),
                'buy_count': row.buy_count or 0,
                'sell_count': row.sell_count or 0,
                'win_rate': 0.0  # TODO: Calculate from actual P&L
            }

        except Exception as e:
            print(f"Error collecting trading stats: {e}")
            return self._mock_trading_stats()

    async def collect_portfolio_stats(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Collect current portfolio statistics"""
        if Portfolio is None:
            return self._mock_portfolio_stats()

        try:
            # Get latest portfolio
            result = await db_session.execute(
                select(Portfolio).order_by(Portfolio.updated_at.desc()).limit(1)
            )

            portfolio = result.scalar_one_or_none()

            if portfolio:
                return {
                    'total_value_krw': float(portfolio.total_value),
                    'cash_krw': float(portfolio.cash),
                    'positions_value_krw': float(portfolio.positions_value),
                    'total_pnl_krw': float(portfolio.total_pnl),
                    'total_return_percent': float(portfolio.total_return_pct),
                    'position_count': portfolio.position_count or 0
                }
            else:
                return self._mock_portfolio_stats()

        except Exception as e:
            print(f"Error collecting portfolio stats: {e}")
            return self._mock_portfolio_stats()

    async def collect_risk_metrics(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Collect current risk metrics"""
        if RiskMetric is None:
            return self._mock_risk_metrics()

        try:
            # Get latest risk metrics
            result = await db_session.execute(
                select(RiskMetric).order_by(RiskMetric.calculated_at.desc()).limit(1)
            )

            risk = result.scalar_one_or_none()

            if risk:
                return {
                    'max_drawdown_percent': float(risk.max_drawdown),
                    'current_drawdown_percent': float(risk.current_drawdown),
                    'sharpe_ratio': float(risk.sharpe_ratio) if risk.sharpe_ratio else 0.0,
                    'var_95_krw': float(risk.var_95) if risk.var_95 else 0.0,
                    'portfolio_beta': float(risk.portfolio_beta) if risk.portfolio_beta else 1.0,
                    'concentration_risk': float(risk.concentration_risk) if risk.concentration_risk else 0.0
                }
            else:
                return self._mock_risk_metrics()

        except Exception as e:
            print(f"Error collecting risk metrics: {e}")
            return self._mock_risk_metrics()

    async def collect_top_performers(
        self,
        db_session: AsyncSession,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Collect top performing stocks"""
        # This would query actual position performance
        # For now, return mock data
        return [
            {'symbol': '005930', 'name': 'Samsung Electronics', 'return_percent': 5.2, 'pnl_krw': 1500000},
            {'symbol': '000660', 'name': 'SK Hynix', 'return_percent': 3.8, 'pnl_krw': 950000},
            {'symbol': '035420', 'name': 'NAVER', 'return_percent': 2.1, 'pnl_krw': 420000},
        ]

    def collect_system_health(self) -> Dict[str, Any]:
        """Collect system health metrics"""
        import psutil

        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'cpu_percent': cpu,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent,
            'uptime_hours': 0.0,  # TODO: Track actual uptime
            'error_count': 0,  # TODO: Get from metrics
            'alert_count': 0  # TODO: Get from alert manager
        }

    async def collect_alerts_summary(self) -> Dict[str, Any]:
        """Collect summary of alerts sent"""
        # TODO: Get from AlertManager
        return {
            'total_alerts': 0,
            'critical_alerts': 0,
            'error_alerts': 0,
            'warning_alerts': 0
        }

    async def generate_daily_summary(
        self,
        db_session: Optional[AsyncSession] = None,
        date: Optional[datetime] = None
    ) -> DailySummary:
        """
        Generate daily summary report

        Args:
            db_session: Database session
            date: Date for report (defaults to yesterday)

        Returns:
            DailySummary object
        """
        if date is None:
            date = datetime.now() - timedelta(days=1)

        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        # Collect all data
        if db_session:
            trading_stats = await self.collect_trading_stats(db_session, start_date, end_date)
            portfolio_stats = await self.collect_portfolio_stats(db_session)
            risk_metrics = await self.collect_risk_metrics(db_session)
            top_performers = await self.collect_top_performers(db_session)
        else:
            trading_stats = self._mock_trading_stats()
            portfolio_stats = self._mock_portfolio_stats()
            risk_metrics = self._mock_risk_metrics()
            top_performers = []

        system_health = self.collect_system_health()
        alerts_summary = await self.collect_alerts_summary()

        return DailySummary(
            date=date.strftime('%Y-%m-%d'),
            trading_stats=trading_stats,
            portfolio_stats=portfolio_stats,
            risk_metrics=risk_metrics,
            system_health=system_health,
            top_performers=top_performers,
            alerts_summary=alerts_summary
        )

    async def send_daily_report(
        self,
        summary: DailySummary,
        send_email: bool = True,
        send_slack: bool = True
    ):
        """
        Send daily report via configured channels

        Args:
            summary: DailySummary to send
            send_email: Send via email
            send_slack: Send via Slack
        """
        tasks = []

        if send_email and self.email_config:
            tasks.append(self._send_email_report(summary))

        if send_slack and self.slack_webhook_url:
            tasks.append(self._send_slack_report(summary))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            self.reports_sent += 1

    async def _send_email_report(self, summary: DailySummary):
        """Send report via email"""
        try:
            config = self.email_config

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Daily Trading Summary - {summary.date}"
            msg['From'] = config['from_email']
            msg['To'] = ', '.join(config['to_emails'])

            # Create HTML body
            html = self._generate_html_report(summary)
            msg.attach(MIMEText(html, 'html'))

            # Send email
            with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
                server.starttls()
                server.login(config['username'], config['password'])
                server.send_message(msg)

        except Exception as e:
            print(f"Error sending email report: {e}")

    async def _send_slack_report(self, summary: DailySummary):
        """Send report to Slack"""
        try:
            # Create Slack message
            payload = {
                "channel": self.slack_channel,
                "username": "Daily Report Bot",
                "icon_emoji": ":bar_chart:",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"Daily Trading Summary - {summary.date}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Total Trades:*\n{summary.trading_stats['total_trades']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Total Volume:*\n{summary.trading_stats['total_volume_krw']:,.0f} KRW"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Total P&L:*\n{summary.trading_stats['total_pnl_krw']:,.0f} KRW"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Portfolio Value:*\n{summary.portfolio_stats['total_value_krw']:,.0f} KRW"
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Risk Metrics*"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Max Drawdown:*\n{summary.risk_metrics['max_drawdown_percent']:.2f}%"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Sharpe Ratio:*\n{summary.risk_metrics['sharpe_ratio']:.2f}"
                            }
                        ]
                    }
                ]
            }

            # Add top performers if available
            if summary.top_performers:
                performers_text = "\n".join([
                    f"• {p['symbol']} ({p['name']}): {p['return_percent']:+.2f}%"
                    for p in summary.top_performers[:3]
                ])

                payload["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Top Performers*\n{performers_text}"
                    }
                })

            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 200:
                        print(f"Error sending Slack report: {response.status}")

        except Exception as e:
            print(f"Error sending Slack report: {e}")

    def _generate_html_report(self, summary: DailySummary) -> str:
        """Generate HTML report"""
        top_performers_html = ""
        if summary.top_performers:
            performers_rows = "\n".join([
                f"<tr><td>{p['symbol']}</td><td>{p['name']}</td><td>{p['return_percent']:+.2f}%</td><td>{p['pnl_krw']:,.0f} KRW</td></tr>"
                for p in summary.top_performers
            ])
            top_performers_html = f"""
            <h2>Top Performers</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Name</th>
                    <th>Return</th>
                    <th>P&L</th>
                </tr>
                {performers_rows}
            </table>
            """

        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                h2 {{ color: #555; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #007bff; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff; }}
                .stat-label {{ font-size: 14px; color: #666; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #333; margin-top: 5px; }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
                .warning {{ color: #ffc107; }}
            </style>
        </head>
        <body>
            <h1>Daily Trading Summary - {summary.date}</h1>

            <h2>Trading Activity</h2>
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Trades</div>
                    <div class="stat-value">{summary.trading_stats['total_trades']}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Volume</div>
                    <div class="stat-value">{summary.trading_stats['total_volume_krw']:,.0f} KRW</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total P&L</div>
                    <div class="stat-value {'positive' if summary.trading_stats['total_pnl_krw'] >= 0 else 'negative'}">
                        {summary.trading_stats['total_pnl_krw']:+,.0f} KRW
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Buy/Sell Ratio</div>
                    <div class="stat-value">
                        {summary.trading_stats['buy_count']}/{summary.trading_stats['sell_count']}
                    </div>
                </div>
            </div>

            <h2>Portfolio Status</h2>
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Value</div>
                    <div class="stat-value">{summary.portfolio_stats['total_value_krw']:,.0f} KRW</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Cash</div>
                    <div class="stat-value">{summary.portfolio_stats['cash_krw']:,.0f} KRW</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Positions Value</div>
                    <div class="stat-value">{summary.portfolio_stats['positions_value_krw']:,.0f} KRW</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Return</div>
                    <div class="stat-value {'positive' if summary.portfolio_stats['total_return_percent'] >= 0 else 'negative'}">
                        {summary.portfolio_stats['total_return_percent']:+.2f}%
                    </div>
                </div>
            </div>

            <h2>Risk Metrics</h2>
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">Max Drawdown</div>
                    <div class="stat-value {'warning' if summary.risk_metrics['max_drawdown_percent'] > 20 else ''}">
                        {summary.risk_metrics['max_drawdown_percent']:.2f}%
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Sharpe Ratio</div>
                    <div class="stat-value">{summary.risk_metrics['sharpe_ratio']:.2f}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">VaR (95%)</div>
                    <div class="stat-value">{summary.risk_metrics['var_95_krw']:,.0f} KRW</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Portfolio Beta</div>
                    <div class="stat-value">{summary.risk_metrics['portfolio_beta']:.2f}</div>
                </div>
            </div>

            {top_performers_html}

            <h2>System Health</h2>
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">CPU Usage</div>
                    <div class="stat-value {'warning' if summary.system_health['cpu_percent'] > 70 else ''}">
                        {summary.system_health['cpu_percent']:.1f}%
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Memory Usage</div>
                    <div class="stat-value {'warning' if summary.system_health['memory_percent'] > 75 else ''}">
                        {summary.system_health['memory_percent']:.1f}%
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Alerts Today</div>
                    <div class="stat-value">{summary.alerts_summary['total_alerts']}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Errors Today</div>
                    <div class="stat-value {'warning' if summary.system_health['error_count'] > 0 else ''}">
                        {summary.system_health['error_count']}
                    </div>
                </div>
            </div>

            <p style="margin-top: 40px; color: #666; font-size: 12px; text-align: center;">
                Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Korean Stock Trading System
            </p>
        </body>
        </html>
        """

    # Mock data methods
    def _mock_trading_stats(self) -> Dict[str, Any]:
        return {
            'total_trades': 0,
            'total_volume_krw': 0.0,
            'total_pnl_krw': 0.0,
            'buy_count': 0,
            'sell_count': 0,
            'win_rate': 0.0
        }

    def _mock_portfolio_stats(self) -> Dict[str, Any]:
        return {
            'total_value_krw': 10000000.0,
            'cash_krw': 5000000.0,
            'positions_value_krw': 5000000.0,
            'total_pnl_krw': 0.0,
            'total_return_percent': 0.0,
            'position_count': 0
        }

    def _mock_risk_metrics(self) -> Dict[str, Any]:
        return {
            'max_drawdown_percent': 0.0,
            'current_drawdown_percent': 0.0,
            'sharpe_ratio': 0.0,
            'var_95_krw': 0.0,
            'portfolio_beta': 1.0,
            'concentration_risk': 0.0
        }
