"""
Parameter Optimization Example

Demonstrates how to use the parameter optimizer to find optimal strategy settings.

Usage:
    python examples/parameter_optimization_example.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.backtesting import (
    BacktestConfig,
    ParameterOptimizer,
    ParameterSet,
)


def optimize_entry_exit_parameters():
    """Optimize entry and exit parameters"""
    print("=" * 80)
    print("Optimizing Entry/Exit Parameters")
    print("=" * 80)

    # Base configuration
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    base_config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000_000,
        max_positions=20,
        max_position_size=0.10,
        position_sizing_method="equal",
        markets=["KOSPI", "KOSDAQ"],
    )

    # Create optimizer
    optimizer = ParameterOptimizer(base_config)

    # Define parameter ranges to test
    parameter_ranges = {
        "min_composite_score": [55.0, 60.0, 65.0, 70.0],
        "stop_loss_pct": [0.05, 0.07, 0.10, 0.12],
        "take_profit_pct": [0.15, 0.20, 0.25, 0.30],
    }

    # Run grid search
    print(f"\nTesting {4 * 4 * 4} = 64 combinations...")
    results = optimizer.grid_search(
        parameter_ranges,
        optimization_metric="sharpe_ratio",
        max_workers=1,  # Use 1 for sequential, increase for parallel
    )

    # Display top 10 results
    print("\n" + "=" * 80)
    print("Top 10 Configurations by Sharpe Ratio")
    print("=" * 80)
    print(results.head(10).to_string())

    # Generate optimization report
    print("\n\nGenerating optimization report...")
    report_path = optimizer.generate_optimization_report(
        results, output_dir="optimization_reports/entry_exit"
    )
    print(f"Report saved to: {report_path}")

    # Plot parameter heatmap
    print("\nGenerating parameter heatmap...")
    optimizer.plot_parameter_heatmap(
        results,
        x_param="stop_loss_pct",
        y_param="take_profit_pct",
        metric="sharpe_ratio",
        save_path="optimization_reports/entry_exit/stop_take_profit_heatmap.png",
    )
    print("Heatmap saved!")

    return results


def optimize_position_sizing():
    """Optimize position sizing parameters"""
    print("\n")
    print("=" * 80)
    print("Optimizing Position Sizing Parameters")
    print("=" * 80)

    # Base configuration
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    base_config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000_000,
        min_composite_score=60.0,
        stop_loss_pct=0.10,
        take_profit_pct=0.20,
        position_sizing_method="equal",
        markets=["KOSPI", "KOSDAQ"],
    )

    # Create optimizer
    optimizer = ParameterOptimizer(base_config)

    # Define parameter ranges
    parameter_ranges = {
        "max_positions": [10, 15, 20, 25, 30],
        "max_position_size": [0.05, 0.07, 0.10, 0.12, 0.15],
    }

    # Run grid search
    results = optimizer.grid_search(
        parameter_ranges,
        optimization_metric="sharpe_ratio",
        max_workers=1,
    )

    # Display top 10 results
    print("\n" + "=" * 80)
    print("Top 10 Configurations by Sharpe Ratio")
    print("=" * 80)
    print(results.head(10).to_string())

    # Generate optimization report
    print("\n\nGenerating optimization report...")
    report_path = optimizer.generate_optimization_report(
        results, output_dir="optimization_reports/position_sizing"
    )
    print(f"Report saved to: {report_path}")

    # Plot parameter heatmap
    print("\nGenerating parameter heatmap...")
    optimizer.plot_parameter_heatmap(
        results,
        x_param="max_positions",
        y_param="max_position_size",
        metric="sharpe_ratio",
        save_path="optimization_reports/position_sizing/position_heatmap.png",
    )
    print("Heatmap saved!")

    return results


def compare_manual_parameter_sets():
    """Compare manually defined parameter sets"""
    print("\n")
    print("=" * 80)
    print("Comparing Manual Parameter Sets")
    print("=" * 80)

    # Base configuration
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    base_config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000_000,
        markets=["KOSPI", "KOSDAQ"],
    )

    # Create optimizer
    optimizer = ParameterOptimizer(base_config)

    # Define parameter sets to test
    parameter_sets = [
        ParameterSet(
            name="Ultra Conservative",
            parameters={
                "min_composite_score": 75.0,
                "min_momentum_score": 65.0,
                "min_quality_score": 60.0,
                "stop_loss_pct": 0.05,
                "take_profit_pct": 0.15,
                "max_positions": 10,
                "max_position_size": 0.07,
            },
            description="Very strict entry, tight stops, small positions",
        ),
        ParameterSet(
            name="Conservative",
            parameters={
                "min_composite_score": 70.0,
                "min_momentum_score": 60.0,
                "min_quality_score": 50.0,
                "stop_loss_pct": 0.07,
                "take_profit_pct": 0.18,
                "max_positions": 15,
                "max_position_size": 0.08,
            },
            description="Strict entry, moderate stops, medium positions",
        ),
        ParameterSet(
            name="Balanced",
            parameters={
                "min_composite_score": 60.0,
                "min_momentum_score": 50.0,
                "min_quality_score": 40.0,
                "stop_loss_pct": 0.10,
                "take_profit_pct": 0.20,
                "max_positions": 20,
                "max_position_size": 0.10,
            },
            description="Balanced approach with moderate risk",
        ),
        ParameterSet(
            name="Aggressive",
            parameters={
                "min_composite_score": 55.0,
                "min_momentum_score": 45.0,
                "min_quality_score": 35.0,
                "stop_loss_pct": 0.12,
                "take_profit_pct": 0.25,
                "max_positions": 25,
                "max_position_size": 0.12,
            },
            description="Looser entry, wider stops, larger positions",
        ),
        ParameterSet(
            name="Ultra Aggressive",
            parameters={
                "min_composite_score": 50.0,
                "min_momentum_score": 40.0,
                "min_quality_score": 30.0,
                "stop_loss_pct": 0.15,
                "take_profit_pct": 0.30,
                "max_positions": 30,
                "max_position_size": 0.15,
            },
            description="Very loose entry, wide stops, large positions",
        ),
    ]

    # Run tests
    results = optimizer.run_parameter_tests(parameter_sets, max_workers=1)

    # Display results
    print("\n" + "=" * 80)
    print("Comparison Results")
    print("=" * 80)
    print(results.to_string())

    # Generate report
    print("\n\nGenerating comparison report...")
    report_path = optimizer.generate_optimization_report(
        results, output_dir="optimization_reports/manual_comparison"
    )
    print(f"Report saved to: {report_path}")

    return results


def find_best_composite_score_threshold():
    """Find optimal composite score threshold"""
    print("\n")
    print("=" * 80)
    print("Finding Optimal Composite Score Threshold")
    print("=" * 80)

    # Base configuration
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years

    base_config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000_000,
        max_positions=20,
        max_position_size=0.10,
        stop_loss_pct=0.10,
        take_profit_pct=0.20,
        position_sizing_method="equal",
        markets=["KOSPI", "KOSDAQ"],
    )

    # Create optimizer
    optimizer = ParameterOptimizer(base_config)

    # Test different composite score thresholds
    parameter_ranges = {
        "min_composite_score": [50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0],
        "min_momentum_score": [40.0, 45.0, 50.0, 55.0, 60.0],
    }

    # Run grid search
    results = optimizer.grid_search(
        parameter_ranges,
        optimization_metric="sharpe_ratio",
        max_workers=1,
    )

    # Display top 10 results
    print("\n" + "=" * 80)
    print("Top 10 Score Thresholds by Sharpe Ratio")
    print("=" * 80)
    print(results.head(10).to_string())

    # Generate report
    print("\n\nGenerating optimization report...")
    report_path = optimizer.generate_optimization_report(
        results, output_dir="optimization_reports/score_threshold"
    )
    print(f"Report saved to: {report_path}")

    # Plot heatmap
    print("\nGenerating score threshold heatmap...")
    optimizer.plot_parameter_heatmap(
        results,
        x_param="min_composite_score",
        y_param="min_momentum_score",
        metric="sharpe_ratio",
        save_path="optimization_reports/score_threshold/score_heatmap.png",
    )
    print("Heatmap saved!")

    return results


def main():
    """Main function"""
    print("\n" + "=" * 80)
    print("Ko-Stock-Filter Parameter Optimization")
    print("=" * 80)

    # Menu
    print("\nSelect optimization to run:")
    print("1. Optimize Entry/Exit Parameters")
    print("2. Optimize Position Sizing")
    print("3. Compare Manual Parameter Sets")
    print("4. Find Best Composite Score Threshold")
    print("0. Exit")

    choice = input("\nEnter your choice (0-4): ").strip()

    if choice == "1":
        optimize_entry_exit_parameters()
    elif choice == "2":
        optimize_position_sizing()
    elif choice == "3":
        compare_manual_parameter_sets()
    elif choice == "4":
        find_best_composite_score_threshold()
    elif choice == "0":
        print("Exiting...")
        return
    else:
        print("Invalid choice. Please try again.")
        return

    print("\nOptimization complete!")


if __name__ == "__main__":
    main()
