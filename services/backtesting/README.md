# Backtesting Framework

Comprehensive backtesting framework for evaluating trading strategies on historical Korean stock market data.

## Features

- **Fast Data Loading**: Efficient historical data loading from PostgreSQL database with caching
- **Vectorized Operations**: Uses pandas/numpy vectorized operations for maximum performance
- **Comprehensive Metrics**: 30+ performance metrics including Sharpe ratio, max drawdown, win rate, etc.
- **Rich Visualizations**: Automatic generation of performance charts and reports
- **Parameter Optimization**: Grid search and comparison of strategy parameters
- **Realistic Simulation**: Includes slippage, commissions, and Korean market-specific taxes

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. The framework uses these key libraries:
- pandas & numpy: Data manipulation and vectorized operations
- matplotlib & seaborn: Chart generation
- sqlalchemy: Database access

## Quick Start

### Basic Backtest

```python
from datetime import datetime, timedelta
from services.backtesting import BacktestConfig, BacktestingEngine, ReportGenerator

# Define period
end_date = datetime.now()
start_date = end_date - timedelta(days=365)  # 1 year

# Configure backtest
config = BacktestConfig(
    start_date=start_date,
    end_date=end_date,
    initial_capital=100_000_000,  # 100M KRW
    max_positions=20,
    max_position_size=0.10,  # 10% per position
    min_composite_score=60.0,
    stop_loss_pct=0.10,
    take_profit_pct=0.20,
)

# Run backtest
engine = BacktestingEngine(config)
result = engine.run()

# View results
print(result.summary())

# Generate report
report_gen = ReportGenerator(result)
report_path = report_gen.generate_full_report()
print(f"Report saved to: {report_path}")
```

### Parameter Optimization

```python
from services.backtesting import ParameterOptimizer

# Create optimizer
optimizer = ParameterOptimizer(base_config)

# Define parameter ranges
parameter_ranges = {
    "min_composite_score": [55.0, 60.0, 65.0, 70.0],
    "stop_loss_pct": [0.05, 0.07, 0.10, 0.12],
    "take_profit_pct": [0.15, 0.20, 0.25, 0.30],
}

# Run grid search
results = optimizer.grid_search(
    parameter_ranges,
    optimization_metric="sharpe_ratio"
)

# Generate optimization report
report_path = optimizer.generate_optimization_report(results)
```

## Configuration Options

### BacktestConfig Parameters

#### Time Period
- `start_date`: Start date for backtest
- `end_date`: End date for backtest

#### Capital & Position Sizing
- `initial_capital`: Starting capital (default: 100M KRW)
- `max_positions`: Maximum number of concurrent positions (default: 20)
- `max_position_size`: Maximum size per position as fraction of portfolio (default: 0.10 = 10%)
- `position_sizing_method`: "equal", "kelly", or "volatility" (default: "equal")
- `kelly_fraction`: Fraction of Kelly criterion to use (default: 0.25 for quarter-Kelly)

#### Entry Criteria
- `min_composite_score`: Minimum composite score for entry (default: 60.0)
- `min_momentum_score`: Minimum momentum score (default: 50.0)
- `min_quality_score`: Minimum quality score (default: 40.0)
- `min_volume`: Minimum daily volume filter (optional)
- `min_price`: Minimum price filter (optional)

#### Exit Criteria
- `stop_loss_pct`: Stop loss percentage (default: 0.10 = 10%)
- `take_profit_pct`: Take profit percentage (default: 0.20 = 20%)
- `trailing_stop_pct`: Trailing stop percentage (default: 0.08 = 8%)
- `quality_exit_threshold`: Exit if quality score drops below this (default: 40.0)
- `score_deterioration_threshold`: Exit if score drops by this amount (default: 20.0)

#### Costs
- `commission_rate`: Commission rate (default: 0.00015 = 0.015%)
- `slippage_bps`: Slippage in basis points (default: 10 bps)

#### Universe Filters
- `markets`: List of markets, e.g., ["KOSPI", "KOSDAQ"] (default: None = all)
- `sectors`: List of sectors to include (default: None = all)

#### Risk Management
- `max_sector_concentration`: Maximum exposure to one sector (default: 0.30 = 30%)
- `max_correlation`: Maximum correlation between positions (default: 0.70)

## Performance Metrics

The framework calculates 30+ comprehensive metrics:

### Return Metrics
- Total Return (%)
- Annualized Return (%)
- CAGR (Compound Annual Growth Rate)

### Risk Metrics
- Volatility (annualized)
- Maximum Drawdown (%)
- Max Drawdown Duration (days)
- Value at Risk (95%)
- Conditional VaR (95%)
- Ulcer Index

### Risk-Adjusted Returns
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio

### Trade Metrics
- Total Trades
- Win Rate (%)
- Profit Factor (gross profit / gross loss)
- Average Win/Loss (%)
- Best/Worst Trade (%)
- Average Holding Period (days)

### Monthly Metrics
- Best/Worst Month (%)
- Positive Months Count

## Generated Reports

### Performance Report (HTML)
The framework generates a comprehensive HTML report with:
- Summary metrics dashboard
- Performance tables
- 5 detailed chart images:
  1. **Portfolio Performance**: Equity curve and cumulative returns
  2. **Drawdown Analysis**: Drawdown timeline, histogram, and underwater plot
  3. **Returns Distribution**: Histogram, Q-Q plot, and daily returns
  4. **Monthly Returns**: Heatmap by month and year
  5. **Rolling Metrics**: Rolling Sharpe, volatility, and returns

### Optimization Report (HTML)
For parameter optimization:
- Best configurations by different metrics
- Efficient frontier plot (return vs risk)
- Parameter comparison charts
- Parameter heatmaps
- Complete results table

### CSV Exports
- `trades.csv`: Complete trade history
- `portfolio_values.csv`: Daily portfolio values
- `positions.csv`: Position history
- `metrics.csv`: All calculated metrics

## Examples

See the `examples/` directory for comprehensive examples:

1. **backtest_example.py**: Basic backtesting examples
   - 1-year backtest
   - 3-year backtest
   - Conservative strategy
   - Aggressive strategy
   - Strategy comparison

2. **parameter_optimization_example.py**: Parameter optimization examples
   - Entry/exit parameter optimization
   - Position sizing optimization
   - Manual parameter set comparison
   - Composite score threshold optimization

## Architecture

### Components

1. **BacktestDataLoader** (`data_loader.py`)
   - Efficient data loading from database
   - Caching for repeated queries
   - Multi-index DataFrames for fast lookups

2. **BacktestingEngine** (`backtesting_engine.py`)
   - Main simulation engine
   - Day-by-day simulation
   - Portfolio tracking
   - Trade execution

3. **MetricsCalculator** (`performance_metrics.py`)
   - Comprehensive metrics calculation
   - Vectorized operations for speed
   - Industry-standard formulas

4. **ReportGenerator** (`report_generator.py`)
   - HTML report generation
   - Chart creation with matplotlib/seaborn
   - CSV exports

5. **ParameterOptimizer** (`parameter_optimizer.py`)
   - Grid search over parameter ranges
   - Parallel execution support
   - Results comparison and visualization

## Performance Optimization

The framework uses several techniques for speed:

1. **Vectorized Operations**: All calculations use pandas/numpy vectorization
2. **Data Caching**: Historical data is cached to avoid repeated database queries
3. **Efficient Indexing**: Multi-index DataFrames for O(1) lookups
4. **Batch Processing**: Trades are processed in batches where possible
5. **Parallel Optimization**: Parameter optimization can run in parallel

## Korean Market Specifics

The framework handles Korean market-specific details:

### Fees
- **Commission**: 0.015% (configurable)
- **Transaction Tax**: 0.23% on sells only
- **Agricultural/Fisheries Tax**: 0.15% of transaction tax

### Markets
- **KOSPI**: Main board (typically more stable)
- **KOSDAQ**: Tech-focused board (typically more volatile)
- **KONEX**: SME board

### Trading
- No fractional shares (shares rounded down)
- T+2 settlement (not enforced in backtest)

## Limitations

1. **Historical Bias**: Strategy designed with knowledge of past data
2. **Market Impact**: Does not model large order market impact
3. **Liquidity**: Assumes all trades can be executed at calculated prices
4. **Dividends**: Dividend payments not included
5. **Corporate Actions**: Stock splits, mergers not handled
6. **Short Selling**: Only long positions supported

## Best Practices

1. **Use Multiple Time Periods**: Test strategies across different market conditions
2. **Out-of-Sample Testing**: Reserve recent data for validation
3. **Walk-Forward Analysis**: Periodically re-optimize parameters
4. **Conservative Assumptions**: Use realistic slippage and commissions
5. **Risk Management**: Always use stop losses
6. **Diversification**: Maintain multiple positions
7. **Parameter Stability**: Prefer strategies that work across parameter ranges

## Troubleshooting

### No Data Found
- Check database connection
- Verify date range has data
- Ensure stock universe filters are not too restrictive

### Slow Performance
- Reduce date range for initial tests
- Reduce number of stocks in universe
- Use caching (enabled by default)
- For optimization, increase `max_workers` for parallel execution

### Memory Issues
- Process smaller date ranges
- Reduce number of stocks
- Clear cache between runs: `data_loader.clear_cache()`

## Advanced Usage

### Custom Position Sizing

```python
# Equal weight
config.position_sizing_method = "equal"

# Kelly criterion (uses quarter-Kelly by default)
config.position_sizing_method = "kelly"
config.kelly_fraction = 0.25  # Adjust conservatism

# Volatility-adjusted (larger positions for less volatile stocks)
config.position_sizing_method = "volatility"
```

### Sector-Specific Testing

```python
# Test specific sector
config.sectors = ["Technology"]

# Test multiple sectors
config.sectors = ["Technology", "Finance", "Healthcare"]
```

### Custom Optimization Metrics

```python
# Optimize for different objectives
results = optimizer.grid_search(
    parameter_ranges,
    optimization_metric="total_return"  # or "calmar_ratio", "win_rate", etc.
)
```

## Contributing

When extending the framework:

1. Maintain vectorized operations for performance
2. Add comprehensive docstrings
3. Include examples in docstrings
4. Update this README
5. Add tests for new functionality

## References

- Sharpe Ratio: (Return - RiskFree) / Volatility
- Sortino Ratio: (Return - RiskFree) / Downside Deviation
- Calmar Ratio: Return / Max Drawdown
- Ulcer Index: RMS of drawdowns
- Kelly Criterion: f* = (p*b - q) / b

## Support

For issues or questions:
1. Check existing examples
2. Review this documentation
3. Check the docstrings in the code
4. Open an issue on GitHub

## License

Part of the Ko-Stock-Filter project.
