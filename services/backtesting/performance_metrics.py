"""
Performance Metrics Calculator for Backtesting

Calculates comprehensive performance metrics including:
- Sharpe ratio
- Sortino ratio
- Maximum drawdown
- Win rate and profit factor
- Risk-adjusted returns
- And more...
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import numpy as np


@dataclass
class PerformanceMetrics:
    """Container for backtesting performance metrics"""

    # Return Metrics
    total_return: float  # Total return (%)
    annualized_return: float  # Annualized return (%)
    cagr: float  # Compound Annual Growth Rate (%)

    # Risk Metrics
    volatility: float  # Annualized volatility (%)
    max_drawdown: float  # Maximum drawdown (%)
    max_drawdown_duration: int  # Max drawdown duration in days
    sharpe_ratio: float  # Sharpe ratio (risk-free rate = 0)
    sortino_ratio: float  # Sortino ratio (downside deviation)
    calmar_ratio: float  # Calmar ratio (return / max drawdown)

    # Trade Metrics
    total_trades: int  # Total number of trades
    winning_trades: int  # Number of winning trades
    losing_trades: int  # Number of losing trades
    win_rate: float  # Win rate (%)
    profit_factor: float  # Gross profit / gross loss

    # Trade Performance
    avg_win: float  # Average winning trade (%)
    avg_loss: float  # Average losing trade (%)
    avg_trade: float  # Average trade return (%)
    best_trade: float  # Best trade (%)
    worst_trade: float  # Worst trade (%)

    # Time Metrics
    avg_holding_period: float  # Average holding period (days)
    max_holding_period: int  # Maximum holding period (days)
    min_holding_period: int  # Minimum holding period (days)

    # Portfolio Metrics
    final_portfolio_value: float  # Final portfolio value
    initial_capital: float  # Initial capital
    total_fees: float  # Total fees paid (commission + tax)
    total_commission: float  # Total commission paid
    total_tax: float  # Total tax paid

    # Risk-Adjusted Metrics
    value_at_risk_95: float  # 95% Value at Risk
    conditional_var_95: float  # 95% Conditional VaR (Expected Shortfall)
    ulcer_index: float  # Ulcer Index (drawdown pain measure)

    # Period Metrics
    best_month: float  # Best monthly return (%)
    worst_month: float  # Worst monthly return (%)
    positive_months: int  # Number of positive months
    total_months: int  # Total number of months

    # Additional Info
    start_date: datetime
    end_date: datetime
    trading_days: int

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary"""
        return {
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "cagr": self.cagr,
            "volatility": self.volatility,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_duration": self.max_drawdown_duration,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "avg_trade": self.avg_trade,
            "best_trade": self.best_trade,
            "worst_trade": self.worst_trade,
            "avg_holding_period": self.avg_holding_period,
            "max_holding_period": self.max_holding_period,
            "min_holding_period": self.min_holding_period,
            "final_portfolio_value": self.final_portfolio_value,
            "initial_capital": self.initial_capital,
            "total_fees": self.total_fees,
            "total_commission": self.total_commission,
            "total_tax": self.total_tax,
            "value_at_risk_95": self.value_at_risk_95,
            "conditional_var_95": self.conditional_var_95,
            "ulcer_index": self.ulcer_index,
            "best_month": self.best_month,
            "worst_month": self.worst_month,
            "positive_months": self.positive_months,
            "total_months": self.total_months,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "trading_days": self.trading_days,
        }


class MetricsCalculator:
    """Calculate performance metrics from backtest results"""

    @staticmethod
    def calculate_metrics(
        portfolio_values: pd.Series,
        trades: pd.DataFrame,
        initial_capital: float,
        risk_free_rate: float = 0.0,
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics

        Args:
            portfolio_values: Series of portfolio values indexed by date
            trades: DataFrame with trade history
            initial_capital: Initial capital amount
            risk_free_rate: Annual risk-free rate (default 0.0)

        Returns:
            PerformanceMetrics object with all metrics
        """
        if len(portfolio_values) < 2:
            raise ValueError("Need at least 2 data points to calculate metrics")

        # Calculate returns
        returns = portfolio_values.pct_change().dropna()
        total_return = (
            (portfolio_values.iloc[-1] - initial_capital) / initial_capital * 100
        )

        # Time period
        start_date = portfolio_values.index[0]
        end_date = portfolio_values.index[-1]
        trading_days = len(portfolio_values)
        years = trading_days / 252  # Assuming 252 trading days per year

        # Annualized return
        if years > 0:
            cagr = (
                (portfolio_values.iloc[-1] / initial_capital) ** (1 / years) - 1
            ) * 100
            annualized_return = cagr
        else:
            cagr = 0.0
            annualized_return = 0.0

        # Volatility (annualized)
        if len(returns) > 1:
            volatility = returns.std() * np.sqrt(252) * 100
        else:
            volatility = 0.0

        # Drawdown analysis
        dd_metrics = MetricsCalculator._calculate_drawdown_metrics(portfolio_values)

        # Sharpe ratio
        if volatility > 0:
            sharpe_ratio = (annualized_return - risk_free_rate * 100) / volatility
        else:
            sharpe_ratio = 0.0

        # Sortino ratio (uses downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 1:
            downside_deviation = downside_returns.std() * np.sqrt(252) * 100
            if downside_deviation > 0:
                sortino_ratio = (
                    annualized_return - risk_free_rate * 100
                ) / downside_deviation
            else:
                sortino_ratio = 0.0
        else:
            sortino_ratio = 0.0

        # Calmar ratio
        if dd_metrics["max_drawdown"] > 0:
            calmar_ratio = annualized_return / dd_metrics["max_drawdown"]
        else:
            calmar_ratio = 0.0

        # Trade metrics
        trade_metrics = MetricsCalculator._calculate_trade_metrics(trades)

        # VaR and CVaR
        var_95 = MetricsCalculator._calculate_var(returns, 0.95)
        cvar_95 = MetricsCalculator._calculate_cvar(returns, 0.95)

        # Ulcer Index
        ulcer_index = MetricsCalculator._calculate_ulcer_index(portfolio_values)

        # Monthly metrics
        monthly_metrics = MetricsCalculator._calculate_monthly_metrics(
            portfolio_values
        )

        # Fee metrics
        fee_metrics = MetricsCalculator._calculate_fee_metrics(trades)

        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            cagr=cagr,
            volatility=volatility,
            max_drawdown=dd_metrics["max_drawdown"],
            max_drawdown_duration=dd_metrics["max_drawdown_duration"],
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            total_trades=trade_metrics["total_trades"],
            winning_trades=trade_metrics["winning_trades"],
            losing_trades=trade_metrics["losing_trades"],
            win_rate=trade_metrics["win_rate"],
            profit_factor=trade_metrics["profit_factor"],
            avg_win=trade_metrics["avg_win"],
            avg_loss=trade_metrics["avg_loss"],
            avg_trade=trade_metrics["avg_trade"],
            best_trade=trade_metrics["best_trade"],
            worst_trade=trade_metrics["worst_trade"],
            avg_holding_period=trade_metrics["avg_holding_period"],
            max_holding_period=trade_metrics["max_holding_period"],
            min_holding_period=trade_metrics["min_holding_period"],
            final_portfolio_value=portfolio_values.iloc[-1],
            initial_capital=initial_capital,
            total_fees=fee_metrics["total_fees"],
            total_commission=fee_metrics["total_commission"],
            total_tax=fee_metrics["total_tax"],
            value_at_risk_95=var_95,
            conditional_var_95=cvar_95,
            ulcer_index=ulcer_index,
            best_month=monthly_metrics["best_month"],
            worst_month=monthly_metrics["worst_month"],
            positive_months=monthly_metrics["positive_months"],
            total_months=monthly_metrics["total_months"],
            start_date=start_date,
            end_date=end_date,
            trading_days=trading_days,
        )

    @staticmethod
    def _calculate_drawdown_metrics(portfolio_values: pd.Series) -> Dict:
        """Calculate drawdown-related metrics"""
        # Calculate running maximum
        running_max = portfolio_values.expanding().max()

        # Calculate drawdown
        drawdown = (portfolio_values - running_max) / running_max * 100

        # Maximum drawdown
        max_drawdown = abs(drawdown.min())

        # Drawdown duration
        # Find periods of drawdown
        in_drawdown = drawdown < 0
        drawdown_periods = (in_drawdown != in_drawdown.shift()).cumsum()

        if in_drawdown.any():
            drawdown_durations = (
                in_drawdown.groupby(drawdown_periods).sum()[
                    in_drawdown.groupby(drawdown_periods).sum() > 0
                ]
            )
            max_drawdown_duration = int(drawdown_durations.max())
        else:
            max_drawdown_duration = 0

        return {
            "max_drawdown": max_drawdown,
            "max_drawdown_duration": max_drawdown_duration,
            "drawdown_series": drawdown,
        }

    @staticmethod
    def _calculate_trade_metrics(trades: pd.DataFrame) -> Dict:
        """Calculate trade-related metrics"""
        if trades.empty:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "avg_trade": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "avg_holding_period": 0.0,
                "max_holding_period": 0,
                "min_holding_period": 0,
            }

        # Filter for closed trades (must have both buy and sell)
        closed_trades = trades[trades["action"] == "SELL"].copy()

        if closed_trades.empty:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "avg_trade": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "avg_holding_period": 0.0,
                "max_holding_period": 0,
                "min_holding_period": 0,
            }

        # Calculate trade returns
        trade_returns = closed_trades["return_pct"].values
        winning_trades = trade_returns[trade_returns > 0]
        losing_trades = trade_returns[trade_returns < 0]

        total_trades = len(trade_returns)
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)

        win_rate = (num_wins / total_trades * 100) if total_trades > 0 else 0.0

        # Profit factor
        gross_profit = winning_trades.sum() if len(winning_trades) > 0 else 0.0
        gross_loss = abs(losing_trades.sum()) if len(losing_trades) > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

        # Average metrics
        avg_win = winning_trades.mean() if len(winning_trades) > 0 else 0.0
        avg_loss = losing_trades.mean() if len(losing_trades) > 0 else 0.0
        avg_trade = trade_returns.mean() if len(trade_returns) > 0 else 0.0

        best_trade = trade_returns.max() if len(trade_returns) > 0 else 0.0
        worst_trade = trade_returns.min() if len(trade_returns) > 0 else 0.0

        # Holding period
        if "holding_period" in closed_trades.columns:
            holding_periods = closed_trades["holding_period"].values
            avg_holding_period = (
                holding_periods.mean() if len(holding_periods) > 0 else 0.0
            )
            max_holding_period = (
                int(holding_periods.max()) if len(holding_periods) > 0 else 0
            )
            min_holding_period = (
                int(holding_periods.min()) if len(holding_periods) > 0 else 0
            )
        else:
            avg_holding_period = 0.0
            max_holding_period = 0
            min_holding_period = 0

        return {
            "total_trades": total_trades,
            "winning_trades": num_wins,
            "losing_trades": num_losses,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_trade": avg_trade,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "avg_holding_period": avg_holding_period,
            "max_holding_period": max_holding_period,
            "min_holding_period": min_holding_period,
        }

    @staticmethod
    def _calculate_var(returns: pd.Series, confidence: float) -> float:
        """Calculate Value at Risk"""
        if len(returns) < 2:
            return 0.0
        return float(np.percentile(returns, (1 - confidence) * 100) * 100)

    @staticmethod
    def _calculate_cvar(returns: pd.Series, confidence: float) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        if len(returns) < 2:
            return 0.0
        var = np.percentile(returns, (1 - confidence) * 100)
        return float(returns[returns <= var].mean() * 100)

    @staticmethod
    def _calculate_ulcer_index(portfolio_values: pd.Series) -> float:
        """
        Calculate Ulcer Index (measures depth and duration of drawdowns)
        """
        if len(portfolio_values) < 2:
            return 0.0

        running_max = portfolio_values.expanding().max()
        drawdown_pct = (portfolio_values - running_max) / running_max * 100
        ulcer_index = np.sqrt((drawdown_pct**2).mean())

        return float(ulcer_index)

    @staticmethod
    def _calculate_monthly_metrics(portfolio_values: pd.Series) -> Dict:
        """Calculate monthly return metrics"""
        # Resample to monthly
        monthly_values = portfolio_values.resample("M").last()

        if len(monthly_values) < 2:
            return {
                "best_month": 0.0,
                "worst_month": 0.0,
                "positive_months": 0,
                "total_months": 0,
            }

        monthly_returns = monthly_values.pct_change().dropna() * 100

        best_month = float(monthly_returns.max()) if len(monthly_returns) > 0 else 0.0
        worst_month = float(monthly_returns.min()) if len(monthly_returns) > 0 else 0.0
        positive_months = int((monthly_returns > 0).sum())
        total_months = len(monthly_returns)

        return {
            "best_month": best_month,
            "worst_month": worst_month,
            "positive_months": positive_months,
            "total_months": total_months,
        }

    @staticmethod
    def _calculate_fee_metrics(trades: pd.DataFrame) -> Dict:
        """Calculate fee-related metrics"""
        if trades.empty:
            return {
                "total_fees": 0.0,
                "total_commission": 0.0,
                "total_tax": 0.0,
            }

        total_commission = (
            trades["commission"].sum() if "commission" in trades.columns else 0.0
        )
        total_tax = trades["tax"].sum() if "tax" in trades.columns else 0.0
        total_fees = total_commission + total_tax

        return {
            "total_fees": total_fees,
            "total_commission": total_commission,
            "total_tax": total_tax,
        }
