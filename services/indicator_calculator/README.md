# Financial Indicator Calculator

A comprehensive service for calculating and storing financial indicators for Korean stocks.

## Features

### Calculated Indicators

1. **PER (Price to Earnings Ratio)**
   - Formula: Current Price / Earnings Per Share
   - Measures how much investors are willing to pay per unit of earnings

2. **PBR (Price to Book Ratio)**
   - Formula: Current Price / Book Value Per Share
   - Compares market value to book value

3. **ROE (Return on Equity)**
   - Formula: (Net Income / Total Equity) × 100
   - Measures profitability relative to shareholders' equity

4. **Debt Ratio**
   - Formula: (Total Debt / Total Assets) × 100
   - Indicates the proportion of assets financed by debt

5. **Operating Margin**
   - Formula: (Operating Profit / Revenue) × 100
   - Shows operational efficiency

6. **EPS Growth Rate**
   - Formula: ((Current EPS - Previous EPS) / Previous EPS) × 100
   - Year-over-year earnings per share growth

7. **Revenue Growth Rate**
   - Formula: ((Current Revenue - Previous Revenue) / Previous Revenue) × 100
   - Year-over-year revenue growth

## Architecture

The calculator is organized into three main components:

### 1. Financial Calculator (`financial_calculator.py`)
- Core calculation logic for all indicators
- Handles missing data gracefully with defensive programming
- Returns `None` for indicators that cannot be calculated
- Validates input data (e.g., prevents division by zero)

### 2. Financial Data Repository (`financial_repository.py`)
- Database access layer using SQLAlchemy
- Fetches stock prices, fundamental data, and historical data
- Saves calculated indicators to the database
- Handles data retrieval for growth calculations (YoY comparisons)

### 3. Financial Indicator Service (`financial_service.py`)
- Orchestrates calculation workflow
- Processes individual stocks or batches
- Provides transaction management
- Generates calculation statistics and reports

## Usage

### Command Line Interface

The service includes a CLI script for easy execution:

```bash
# Calculate for all active stocks
python services/indicator_calculator/run_financial_calculation.py --all

# Calculate only for stocks without recent data
python services/indicator_calculator/run_financial_calculation.py --missing

# Calculate for specific tickers
python services/indicator_calculator/run_financial_calculation.py --tickers 005930 000660

# Calculate with a specific date
python services/indicator_calculator/run_financial_calculation.py --all --date 2024-10-01
```

### Programmatic Usage

```python
from shared.database.connection import SessionLocal
from services.indicator_calculator.financial_service import FinancialIndicatorService

# Create database session
db = SessionLocal()

try:
    # Initialize service
    service = FinancialIndicatorService(db_session=db)

    # Calculate for all stocks
    stats = service.calculate_indicators_for_all_stocks()
    print(f"Processed {stats['successful']} stocks successfully")

    # Calculate for specific stock ID
    indicators = service.calculate_indicators_for_stock(stock_id=1)
    if indicators:
        print(f"PER: {indicators.per}")
        print(f"ROE: {indicators.roe}%")

    # Calculate for specific tickers
    stats = service.calculate_indicators_for_tickers(['005930', '000660'])

finally:
    db.close()
```

### Daily Scheduled Calculation

For automated daily calculations, use the `run_daily_calculation` function:

```python
from services.indicator_calculator.financial_service import run_daily_calculation

# This can be called by a scheduler (e.g., cron, APScheduler)
stats = run_daily_calculation()
```

## Missing Data Handling

The calculator is designed to handle missing data gracefully:

1. **Partial Calculations**: If some data is missing, the calculator will compute what it can and return `None` for indicators that cannot be calculated.

2. **Growth Metrics**: Growth calculations require historical data. If previous period data is not available, growth metrics will be `None`, but other indicators will still be calculated.

3. **Validation**: All calculations include validation:
   - Checks for `None` values
   - Prevents division by zero
   - Handles negative values appropriately
   - Validates data types

4. **Logging**: The service logs warnings for missing data and errors, making it easy to identify data quality issues.

## Database Schema

The calculator stores results in the `fundamental_indicators` table with the following key fields:

```sql
- per: Float (Price to Earnings Ratio)
- pbr: Float (Price to Book Ratio)
- roe: Float (Return on Equity %)
- debt_ratio: Float (Debt to Total Assets %)
- operating_margin: Float (Operating Profit Margin %)
- earnings_growth: Float (YoY Earnings Growth %)
- revenue_growth: Float (YoY Revenue Growth %)
- eps: Float (Earnings Per Share)
- bps: Float (Book Value Per Share)
- date: DateTime (Calculation date)
```

## Error Handling

The service implements comprehensive error handling:

- **Try-Catch Blocks**: All database operations and calculations are wrapped in try-catch blocks
- **Transaction Management**: Database commits and rollbacks are properly managed
- **Detailed Logging**: Errors are logged with full stack traces for debugging
- **Statistics Tracking**: The service tracks successful, failed, and skipped calculations

## Testing

Run the test suite to verify calculations:

```bash
# Run all financial calculator tests
pytest tests/test_financial_calculator.py -v

# Run with coverage
pytest tests/test_financial_calculator.py --cov=services.indicator_calculator --cov-report=html
```

The test suite includes:
- Unit tests for each indicator calculation
- Edge cases (zero values, negative values, missing data)
- Integration tests for the full calculation workflow
- Tests for data type conversions

## Configuration

The service uses configuration from `shared/configs/config.py`:
- Database connection settings
- Logging levels
- Date ranges for historical data lookback

## Dependencies

- SQLAlchemy: Database ORM
- Python 3.8+: Core language
- PostgreSQL: Database backend

## Scheduling

For production deployments, set up a daily scheduled job:

### Using Cron

```bash
# Add to crontab (run daily at 8 PM)
0 20 * * * cd /path/to/ko-stock-filter && python services/indicator_calculator/run_financial_calculation.py --all >> logs/financial_calc.log 2>&1
```

### Using APScheduler

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from services.indicator_calculator.financial_service import run_daily_calculation

scheduler = BlockingScheduler()
scheduler.add_job(run_daily_calculation, 'cron', hour=20, minute=0)
scheduler.start()
```

## Performance Considerations

- **Batch Processing**: The service processes stocks in batches for efficiency
- **Database Connection Pooling**: Uses connection pooling for optimal database performance
- **Incremental Updates**: Use `--missing` flag to only calculate for stocks without recent data
- **Logging**: Production deployments should configure appropriate log levels to balance debugging and performance

## Troubleshooting

### Common Issues

1. **No data calculated for a stock**
   - Check if price data exists in `stock_prices` table
   - Verify fundamental data exists in `fundamental_indicators` table
   - Review logs for specific error messages

2. **Growth metrics are None**
   - Requires historical data from approximately 1 year ago
   - Check if previous period data exists
   - Verify date ranges in database

3. **Division by zero errors**
   - The calculator handles these gracefully and returns `None`
   - Check source data quality

## Future Enhancements

Potential improvements:
- Async/parallel processing for better performance
- Caching layer for frequently accessed data
- Real-time calculation triggers
- API endpoints for on-demand calculations
- More sophisticated growth metrics (CAGR, etc.)
- Additional financial ratios (Quick Ratio, Current Ratio, etc.)
