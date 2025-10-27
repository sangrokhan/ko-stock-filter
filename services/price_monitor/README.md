# Price Monitor Service

Real-time price monitoring service for Korean stocks that tracks price changes during market hours, detects significant movements, and publishes events.

## Features

- **Market Hours Awareness**: Automatically operates only during Korean stock market hours (09:00-15:30 KST)
- **Holiday Calendar**: Respects Korean stock market holidays and weekends
- **Configurable Polling**: Poll price updates every 1-5 minutes (configurable)
- **Significant Change Detection**: Detects price changes exceeding 5% (configurable)
- **Database Updates**: Automatically updates stock prices in PostgreSQL database
- **Event Publishing**: Publishes price updates and alerts to Redis for other services
- **High Performance**: Supports concurrent price updates for multiple stocks

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Price Monitor Service                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Market     │    │    Price     │    │    Event     │  │
│  │   Calendar   │───▶│   Monitor    │───▶│  Publisher   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │         │
│         ▼                    ▼                    ▼         │
│  Check Hours         Fetch Prices          Publish to      │
│  & Holidays         Update DB              Redis Queue     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         │                     │                    │
         ▼                     ▼                    ▼
   KST Timezone          PostgreSQL              Redis
   Holiday List          Stock Prices            Events
```

## Components

### 1. Market Calendar (`market_calendar.py`)
- Detects Korean stock market trading hours (09:00-15:30 KST)
- Maintains Korean stock market holiday calendar
- Provides utilities to check if market is open
- Calculates time until next market open/close

### 2. Price Monitor (`price_monitor.py`)
- Fetches current prices for active stocks
- Calculates price changes and percentage movements
- Detects significant price changes (>5% by default)
- Updates stock prices in the database
- Coordinates with event publisher

### 3. Event Publisher (`event_publisher.py`)
- Publishes price update events to Redis
- Publishes significant change alerts
- Caches latest prices in Redis for quick access
- Supports multiple event channels

### 4. Main Service (`main.py`)
- Orchestrates all components
- Manages service lifecycle
- Implements monitoring loop
- Handles graceful shutdown

## Configuration

Configure the service using environment variables with the `PRICE_MONITOR_` prefix:

```bash
# Database
PRICE_MONITOR_DATABASE_URL=postgresql://user:password@localhost:5432/stock_trading

# Redis
PRICE_MONITOR_REDIS_HOST=localhost
PRICE_MONITOR_REDIS_PORT=6379
PRICE_MONITOR_REDIS_DB=0
PRICE_MONITOR_REDIS_PASSWORD=your_password

# Monitoring Settings
PRICE_MONITOR_POLL_INTERVAL_SECONDS=60  # Poll every 1 minute
PRICE_MONITOR_SIGNIFICANT_CHANGE_THRESHOLD=5.0  # 5% threshold

# API Keys (Korean stock data providers)
PRICE_MONITOR_KOREAINVESTMENT_API_KEY=your_api_key
PRICE_MONITOR_KOREAINVESTMENT_API_SECRET=your_api_secret
PRICE_MONITOR_KOREAINVESTMENT_APP_KEY=your_app_key
PRICE_MONITOR_KOREAINVESTMENT_APP_SECRET=your_app_secret

# Logging
PRICE_MONITOR_LOG_LEVEL=INFO
```

Or create a `.env` file in the project root:

```env
PRICE_MONITOR_DATABASE_URL=postgresql://user:password@localhost:5432/stock_trading
PRICE_MONITOR_REDIS_HOST=localhost
PRICE_MONITOR_REDIS_PORT=6379
PRICE_MONITOR_POLL_INTERVAL_SECONDS=60
PRICE_MONITOR_SIGNIFICANT_CHANGE_THRESHOLD=5.0
PRICE_MONITOR_LOG_LEVEL=INFO
```

## Usage

### Running the Service

```bash
# Navigate to project root
cd /path/to/ko-stock-filter

# Install dependencies
pip install -r requirements.txt

# Run the service
python -m services.price_monitor.main
```

### Running with Docker

```bash
# Build the Docker image
docker build -t price-monitor -f docker/price_monitor.Dockerfile .

# Run the container
docker run -d \
  --name price-monitor \
  --env-file .env \
  price-monitor
```

## Event Channels

The service publishes events to the following Redis channels:

### 1. `stock:price:update`
Published for every price update during polling.

```json
{
  "event_type": "price_update",
  "ticker": "005930",
  "timestamp": "2024-10-27T10:30:00",
  "data": {
    "current_price": 50000.0,
    "open": 49500.0,
    "high": 50500.0,
    "low": 49200.0,
    "volume": 1234567,
    "trading_value": 61728350000,
    "change_pct": 1.01
  }
}
```

### 2. `stock:price:significant_change`
Published when a price change exceeds the threshold (default: 5%).

```json
{
  "event_type": "significant_change",
  "ticker": "005930",
  "timestamp": "2024-10-27T10:30:00",
  "old_price": 50000.0,
  "new_price": 52500.0,
  "change_pct": 5.0,
  "data": {
    "current_price": 52500.0,
    "open": 49500.0,
    "high": 52500.0,
    "low": 49200.0,
    "volume": 2345678
  }
}
```

### 3. `stock:price:alert`
Published for custom price alerts.

```json
{
  "event_type": "price_alert",
  "ticker": "005930",
  "alert_type": "threshold_breach",
  "message": "Price exceeded upper threshold",
  "timestamp": "2024-10-27T10:30:00",
  "data": {
    "current_price": 55000.0
  }
}
```

## Subscribing to Events

Other services can subscribe to these events using Redis pub/sub:

```python
import redis
import json

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Subscribe to price updates
pubsub = r.pubsub()
pubsub.subscribe('stock:price:update', 'stock:price:significant_change')

# Process events
for message in pubsub.listen():
    if message['type'] == 'message':
        event = json.loads(message['data'])
        print(f"Received event: {event['event_type']} for {event['ticker']}")
```

## Market Hours

The service operates during Korean stock market hours:

- **Trading Hours**: 09:00 - 15:30 KST (Korea Standard Time)
- **Days**: Monday - Friday (excluding holidays)
- **Timezone**: Asia/Seoul (UTC+9)

### Korean Stock Market Holidays (2024-2025)

The service automatically handles the following holidays:

**Fixed Holidays:**
- New Year's Day (January 1)
- Independence Movement Day (March 1)
- Labor Day (May 1)
- Children's Day (May 5)
- Memorial Day (June 6)
- Liberation Day (August 15)
- National Foundation Day (October 3)
- Hangeul Day (October 9)
- Christmas Day (December 25)

**Lunar Holidays:**
- Lunar New Year (3 days)
- Buddha's Birthday
- Chuseok (Korean Thanksgiving, 3 days)

**Additional:**
- Substitute holidays when holidays fall on weekends
- Special election days
- Year-end closures

## Database Schema

The service updates the `stock_prices` table:

```sql
CREATE TABLE stock_prices (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    date TIMESTAMP NOT NULL,
    open NUMERIC(15, 2) NOT NULL,
    high NUMERIC(15, 2) NOT NULL,
    low NUMERIC(15, 2) NOT NULL,
    close NUMERIC(15, 2) NOT NULL,
    volume BIGINT NOT NULL,
    trading_value BIGINT,
    change_pct FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Integration with Korean Stock APIs

The service is designed to integrate with Korean stock market data providers:

### Supported Providers (To be implemented)

1. **Korea Investment & Securities API**
   - Real-time stock prices
   - Trading volume and value
   - Market data

2. **eBest Investment & Securities API**
   - Real-time quotes
   - KOSPI/KOSDAQ data

3. **KRX (Korea Exchange) API**
   - Official market data
   - Corporate actions

**Note**: Currently, the `fetch_current_price()` method in `price_monitor.py` is a placeholder.
Implement this method to integrate with your chosen data provider.

### Implementation Example

```python
def fetch_current_price(self, ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch current price from Korea Investment API."""
    try:
        # Example: Korea Investment API call
        response = requests.get(
            f"{API_BASE_URL}/stock/price",
            headers={
                "authorization": f"Bearer {self.api_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            },
            params={"ticker": ticker}
        )

        data = response.json()

        return {
            "ticker": ticker,
            "current_price": float(data["current_price"]),
            "open": float(data["open_price"]),
            "high": float(data["high_price"]),
            "low": float(data["low_price"]),
            "volume": int(data["volume"]),
            "trading_value": int(data["trading_value"]),
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Failed to fetch price for {ticker}: {e}")
        return None
```

## Monitoring and Logging

The service provides detailed logging:

```
2024-10-27 09:00:00 - price_monitor - INFO - Price Monitor Service starting...
2024-10-27 09:00:01 - price_monitor - INFO - Market is currently open
2024-10-27 09:00:01 - price_monitor - INFO - Running price monitoring cycle...
2024-10-27 09:00:05 - price_monitor - INFO - Retrieved 1234 active stocks to monitor
2024-10-27 09:00:15 - price_monitor - WARNING - Significant price change detected for 005930: 5.23%
2024-10-27 09:01:00 - price_monitor - INFO - Monitoring cycle completed - Total: 1234, Success: 1230, Failed: 2, Skipped: 2
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/test_price_monitor.py -v

# Run with coverage
pytest tests/test_price_monitor.py -v --cov=services.price_monitor

# Run specific test
pytest tests/test_price_monitor.py::TestKoreanMarketCalendar::test_market_hours -v
```

## Performance Considerations

- **Polling Interval**: Default is 60 seconds (1 minute). Can be configured from 60-300 seconds (1-5 minutes)
- **Concurrent Updates**: Supports up to 10 concurrent stock updates (configurable)
- **Database Connections**: Uses connection pooling for efficient database access
- **Redis Caching**: Caches latest prices in Redis with 1-hour TTL
- **Error Handling**: Retries failed API calls up to 3 times with exponential backoff

## Troubleshooting

### Service doesn't start
- Check database connection string
- Verify Redis is running and accessible
- Check log files for error messages

### No price updates
- Verify market is open (check logs)
- Ensure API credentials are configured
- Check that active stocks exist in database
- Verify network connectivity to data provider

### High memory usage
- Reduce number of active stocks
- Increase polling interval
- Check for memory leaks in custom API integrations

## Future Enhancements

- [ ] Support for pre-market and after-hours trading
- [ ] Integration with multiple data providers (failover)
- [ ] Real-time streaming instead of polling (WebSocket)
- [ ] Machine learning-based anomaly detection
- [ ] Advanced alerting (email, SMS, webhooks)
- [ ] Performance metrics and Prometheus integration
- [ ] Circuit breaker pattern for API calls
- [ ] Rate limiting and throttling

## License

MIT License - See LICENSE file for details
