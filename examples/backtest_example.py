"""
Backtesting Framework Example

Demonstrates how to use the backtesting framework to evaluate trading strategies.

Usage:
    python examples/backtest_example.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.backtesting import (
    BacktestConfig,
    BacktestingEngine,
    ReportGenerator,
)


def run_basic_backtest():
    """Run a basic backtest over the past 1 year"""
    print("=" * 80)
    print("Running Basic Backtest - 1 Year")
    print("=" * 80)

    # Define backtest period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # Create configuration
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000_000,  # 100M KRW
        max_positions=20,
        max_position_size=0.10,  # 10% per position
        # Entry criteria
        min_composite_score=60.0,
        min_momentum_score=50.0,
        min_quality_score=40.0,
        # Exit criteria
        stop_loss_pct=0.10,  # 10% stop loss
        take_profit_pct=0.20,  # 20% take profit
        trailing_stop_pct=0.08,  # 8% trailing stop
        # Position sizing
        position_sizing_method="equal",
        # Market filters
        markets=["KOSPI", "KOSDAQ"],
    )

    # Run backtest
    engine = BacktestingEngine(config)
    result = engine.run()

    # Print summary
    print("\n")
    print(result.summary())

    # Generate report
    print("\nGenerating performance report...")
    report_gen = ReportGenerator(result)
    report_path = report_gen.generate_full_report(output_dir="backtest_reports/basic_1yr")
    print(f"Report saved to: {report_path}")

    return result


def run_multi_year_backtest():
    """Run a backtest over the past 3 years"""
    print("\n")
    print("=" * 80)
    print("Running Multi-Year Backtest - 3 Years")
    print("=" * 80)

    # Define backtest period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3 * 365)

    # Create configuration
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000_000,
        max_positions=20,
        max_position_size=0.10,
        min_composite_score=60.0,
        min_momentum_score=50.0,
        min_quality_score=40.0,
        stop_loss_pct=0.10,
        take_profit_pct=0.20,
        trailing_stop_pct=0.08,
        position_sizing_method="equal",
        markets=["KOSPI", "KOSDAQ"],
    )

    # Run backtest
    engine = BacktestingEngine(config)
    result = engine.run()

    # Print summary
    print("\n")
    print(result.summary())

    # Generate report
    print("\nGenerating performance report...")
    report_gen = ReportGenerator(result)
    report_path = report_gen.generate_full_report(output_dir="backtest_reports/multi_year_3yr")
    print(f"Report saved to: {report_path}")

    return result


def run_conservative_strategy():
    """Run backtest with conservative parameters"""
    print("\n")
    print("=" * 80)
    print("Running Conservative Strategy Backtest")
    print("=" * 80)

    # Define backtest period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # Conservative configuration
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000_000,
        max_positions=15,  # Fewer positions
        max_position_size=0.07,  # Smaller position size
        # Stricter entry criteria
        min_composite_score=70.0,  # Higher threshold
        min_momentum_score=60.0,
        min_quality_score=50.0,
        # Tighter stop loss
        stop_loss_pct=0.07,  # 7% stop loss
        take_profit_pct=0.15,  # 15% take profit
        trailing_stop_pct=0.05,  # 5% trailing stop
        position_sizing_method="equal",
        markets=["KOSPI"],  # KOSPI only (more stable)
    )

    # Run backtest
    engine = BacktestingEngine(config)
    result = engine.run()

    # Print summary
    print("\n")
    print(result.summary())

    # Generate report
    print("\nGenerating performance report...")
    report_gen = ReportGenerator(result)
    report_path = report_gen.generate_full_report(
        output_dir="backtest_reports/conservative_strategy"
    )
    print(f"Report saved to: {report_path}")

    return result


def run_aggressive_strategy():
    """Run backtest with aggressive parameters"""
    print("\n")
    print("=" * 80)
    print("Running Aggressive Strategy Backtest")
    print("=" * 80)

    # Define backtest period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # Aggressive configuration
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000_000,
        max_positions=30,  # More positions
        max_position_size=0.15,  # Larger position size
        # Looser entry criteria
        min_composite_score=55.0,  # Lower threshold
        min_momentum_score=45.0,
        min_quality_score=35.0,
        # Wider stops
        stop_loss_pct=0.15,  # 15% stop loss
        take_profit_pct=0.30,  # 30% take profit
        trailing_stop_pct=0.12,  # 12% trailing stop
        position_sizing_method="equal",
        markets=["KOSPI", "KOSDAQ"],
    )

    # Run backtest
    engine = BacktestingEngine(config)
    result = engine.run()

    # Print summary
    print("\n")
    print(result.summary())

    # Generate report
    print("\nGenerating performance report...")
    report_gen = ReportGenerator(result)
    report_path = report_gen.generate_full_report(
        output_dir="backtest_reports/aggressive_strategy"
    )
    print(f"Report saved to: {report_path}")

    return result


def compare_strategies():
    """Compare multiple strategy configurations"""
    print("\n")
    print("=" * 80)
    print("Comparing Multiple Strategies")
    print("=" * 80)

    # Run different strategies
    results = {
        "Conservative": run_conservative_strategy(),
        "Balanced": run_basic_backtest(),
        "Aggressive": run_aggressive_strategy(),
    }

    # Print comparison
    print("\n")
    print("=" * 80)
    print("Strategy Comparison Summary")
    print("=" * 80)
    print(
        f"{'Strategy':<20} {'Return':<12} {'Sharpe':<10} {'Max DD':<10} {'Win Rate':<10} {'Trades':<10}"
    )
    print("-" * 80)

    for name, result in results.items():
        m = result.metrics
        print(
            f"{name:<20} {m.total_return:>10.2f}%  {m.sharpe_ratio:>8.2f}  "
            f"{m.max_drawdown:>8.2f}%  {m.win_rate:>8.2f}%  {m.total_trades:>8d}"
        )

    print("=" * 80)


def main():
    """Main function"""
    print("\n" + "=" * 80)
    print("Ko-Stock-Filter Backtesting Framework")
    print("=" * 80)

    # Menu
    print("\nSelect an example to run:")
    print("1. Basic 1-Year Backtest")
    print("2. Multi-Year Backtest (3 years)")
    print("3. Conservative Strategy")
    print("4. Aggressive Strategy")
    print("5. Compare All Strategies")
    print("0. Exit")

    choice = input("\nEnter your choice (0-5): ").strip()

    if choice == "1":
        run_basic_backtest()
    elif choice == "2":
        run_multi_year_backtest()
    elif choice == "3":
        run_conservative_strategy()
    elif choice == "4":
        run_aggressive_strategy()
    elif choice == "5":
        compare_strategies()
    elif choice == "0":
        print("Exiting...")
        return
    else:
        print("Invalid choice. Please try again.")
        return

    print("\nBacktest complete!")


if __name__ == "__main__":
    main()
