"""
Parameter Optimizer

Tests and compares different strategy parameter combinations to find optimal settings.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from .backtesting_engine import BacktestingEngine, BacktestConfig, BacktestResult
from .performance_metrics import PerformanceMetrics


@dataclass
class ParameterSet:
    """A set of parameters to test"""

    name: str
    parameters: Dict[str, Any]
    description: Optional[str] = None


class ParameterOptimizer:
    """
    Optimize strategy parameters through systematic testing

    Tests multiple parameter combinations and compares results.
    """

    def __init__(self, base_config: BacktestConfig):
        """
        Initialize parameter optimizer

        Args:
            base_config: Base configuration to modify
        """
        self.base_config = base_config
        self.results: List[tuple[ParameterSet, BacktestResult]] = []

    def add_parameter_set(self, param_set: ParameterSet):
        """
        Add a parameter set to test

        Args:
            param_set: Parameter set to test
        """
        # Validate parameters exist in config
        for param_name in param_set.parameters.keys():
            if not hasattr(self.base_config, param_name):
                raise ValueError(f"Invalid parameter: {param_name}")

    def grid_search(
        self,
        parameter_ranges: Dict[str, List[Any]],
        optimization_metric: str = "sharpe_ratio",
        max_workers: int = 4,
    ) -> pd.DataFrame:
        """
        Perform grid search over parameter ranges

        Args:
            parameter_ranges: Dictionary mapping parameter names to lists of values to test
                             e.g., {"stop_loss_pct": [0.05, 0.10, 0.15],
                                   "min_composite_score": [55, 60, 65]}
            optimization_metric: Metric to optimize (default: sharpe_ratio)
            max_workers: Number of parallel workers

        Returns:
            DataFrame with results sorted by optimization metric
        """
        print(f"Starting grid search over {len(parameter_ranges)} parameters...")

        # Generate all combinations
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())
        combinations = list(product(*param_values))

        print(f"Testing {len(combinations)} parameter combinations...")

        # Create parameter sets
        parameter_sets = []
        for i, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))
            param_set = ParameterSet(
                name=f"Config_{i+1}",
                parameters=params,
                description=", ".join([f"{k}={v}" for k, v in params.items()]),
            )
            parameter_sets.append(param_set)

        # Run backtests
        results = self.run_parameter_tests(parameter_sets, max_workers=max_workers)

        # Sort by optimization metric
        results = results.sort_values(optimization_metric, ascending=False)

        return results

    def run_parameter_tests(
        self, parameter_sets: List[ParameterSet], max_workers: int = 4
    ) -> pd.DataFrame:
        """
        Run backtests for multiple parameter sets

        Args:
            parameter_sets: List of parameter sets to test
            max_workers: Number of parallel workers

        Returns:
            DataFrame comparing results
        """
        print(f"Running {len(parameter_sets)} parameter tests...")

        results_data = []

        # Run tests sequentially or in parallel
        if max_workers > 1:
            # Parallel execution
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._run_single_test, param_set): param_set
                    for param_set in parameter_sets
                }

                for i, future in enumerate(as_completed(futures)):
                    param_set = futures[future]
                    try:
                        result = future.result()
                        results_data.append(self._extract_result_data(param_set, result))
                        print(
                            f"  Completed {i+1}/{len(parameter_sets)}: {param_set.name} - "
                            f"Return: {result.metrics.total_return:.2f}%, "
                            f"Sharpe: {result.metrics.sharpe_ratio:.2f}"
                        )
                    except Exception as e:
                        print(f"  Error testing {param_set.name}: {e}")
        else:
            # Sequential execution
            for i, param_set in enumerate(parameter_sets):
                try:
                    result = self._run_single_test(param_set)
                    results_data.append(self._extract_result_data(param_set, result))
                    print(
                        f"  Completed {i+1}/{len(parameter_sets)}: {param_set.name} - "
                        f"Return: {result.metrics.total_return:.2f}%, "
                        f"Sharpe: {result.metrics.sharpe_ratio:.2f}"
                    )
                    self.results.append((param_set, result))
                except Exception as e:
                    print(f"  Error testing {param_set.name}: {e}")

        # Create comparison DataFrame
        df = pd.DataFrame(results_data)

        return df

    def _run_single_test(self, param_set: ParameterSet) -> BacktestResult:
        """Run a single backtest with given parameters"""
        # Create modified config
        config = BacktestConfig(
            start_date=self.base_config.start_date,
            end_date=self.base_config.end_date,
            initial_capital=self.base_config.initial_capital,
            max_positions=self.base_config.max_positions,
            max_position_size=self.base_config.max_position_size,
            min_composite_score=self.base_config.min_composite_score,
            min_momentum_score=self.base_config.min_momentum_score,
            min_quality_score=self.base_config.min_quality_score,
            stop_loss_pct=self.base_config.stop_loss_pct,
            take_profit_pct=self.base_config.take_profit_pct,
            trailing_stop_pct=self.base_config.trailing_stop_pct,
            quality_exit_threshold=self.base_config.quality_exit_threshold,
            score_deterioration_threshold=self.base_config.score_deterioration_threshold,
            position_sizing_method=self.base_config.position_sizing_method,
            kelly_fraction=self.base_config.kelly_fraction,
            commission_rate=self.base_config.commission_rate,
            slippage_bps=self.base_config.slippage_bps,
            markets=self.base_config.markets,
            sectors=self.base_config.sectors,
            min_volume=self.base_config.min_volume,
            min_price=self.base_config.min_price,
            rebalance_frequency=self.base_config.rebalance_frequency,
            max_sector_concentration=self.base_config.max_sector_concentration,
            max_correlation=self.base_config.max_correlation,
        )

        # Apply parameter overrides
        for param_name, param_value in param_set.parameters.items():
            setattr(config, param_name, param_value)

        # Run backtest
        engine = BacktestingEngine(config)
        result = engine.run()

        return result

    def _extract_result_data(
        self, param_set: ParameterSet, result: BacktestResult
    ) -> Dict:
        """Extract data from result for comparison"""
        m = result.metrics

        data = {
            "name": param_set.name,
            "description": param_set.description,
            # Returns
            "total_return": m.total_return,
            "annualized_return": m.annualized_return,
            "cagr": m.cagr,
            # Risk
            "volatility": m.volatility,
            "max_drawdown": m.max_drawdown,
            "max_drawdown_duration": m.max_drawdown_duration,
            # Risk-adjusted
            "sharpe_ratio": m.sharpe_ratio,
            "sortino_ratio": m.sortino_ratio,
            "calmar_ratio": m.calmar_ratio,
            # Trading
            "total_trades": m.total_trades,
            "win_rate": m.win_rate,
            "profit_factor": m.profit_factor,
            "avg_trade": m.avg_trade,
            # Portfolio
            "final_value": m.final_portfolio_value,
            "total_fees": m.total_fees,
        }

        # Add parameters
        for param_name, param_value in param_set.parameters.items():
            data[f"param_{param_name}"] = param_value

        return data

    def plot_parameter_comparison(
        self,
        results_df: pd.DataFrame,
        metrics: List[str] = None,
        save_path: Optional[str] = None,
    ):
        """
        Plot comparison of parameter test results

        Args:
            results_df: DataFrame from run_parameter_tests
            metrics: List of metrics to plot (default: key metrics)
            save_path: Path to save chart
        """
        if metrics is None:
            metrics = [
                "total_return",
                "sharpe_ratio",
                "max_drawdown",
                "win_rate",
                "profit_factor",
            ]

        n_metrics = len(metrics)
        fig, axes = plt.subplots(n_metrics, 1, figsize=(16, 4 * n_metrics))

        if n_metrics == 1:
            axes = [axes]

        for i, metric in enumerate(metrics):
            if metric in results_df.columns:
                ax = axes[i]
                results_df.plot(
                    x="name", y=metric, kind="bar", ax=ax, color="steelblue", legend=False
                )
                ax.set_title(f"{metric.replace('_', ' ').title()}", fontsize=14, fontweight="bold")
                ax.set_xlabel("Configuration", fontsize=12)
                ax.set_ylabel(metric.replace("_", " ").title(), fontsize=12)
                ax.grid(True, alpha=0.3, axis="y")
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
        else:
            plt.show()

    def plot_parameter_heatmap(
        self,
        results_df: pd.DataFrame,
        x_param: str,
        y_param: str,
        metric: str = "sharpe_ratio",
        save_path: Optional[str] = None,
    ):
        """
        Plot heatmap of metric across two parameters

        Args:
            results_df: DataFrame from run_parameter_tests
            x_param: Parameter for x-axis
            y_param: Parameter for y-axis
            metric: Metric to visualize
            save_path: Path to save chart
        """
        x_col = f"param_{x_param}"
        y_col = f"param_{y_param}"

        if x_col not in results_df.columns or y_col not in results_df.columns:
            raise ValueError(f"Parameters {x_param} or {y_param} not found in results")

        # Create pivot table
        pivot = results_df.pivot_table(
            values=metric, index=y_col, columns=x_col, aggfunc="mean"
        )

        # Plot heatmap
        fig, ax = plt.subplots(figsize=(12, 8))
        sns.heatmap(
            pivot,
            annot=True,
            fmt=".2f",
            cmap="RdYlGn",
            center=0 if metric == "max_drawdown" else None,
            cbar_kws={"label": metric.replace("_", " ").title()},
            linewidths=0.5,
            ax=ax,
        )

        ax.set_title(
            f"{metric.replace('_', ' ').title()} by {x_param} and {y_param}",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_xlabel(x_param.replace("_", " ").title(), fontsize=12)
        ax.set_ylabel(y_param.replace("_", " ").title(), fontsize=12)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
        else:
            plt.show()

    def plot_efficient_frontier(
        self,
        results_df: pd.DataFrame,
        save_path: Optional[str] = None,
    ):
        """
        Plot efficient frontier (return vs risk)

        Args:
            results_df: DataFrame from run_parameter_tests
            save_path: Path to save chart
        """
        fig, ax = plt.subplots(figsize=(12, 8))

        # Scatter plot of volatility vs return
        scatter = ax.scatter(
            results_df["volatility"],
            results_df["annualized_return"],
            s=100,
            c=results_df["sharpe_ratio"],
            cmap="RdYlGn",
            alpha=0.6,
            edgecolors="black",
            linewidth=1,
        )

        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label("Sharpe Ratio", fontsize=12)

        # Find and highlight best Sharpe ratio
        best_idx = results_df["sharpe_ratio"].idxmax()
        best_row = results_df.loc[best_idx]
        ax.scatter(
            best_row["volatility"],
            best_row["annualized_return"],
            s=300,
            marker="*",
            color="gold",
            edgecolors="black",
            linewidth=2,
            label="Best Sharpe Ratio",
            zorder=5,
        )

        # Labels and formatting
        ax.set_xlabel("Volatility (%)", fontsize=12)
        ax.set_ylabel("Annualized Return (%)", fontsize=12)
        ax.set_title("Efficient Frontier - Return vs Risk", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)

        # Add annotations for top performers
        top_n = min(5, len(results_df))
        top_results = results_df.nlargest(top_n, "sharpe_ratio")

        for idx, row in top_results.iterrows():
            ax.annotate(
                row["name"],
                (row["volatility"], row["annualized_return"]),
                xytext=(10, 10),
                textcoords="offset points",
                fontsize=8,
                alpha=0.7,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7),
            )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
        else:
            plt.show()

    def generate_optimization_report(
        self, results_df: pd.DataFrame, output_dir: str = "optimization_reports"
    ) -> str:
        """
        Generate comprehensive optimization report

        Args:
            results_df: DataFrame from run_parameter_tests
            output_dir: Directory to save report

        Returns:
            Path to report HTML file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate charts
        self.plot_parameter_comparison(
            results_df, save_path=str(output_path / "parameter_comparison.png")
        )
        self.plot_efficient_frontier(
            results_df, save_path=str(output_path / "efficient_frontier.png")
        )

        # Generate HTML report
        html = self._generate_optimization_html(results_df, output_path)

        report_file = output_path / "optimization_report.html"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html)

        # Export CSV
        results_df.to_csv(output_path / "optimization_results.csv", index=False)

        return str(report_file)

    def _generate_optimization_html(
        self, results_df: pd.DataFrame, output_path: Path
    ) -> str:
        """Generate HTML optimization report"""
        # Find best configurations
        best_sharpe = results_df.loc[results_df["sharpe_ratio"].idxmax()]
        best_return = results_df.loc[results_df["total_return"].idxmax()]
        best_drawdown = results_df.loc[results_df["max_drawdown"].idxmin()]

        # Generate table HTML
        table_html = results_df.to_html(
            index=False,
            classes="table",
            float_format=lambda x: f"{x:.2f}",
            escape=False,
        )

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Parameter Optimization Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: auto; background-color: white; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px; }}
        .highlight-box {{ background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #3498db; }}
        .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 12px; }}
        .table th, .table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        .table th {{ background-color: #34495e; color: white; }}
        .table tr:hover {{ background-color: #f5f5f5; }}
        .chart {{ margin: 30px 0; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Parameter Optimization Report</h1>
        <p><strong>Total Configurations Tested:</strong> {len(results_df)}</p>

        <h2>Best Configurations</h2>

        <div class="highlight-box">
            <h3>Best Sharpe Ratio: {best_sharpe['sharpe_ratio']:.2f}</h3>
            <p><strong>Configuration:</strong> {best_sharpe['name']}</p>
            <p><strong>Description:</strong> {best_sharpe['description']}</p>
            <p><strong>Return:</strong> <span class="positive">{best_sharpe['total_return']:.2f}%</span></p>
            <p><strong>Max Drawdown:</strong> <span class="negative">-{best_sharpe['max_drawdown']:.2f}%</span></p>
            <p><strong>Win Rate:</strong> {best_sharpe['win_rate']:.2f}%</p>
        </div>

        <div class="highlight-box">
            <h3>Best Total Return: {best_return['total_return']:.2f}%</h3>
            <p><strong>Configuration:</strong> {best_return['name']}</p>
            <p><strong>Description:</strong> {best_return['description']}</p>
            <p><strong>Sharpe Ratio:</strong> {best_return['sharpe_ratio']:.2f}</p>
            <p><strong>Max Drawdown:</strong> <span class="negative">-{best_return['max_drawdown']:.2f}%</span></p>
            <p><strong>Win Rate:</strong> {best_return['win_rate']:.2f}%</p>
        </div>

        <div class="highlight-box">
            <h3>Lowest Drawdown: {best_drawdown['max_drawdown']:.2f}%</h3>
            <p><strong>Configuration:</strong> {best_drawdown['name']}</p>
            <p><strong>Description:</strong> {best_drawdown['description']}</p>
            <p><strong>Return:</strong> <span class="positive">{best_drawdown['total_return']:.2f}%</span></p>
            <p><strong>Sharpe Ratio:</strong> {best_drawdown['sharpe_ratio']:.2f}</p>
            <p><strong>Win Rate:</strong> {best_drawdown['win_rate']:.2f}%</p>
        </div>

        <h2>Performance Charts</h2>
        <div class="chart">
            <img src="efficient_frontier.png" alt="Efficient Frontier" style="width:100%">
        </div>
        <div class="chart">
            <img src="parameter_comparison.png" alt="Parameter Comparison" style="width:100%">
        </div>

        <h2>All Results</h2>
        {table_html}

        <hr style="margin-top: 50px;">
        <p style="text-align: center; color: #7f8c8d; font-size: 12px;">
            Generated by Ko-Stock-Filter Parameter Optimizer
        </p>
    </div>
</body>
</html>
        """

        return html
