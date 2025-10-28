# Stock Screener Service

Comprehensive stock screening engine for filtering Korean stocks based on multiple criteria including volatility, valuation, financial health, and liquidity.

## Features

### Implemented Filters

1. **Volatility Filter**
   - Removes high volatility stocks
   - Configurable maximum volatility threshold (default: 40%)
   - Uses annualized volatility from stability scores

2. **Valuation Filters**
   - Removes overvalued stocks
   - PER (Price-to-Earnings Ratio) threshold (default: max 50)
   - PBR (Price-to-Book Ratio) threshold (default: max 5)

3. **Financial Health Filter**
   - Removes financially unstable companies
   - Debt ratio threshold (default: max 200%)
   - Filters companies with excessive debt

4. **Liquidity Filters**
   - Removes low liquidity stocks
   - Minimum average volume (default: 100,000 shares)
   - Minimum trading value (default: 100,000,000 KRW)

5. **Undervalued Stock Identification**
   - Identifies potentially undervalued stocks
   - PBR < 1.0 criterion
   - PER below industry average
   - Provides reasons for undervaluation

### Additional Features

- **Market Filters**: Filter by KOSPI, KOSDAQ, or KONEX
- **Sector/Industry Filters**: Filter by specific sectors or industries
- **Data Quality Checks**: Ensures sufficient historical data
- **Screening Summary**: Provides statistics on screening results
- **Configurable Thresholds**: All thresholds configurable via environment variables

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

All screening thresholds are configurable through environment variables:

```bash
# Volatility filter
MAX_VOLATILITY_PCT=40.0

# Valuation filters
MAX_PER=50.0
MAX_PBR=5.0

# Financial health filters
MAX_DEBT_RATIO_PCT=200.0

# Liquidity filters
MIN_AVG_VOLUME=100000
MIN_TRADING_VALUE=100000000.0

# Undervalued stock identification
UNDERVALUED_PBR_THRESHOLD=1.0
PER_INDUSTRY_AVG_MULTIPLIER=1.0

# Data requirements
MIN_PRICE_HISTORY_DAYS=60
MIN_VOLUME_HISTORY_DAYS=20
```

## Usage

### Command Line

Run the stock screener service directly:

```bash
python -m services.stock_screener.main
```

This will:
1. Apply all default filters
2. Display top 10 filtered stocks
3. Show screening summary statistics
4. Identify undervalued stocks

### Programmatic Usage

```python
from services.stock_screener import StockScreenerService, ScreeningCriteria

# Initialize service
service = StockScreenerService()
service.start()

# Apply default filters
results = service.apply_default_filters()

# Custom screening criteria
criteria = ScreeningCriteria(
    max_volatility_pct=30.0,
    max_per=40.0,
    max_pbr=3.0,
    max_debt_ratio_pct=150.0,
    min_avg_volume=500000,
    markets=['KOSPI'],  # KOSPI only
    sectors=['Technology']  # Technology sector only
)
results = service.screen_stocks(criteria)

# Find undervalued stocks
undervalued = service.identify_undervalued_stocks()

# Get summary statistics
summary = service.get_screening_summary(results)
```

### Individual Filters

```python
# Filter high volatility stocks only
low_volatility = service.filter_high_volatility(max_volatility_pct=35.0)

# Filter overvalued stocks only
reasonably_valued = service.filter_overvalued(max_per=40.0, max_pbr=3.0)

# Filter unstable companies only
stable_companies = service.filter_unstable_companies(max_debt_ratio_pct=150.0)

# Filter low liquidity stocks only
liquid_stocks = service.filter_low_liquidity(
    min_avg_volume=200000,
    min_trading_value=200000000.0
)
```

## Screening Process

The screening engine follows this process:

1. **Fetch Active Stocks**
   - Retrieves all active stocks from database
   - Applies market/sector/industry filters

2. **Data Quality Check**
   - Verifies sufficient price history (default: 60 days)
   - Verifies sufficient volume history (default: 20 days)

3. **Apply Filters**
   - Price filters (min/max price, market cap)
   - Volatility filter (from stability scores)
   - Valuation filters (PER, PBR from fundamentals)
   - Financial health filters (debt ratio)
   - Liquidity filters (average volume, trading value)
   - Stability score filters (optional)

4. **Identify Undervalued**
   - Check PBR < threshold
   - Compare PER to industry average
   - Record reasons for undervaluation

5. **Build Results**
   - Compile all metrics for passing stocks
   - Return structured results with all relevant data

## Result Structure

Each screening result includes:

```python
ScreeningResult(
    ticker='005930',
    name_kr='삼성전자',
    market='KOSPI',
    sector='Technology',
    industry='Semiconductors',
    current_price=70000.0,
    market_cap=400000000000000.0,
    per=12.5,
    pbr=1.2,
    debt_ratio=50.0,
    roe=15.0,
    avg_volume=10000000.0,
    avg_trading_value=700000000000.0,
    volatility_pct=25.0,
    stability_score=83.0,
    is_undervalued=False,
    undervalued_reasons=[]
)
```

## Dependencies

The stock screener relies on data from:

- **Stock Prices**: Historical OHLCV data
- **Fundamental Indicators**: PER, PBR, debt ratio, ROE, etc.
- **Stability Scores**: Volatility and stability metrics

Ensure these are populated before running the screener:
1. Run data collector to fetch stock data
2. Run indicator calculator to compute fundamentals
3. Run stability calculator to compute stability scores
4. Run stock screener to filter stocks

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_stock_screener.py -v
```

Test coverage:
- 15 test cases covering all major functionality
- 84% code coverage
- Tests for each individual filter
- Tests for combined filters
- Tests for edge cases and data quality

## Performance Considerations

- Uses database indexes for efficient querying
- Filters applied progressively to reduce data processing
- Supports batch processing for large datasets
- Connection pooling for database efficiency

## Example Output

```
=============================================================
SCREENING RESULTS: 45 stocks passed all filters
=============================================================

1. 005930 (삼성전자)
   Market: KOSPI | Sector: Technology
   Price: 70,000 KRW | Market Cap: 400,000,000,000,000
   PER: 12.50 | PBR: 1.20
   Debt Ratio: 50.0%
   Avg Volume: 10,000,000
   Volatility: 25.0%
   Stability Score: 83.0/100

=============================================================
SUMMARY
=============================================================
Total stocks: 45
Undervalued: 12
Markets: {'KOSPI': 35, 'KOSDAQ': 10}
Average PER: 18.50
Average PBR: 1.80
Average Debt Ratio: 85.5%
```

## Architecture

```
StockScreenerService
├── StockScreeningEngine
│   ├── _get_active_stocks()      # Fetch base stock list
│   ├── _screen_single_stock()    # Apply all filters
│   ├── _check_volatility_filter()
│   ├── _check_valuation_filters()
│   ├── _check_financial_health_filters()
│   ├── _check_liquidity_filters()
│   ├── _check_undervalued()
│   └── get_screening_summary()   # Generate statistics
└── ScreeningCriteria              # Configuration dataclass
```

## Future Enhancements

- [ ] Add momentum filters (RSI, MACD)
- [ ] Add growth filters (revenue growth, earnings growth)
- [ ] Add dividend yield filters
- [ ] Support custom weighted scoring
- [ ] Add screening result export (CSV, Excel)
- [ ] Add screening result visualization
- [ ] REST API endpoints via FastAPI
- [ ] Scheduled screening jobs
- [ ] Screening result caching

## License

Part of the Korean Stock Trading System
