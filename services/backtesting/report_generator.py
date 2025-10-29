"""
Performance Report Generator

Generates comprehensive performance reports with charts and visualizations.
"""

from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import seaborn as sns

from .backtesting_engine import BacktestResult


class ReportGenerator:
    """Generate performance reports with charts"""

    def __init__(self, result: BacktestResult):
        """
        Initialize report generator

        Args:
            result: Backtest result to generate report from
        """
        self.result = result
        self.metrics = result.metrics

        # Set style
        sns.set_style("whitegrid")
        plt.rcParams["figure.figsize"] = (16, 10)
        plt.rcParams["font.size"] = 10

    def generate_full_report(
        self, output_dir: str = "backtest_reports", save_charts: bool = True
    ) -> str:
        """
        Generate full performance report

        Args:
            output_dir: Directory to save report and charts
            save_charts: Whether to save chart images

        Returns:
            Path to generated report HTML file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate charts
        if save_charts:
            self.plot_portfolio_performance(output_path / "portfolio_performance.png")
            self.plot_drawdown_analysis(output_path / "drawdown_analysis.png")
            self.plot_returns_distribution(output_path / "returns_distribution.png")
            self.plot_monthly_returns(output_path / "monthly_returns.png")
            self.plot_rolling_metrics(output_path / "rolling_metrics.png")

        # Generate HTML report
        html_report = self._generate_html_report(output_path, save_charts)

        report_file = output_path / "backtest_report.html"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_report)

        # Generate CSV exports
        self._export_data(output_path)

        return str(report_file)

    def plot_portfolio_performance(self, save_path: Optional[str] = None):
        """Plot portfolio equity curve"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

        # Portfolio value
        portfolio_values = self.result.portfolio_values
        ax1.plot(portfolio_values.index, portfolio_values.values, linewidth=2, label="Portfolio Value")
        ax1.axhline(
            y=self.metrics.initial_capital,
            color="gray",
            linestyle="--",
            alpha=0.5,
            label="Initial Capital",
        )
        ax1.set_ylabel("Portfolio Value (KRW)", fontsize=12)
        ax1.set_title("Portfolio Performance", fontsize=14, fontweight="bold")
        ax1.legend(loc="upper left")
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.0f}"))

        # Cumulative returns
        cumulative_returns = (portfolio_values / self.metrics.initial_capital - 1) * 100
        ax2.plot(cumulative_returns.index, cumulative_returns.values, linewidth=2, color="green")
        ax2.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
        ax2.set_ylabel("Cumulative Return (%)", fontsize=12)
        ax2.set_xlabel("Date", fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.fill_between(
            cumulative_returns.index,
            0,
            cumulative_returns.values,
            alpha=0.3,
            color="green",
        )

        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
        else:
            plt.show()

    def plot_drawdown_analysis(self, save_path: Optional[str] = None):
        """Plot drawdown analysis"""
        fig = plt.figure(figsize=(16, 10))
        gs = GridSpec(2, 2, figure=fig)

        # Calculate drawdown
        portfolio_values = self.result.portfolio_values
        running_max = portfolio_values.expanding().max()
        drawdown = (portfolio_values - running_max) / running_max * 100

        # Drawdown over time
        ax1 = fig.add_subplot(gs[0, :])
        ax1.fill_between(drawdown.index, 0, drawdown.values, alpha=0.3, color="red")
        ax1.plot(drawdown.index, drawdown.values, linewidth=1, color="red")
        ax1.set_ylabel("Drawdown (%)", fontsize=12)
        ax1.set_title("Portfolio Drawdown Over Time", fontsize=14, fontweight="bold")
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        # Drawdown histogram
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.hist(drawdown.values, bins=50, alpha=0.7, color="red", edgecolor="black")
        ax2.axvline(
            x=drawdown.mean(), color="blue", linestyle="--", label=f"Mean: {drawdown.mean():.2f}%"
        )
        ax2.axvline(
            x=drawdown.min(),
            color="darkred",
            linestyle="--",
            label=f"Max DD: {drawdown.min():.2f}%",
        )
        ax2.set_xlabel("Drawdown (%)", fontsize=12)
        ax2.set_ylabel("Frequency", fontsize=12)
        ax2.set_title("Drawdown Distribution", fontsize=12, fontweight="bold")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Underwater plot
        ax3 = fig.add_subplot(gs[1, 1])
        underwater = (portfolio_values / running_max - 1) * 100
        ax3.fill_between(underwater.index, 0, underwater.values, alpha=0.5, color="red")
        ax3.set_ylabel("Underwater (%)", fontsize=12)
        ax3.set_xlabel("Date", fontsize=12)
        ax3.set_title("Underwater Plot (Recovery from Peak)", fontsize=12, fontweight="bold")
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
        else:
            plt.show()

    def plot_returns_distribution(self, save_path: Optional[str] = None):
        """Plot returns distribution analysis"""
        fig = plt.figure(figsize=(16, 10))
        gs = GridSpec(2, 2, figure=fig)

        daily_returns = self.result.daily_returns.dropna() * 100

        # Daily returns histogram with normal distribution overlay
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.hist(daily_returns.values, bins=50, alpha=0.7, color="blue", edgecolor="black", density=True)

        # Overlay normal distribution
        mu, sigma = daily_returns.mean(), daily_returns.std()
        x = np.linspace(daily_returns.min(), daily_returns.max(), 100)
        ax1.plot(x, 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(-0.5 * ((x - mu) / sigma) ** 2), "r-", linewidth=2, label="Normal Distribution")

        ax1.axvline(x=0, color="gray", linestyle="--", alpha=0.5)
        ax1.set_xlabel("Daily Return (%)", fontsize=12)
        ax1.set_ylabel("Density", fontsize=12)
        ax1.set_title("Daily Returns Distribution", fontsize=12, fontweight="bold")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Q-Q plot
        ax2 = fig.add_subplot(gs[0, 1])
        from scipy import stats
        stats.probplot(daily_returns.values, dist="norm", plot=ax2)
        ax2.set_title("Q-Q Plot (Normality Test)", fontsize=12, fontweight="bold")
        ax2.grid(True, alpha=0.3)

        # Returns over time
        ax3 = fig.add_subplot(gs[1, :])
        colors = ["red" if x < 0 else "green" for x in daily_returns.values]
        ax3.bar(daily_returns.index, daily_returns.values, color=colors, alpha=0.6, width=1)
        ax3.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)
        ax3.set_ylabel("Daily Return (%)", fontsize=12)
        ax3.set_xlabel("Date", fontsize=12)
        ax3.set_title("Daily Returns Over Time", fontsize=12, fontweight="bold")
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
        else:
            plt.show()

    def plot_monthly_returns(self, save_path: Optional[str] = None):
        """Plot monthly returns heatmap"""
        fig, ax = plt.subplots(figsize=(16, 8))

        # Calculate monthly returns
        portfolio_values = self.result.portfolio_values
        monthly_returns = portfolio_values.resample("M").last().pct_change() * 100

        # Create pivot table for heatmap
        monthly_returns.index = pd.to_datetime(monthly_returns.index)
        monthly_data = pd.DataFrame(
            {
                "Year": monthly_returns.index.year,
                "Month": monthly_returns.index.month,
                "Return": monthly_returns.values,
            }
        )

        pivot_table = monthly_data.pivot(index="Month", columns="Year", values="Return")

        # Month names
        month_names = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
        pivot_table.index = [month_names[i - 1] for i in pivot_table.index]

        # Create heatmap
        sns.heatmap(
            pivot_table,
            annot=True,
            fmt=".1f",
            cmap="RdYlGn",
            center=0,
            cbar_kws={"label": "Return (%)"},
            linewidths=0.5,
            ax=ax,
        )

        ax.set_title("Monthly Returns Heatmap", fontsize=14, fontweight="bold")
        ax.set_xlabel("Year", fontsize=12)
        ax.set_ylabel("Month", fontsize=12)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
        else:
            plt.show()

    def plot_rolling_metrics(self, save_path: Optional[str] = None):
        """Plot rolling performance metrics"""
        fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)

        daily_returns = self.result.daily_returns.dropna()

        # Rolling Sharpe ratio (252-day)
        rolling_mean = daily_returns.rolling(window=252).mean() * 252 * 100
        rolling_std = daily_returns.rolling(window=252).std() * np.sqrt(252) * 100
        rolling_sharpe = rolling_mean / rolling_std

        axes[0].plot(rolling_sharpe.index, rolling_sharpe.values, linewidth=2, color="blue")
        axes[0].axhline(y=0, color="gray", linestyle="--", alpha=0.5)
        axes[0].axhline(
            y=self.metrics.sharpe_ratio,
            color="red",
            linestyle="--",
            alpha=0.5,
            label=f"Overall: {self.metrics.sharpe_ratio:.2f}",
        )
        axes[0].set_ylabel("Sharpe Ratio", fontsize=12)
        axes[0].set_title("Rolling 1-Year Sharpe Ratio", fontsize=12, fontweight="bold")
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Rolling volatility (63-day ~ 3 months)
        rolling_vol = daily_returns.rolling(window=63).std() * np.sqrt(252) * 100
        axes[1].plot(rolling_vol.index, rolling_vol.values, linewidth=2, color="orange")
        axes[1].axhline(
            y=self.metrics.volatility,
            color="red",
            linestyle="--",
            alpha=0.5,
            label=f"Overall: {self.metrics.volatility:.2f}%",
        )
        axes[1].set_ylabel("Volatility (%)", fontsize=12)
        axes[1].set_title("Rolling 3-Month Volatility", fontsize=12, fontweight="bold")
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        # Rolling returns (252-day)
        rolling_return = daily_returns.rolling(window=252).apply(lambda x: (1 + x).prod() - 1) * 100
        axes[2].plot(rolling_return.index, rolling_return.values, linewidth=2, color="green")
        axes[2].axhline(y=0, color="gray", linestyle="--", alpha=0.5)
        axes[2].set_ylabel("Return (%)", fontsize=12)
        axes[2].set_xlabel("Date", fontsize=12)
        axes[2].set_title("Rolling 1-Year Return", fontsize=12, fontweight="bold")
        axes[2].grid(True, alpha=0.3)

        # Format x-axis
        axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.setp(axes[2].xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
        else:
            plt.show()

    def _generate_html_report(self, output_path: Path, include_charts: bool) -> str:
        """Generate HTML report"""
        m = self.metrics

        # Chart HTML
        chart_html = ""
        if include_charts:
            chart_html = f"""
            <h2>Performance Charts</h2>
            <div class="chart">
                <h3>Portfolio Performance</h3>
                <img src="portfolio_performance.png" alt="Portfolio Performance" style="width:100%">
            </div>
            <div class="chart">
                <h3>Drawdown Analysis</h3>
                <img src="drawdown_analysis.png" alt="Drawdown Analysis" style="width:100%">
            </div>
            <div class="chart">
                <h3>Returns Distribution</h3>
                <img src="returns_distribution.png" alt="Returns Distribution" style="width:100%">
            </div>
            <div class="chart">
                <h3>Monthly Returns</h3>
                <img src="monthly_returns.png" alt="Monthly Returns" style="width:100%">
            </div>
            <div class="chart">
                <h3>Rolling Metrics</h3>
                <img src="rolling_metrics.png" alt="Rolling Metrics" style="width:100%">
            </div>
            """

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Backtest Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: auto; background-color: white; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px; }}
        h3 {{ color: #7f8c8d; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-box {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db; }}
        .metric-box h3 {{ margin-top: 0; color: #2c3e50; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ font-size: 14px; color: #7f8c8d; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #34495e; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .chart {{ margin: 30px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Backtest Performance Report</h1>
        <p><strong>Period:</strong> {m.start_date.date()} to {m.end_date.date()} ({m.trading_days} trading days)</p>
        <p><strong>Initial Capital:</strong> {m.initial_capital:,.0f} KRW</p>
        <p><strong>Final Portfolio Value:</strong> {m.final_portfolio_value:,.0f} KRW</p>

        <h2>Summary Metrics</h2>
        <div class="metrics">
            <div class="metric-box">
                <h3>Total Return</h3>
                <div class="metric-value {'positive' if m.total_return > 0 else 'negative'}">{m.total_return:.2f}%</div>
            </div>
            <div class="metric-box">
                <h3>Annualized Return (CAGR)</h3>
                <div class="metric-value {'positive' if m.cagr > 0 else 'negative'}">{m.cagr:.2f}%</div>
            </div>
            <div class="metric-box">
                <h3>Sharpe Ratio</h3>
                <div class="metric-value">{m.sharpe_ratio:.2f}</div>
            </div>
            <div class="metric-box">
                <h3>Max Drawdown</h3>
                <div class="metric-value negative">-{m.max_drawdown:.2f}%</div>
            </div>
            <div class="metric-box">
                <h3>Win Rate</h3>
                <div class="metric-value">{m.win_rate:.2f}%</div>
            </div>
            <div class="metric-box">
                <h3>Profit Factor</h3>
                <div class="metric-value">{m.profit_factor:.2f}</div>
            </div>
        </div>

        <h2>Performance Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Return</td><td class="{'positive' if m.total_return > 0 else 'negative'}">{m.total_return:.2f}%</td></tr>
            <tr><td>Annualized Return</td><td class="{'positive' if m.annualized_return > 0 else 'negative'}">{m.annualized_return:.2f}%</td></tr>
            <tr><td>CAGR</td><td class="{'positive' if m.cagr > 0 else 'negative'}">{m.cagr:.2f}%</td></tr>
            <tr><td>Volatility (Annualized)</td><td>{m.volatility:.2f}%</td></tr>
            <tr><td>Sharpe Ratio</td><td>{m.sharpe_ratio:.2f}</td></tr>
            <tr><td>Sortino Ratio</td><td>{m.sortino_ratio:.2f}</td></tr>
            <tr><td>Calmar Ratio</td><td>{m.calmar_ratio:.2f}</td></tr>
            <tr><td>Maximum Drawdown</td><td class="negative">-{m.max_drawdown:.2f}%</td></tr>
            <tr><td>Max Drawdown Duration</td><td>{m.max_drawdown_duration} days</td></tr>
            <tr><td>Value at Risk (95%)</td><td class="negative">{m.value_at_risk_95:.2f}%</td></tr>
            <tr><td>Conditional VaR (95%)</td><td class="negative">{m.conditional_var_95:.2f}%</td></tr>
            <tr><td>Ulcer Index</td><td>{m.ulcer_index:.2f}</td></tr>
        </table>

        <h2>Trading Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Trades</td><td>{m.total_trades}</td></tr>
            <tr><td>Winning Trades</td><td class="positive">{m.winning_trades}</td></tr>
            <tr><td>Losing Trades</td><td class="negative">{m.losing_trades}</td></tr>
            <tr><td>Win Rate</td><td>{m.win_rate:.2f}%</td></tr>
            <tr><td>Profit Factor</td><td>{m.profit_factor:.2f}</td></tr>
            <tr><td>Average Win</td><td class="positive">{m.avg_win:.2f}%</td></tr>
            <tr><td>Average Loss</td><td class="negative">{m.avg_loss:.2f}%</td></tr>
            <tr><td>Average Trade</td><td class="{'positive' if m.avg_trade > 0 else 'negative'}">{m.avg_trade:.2f}%</td></tr>
            <tr><td>Best Trade</td><td class="positive">{m.best_trade:.2f}%</td></tr>
            <tr><td>Worst Trade</td><td class="negative">{m.worst_trade:.2f}%</td></tr>
            <tr><td>Average Holding Period</td><td>{m.avg_holding_period:.1f} days</td></tr>
            <tr><td>Max Holding Period</td><td>{m.max_holding_period} days</td></tr>
            <tr><td>Min Holding Period</td><td>{m.min_holding_period} days</td></tr>
        </table>

        <h2>Cost Analysis</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Fees</td><td>{m.total_fees:,.0f} KRW</td></tr>
            <tr><td>Total Commission</td><td>{m.total_commission:,.0f} KRW</td></tr>
            <tr><td>Total Tax</td><td>{m.total_tax:,.0f} KRW</td></tr>
            <tr><td>Fees as % of Initial Capital</td><td>{(m.total_fees / m.initial_capital * 100):.2f}%</td></tr>
        </table>

        <h2>Monthly Performance</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Best Month</td><td class="positive">{m.best_month:.2f}%</td></tr>
            <tr><td>Worst Month</td><td class="negative">{m.worst_month:.2f}%</td></tr>
            <tr><td>Positive Months</td><td>{m.positive_months}</td></tr>
            <tr><td>Total Months</td><td>{m.total_months}</td></tr>
            <tr><td>Positive Month Rate</td><td>{(m.positive_months / m.total_months * 100 if m.total_months > 0 else 0):.2f}%</td></tr>
        </table>

        {chart_html}

        <hr style="margin-top: 50px;">
        <p style="text-align: center; color: #7f8c8d; font-size: 12px;">
            Generated by Ko-Stock-Filter Backtesting Framework
        </p>
    </div>
</body>
</html>
        """

        return html

    def _export_data(self, output_path: Path):
        """Export data to CSV files"""
        # Export trades
        if not self.result.trades.empty:
            self.result.trades.to_csv(output_path / "trades.csv", index=False)

        # Export daily portfolio values
        self.result.portfolio_values.to_csv(output_path / "portfolio_values.csv")

        # Export metrics
        metrics_df = pd.DataFrame([self.metrics.to_dict()])
        metrics_df.to_csv(output_path / "metrics.csv", index=False)

        # Export positions
        if not self.result.positions.empty:
            self.result.positions.to_csv(output_path / "positions.csv", index=False)
