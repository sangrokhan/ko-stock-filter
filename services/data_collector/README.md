# Korean Stock Data Collector Service

A comprehensive data collection service for Korean stock markets (KOSPI, KOSDAQ, KONEX) using FinanceDataReader and pykrx.

## Features

- **Stock Code Collection**: Fetches all stock codes from KOSPI, KOSDAQ, and KONEX markets
- **OHLCV Price Data**: Collects daily Open, High, Low, Close, Volume data for all stocks
- **Fundamental Data**: Collects company fundamentals (PER, PBR, EPS, BPS, market cap, etc.)
- **Rate Limiting**: Built-in rate limiter to respect data source limits
- **Error Handling**: Retry mechanisms with exponential backoff
- **Scheduled Collection**: Automatic daily/weekly collection using APScheduler
- **Comprehensive Logging**: Detailed logging for monitoring and debugging
- **PostgreSQL Storage**: Stores data in relational database for easy querying

## Architecture

```
data_collector/
├── main.py                      # Main service orchestrator
├── stock_code_collector.py      # Collects stock codes and basic info
├── price_collector.py           # Collects OHLCV price data
├── fundamental_collector.py     # Collects fundamental/financial data
├── scheduler.py                 # Manages scheduled tasks
├── db_session.py                # Database session management
├── utils.py                     # Utility functions (rate limiter, retry, etc.)
└── requirements.txt             # Python dependencies
```

## Installation

1. Install dependencies:
```bash
cd services/data_collector
pip install -r requirements.txt
```

2. Set up environment variables (create `.env` file in project root):
```env
DATABASE_URL=postgresql://user:password@localhost:5432/stock_trading
LOG_LEVEL=INFO
```

3. Run database migrations (if not already done):
```bash
cd ../../shared/database
alembic upgrade head
```

## Usage

### Running the Service

Start the data collector service with scheduler:
```bash
python main.py
```

The service will:
- Start the scheduler for continuous data collection
- Show scheduled job times
- Run in the background until stopped (Ctrl+C)

### Scheduled Jobs

The service runs the following jobs automatically:

| Job | Schedule | Description |
|-----|----------|-------------|
| Stock Code Collection | Sunday 1:00 AM KST | Updates list of all stocks |
| Daily Price Collection | Mon-Fri 4:00 PM KST | Collects daily OHLCV data after market close |
| Fundamental Collection | Mon-Fri 4:30 PM KST | Collects fundamental metrics |
| Stock Details Update | Sunday 2:00 AM KST | Updates market cap and shares |

### Initial Data Collection

To collect historical data when first setting up:

```python
from main import DataCollectorService

service = DataCollectorService(enable_scheduler=False)
service.run_initial_collection()  # Collects last 30 days of data
```

### Manual Collection

You can also run collectors manually:

```python
from stock_code_collector import StockCodeCollector
from price_collector import PriceCollector
from fundamental_collector import FundamentalCollector

# Collect stock codes
stock_collector = StockCodeCollector()
count = stock_collector.collect_all_stock_codes()
print(f"Collected {count} stocks")

# Collect prices for specific stock
price_collector = PriceCollector()
records = price_collector.collect_prices_for_stock(
    ticker="005930",  # Samsung Electronics
    start_date="2024-01-01",
    end_date="2024-01-31"
)
print(f"Collected {records} price records")

# Collect prices for all stocks
stats = price_collector.collect_prices_for_all_stocks(
    start_date="2024-10-26",
    end_date="2024-10-27"
)
print(f"Collected prices: {stats}")

# Collect fundamentals
fund_collector = FundamentalCollector()
success = fund_collector.collect_fundamentals_for_stock("005930")
```

## Data Sources

- **FinanceDataReader**: Primary source for OHLCV price data
- **pykrx**: Backup source for prices and primary source for fundamental data
- Both sources are free and do not require API keys

## Rate Limiting

The service includes built-in rate limiting:
- **Stock Code & Price Collector**: 1 request/second
- **Fundamental Collector**: 0.5 requests/second (more conservative)

This ensures respectful API usage and prevents rate limit errors.

## Error Handling

All collectors include:
- Automatic retry with exponential backoff (3 attempts)
- Detailed error logging
- Graceful degradation (continues with next stock on error)
- Transaction management (batch commits for performance)

## Logging

The service provides comprehensive logging:

```
2024-10-27 16:00:00 - INFO - Starting scheduled daily price collection
2024-10-27 16:00:01 - INFO - Processing 2500 stocks
2024-10-27 16:00:05 - INFO - Progress: 100/2500 stocks processed
2024-10-27 16:15:30 - INFO - Scheduled price collection completed: 2450/2500 stocks, 2450 records
```

Logging levels can be configured via `LOG_LEVEL` environment variable.

## Database Schema

Data is stored in the following tables:

- **stocks**: Stock information (ticker, name, market, sector, etc.)
- **stock_prices**: Daily OHLCV data
- **fundamental_indicators**: Fundamental metrics (PER, PBR, EPS, etc.)

See `shared/database/models.py` for complete schema.

## Performance

- **Stock Code Collection**: ~3-5 minutes for all markets (~3000 stocks)
- **Price Collection (single day)**: ~50 minutes for all stocks with rate limiting
- **Fundamental Collection**: ~80 minutes for all stocks with conservative rate limiting
- **Database**: Batch commits for optimal performance

## Monitoring

Check scheduler status:
```python
service = DataCollectorService()
status = service.get_scheduler_status()
print(status)
```

Manually trigger a job:
```python
service.run_scheduled_job('collect_daily_prices')
```

## Troubleshooting

**Problem**: Database connection errors
- **Solution**: Check `DATABASE_URL` in environment variables
- Ensure PostgreSQL is running and accessible

**Problem**: No data collected
- **Solution**: Check if markets are open (Korean markets: Mon-Fri 9:00-15:30 KST)
- Data may not be available immediately after market close

**Problem**: Rate limit errors
- **Solution**: Rate limiter should prevent this, but if it occurs:
  - Increase wait time in rate limiter
  - Run collection during off-peak hours

**Problem**: Missing data for some stocks
- **Solution**: Some stocks may be delisted or suspended
- Check `is_active` flag in database
- Review logs for specific error messages

## Future Enhancements

Possible improvements:
- Real-time data collection (websocket integration)
- Additional fundamental metrics (financial statements)
- Technical indicator calculation
- Data validation and quality checks
- API endpoint for on-demand collection
- Distributed collection (parallel workers)

## Contributing

When adding new features:
1. Follow existing code structure
2. Add comprehensive logging
3. Include error handling with retries
4. Update this README
5. Add tests if possible

## License

Part of the Korean Stock Trading System project.
