"""
Backtesting Framework for Trading Strategy Evaluation

This module provides comprehensive backtesting capabilities including:
- Historical data loading from database
- Vectorized backtesting engine for speed
- Performance metrics calculation (Sharpe ratio, max drawdown, win rate)
- Performance reporting with charts
- Parameter optimization and comparison
"""

from .data_loader import BacktestDataLoader
from .backtesting_engine import BacktestingEngine, BacktestConfig, BacktestResult
from .performance_metrics import PerformanceMetrics, MetricsCalculator
from .report_generator import ReportGenerator
from .parameter_optimizer import ParameterOptimizer, ParameterSet

__all__ = [
    "BacktestDataLoader",
    "BacktestingEngine",
    "BacktestConfig",
    "BacktestResult",
    "PerformanceMetrics",
    "MetricsCalculator",
    "ReportGenerator",
    "ParameterOptimizer",
    "ParameterSet",
]
