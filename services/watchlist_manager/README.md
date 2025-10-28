# Watchlist Manager Service

A comprehensive stock watchlist management system for the Korean Stock Trading System. This service provides powerful features for tracking, analyzing, and managing watchlist stocks with automated scoring, performance tracking, and criteria-based filtering.

## Features

### Core Functionality

- **Add Stocks to Watchlist**: Add stocks with automatic or custom reasons
- **Daily Updates**: Automatically update scores and metrics daily
- **Criteria-Based Filtering**: Automatically remove stocks that no longer meet your criteria
- **Historical Performance Tracking**: Track price and score changes over time
- **Export Capabilities**: Export to CSV or JSON formats for external analysis
- **Multi-User Support**: Isolate watchlists by user ID

### Automatic Reason Generation

When adding a stock to the watchlist without specifying a reason, the system automatically generates intelligent reasons based on:

- Composite scores (Value, Growth, Quality, Momentum)
- Stability metrics
- Fundamental indicators (PER, PBR, ROE, Dividend Yield)
- Market and sector information

### Historical Tracking

Each watchlist entry maintains a comprehensive history including:

- Daily price snapshots
- Score changes (composite and component scores)
- Performance metrics (total return, annualized return)
- Criteria compliance status
- Technical and fundamental metrics

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Required dependencies (install via requirements.txt)

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run database migration:
```bash
cd shared/database/alembic
alembic upgrade head
```

3. Verify installation:
```bash
python services/watchlist_manager/main.py --help
```

## Usage

### Command Line Interface (CLI)

The service provides a powerful CLI for managing watchlists.

#### Add Stock to Watchlist

```bash
# Add with automatic reason generation
python services/watchlist_manager/main.py add 005930 --target-price 75000 --tags "tech,semiconductor"

# Add with custom reason
python services/watchlist_manager/main.py add 000660 \
  --target-price 130000 \
  --reason "Strong Q4 earnings, HBM3 momentum" \
  --tags "tech,memory" \
  --notes "Monitor chip cycle recovery"
```

#### List Watchlist

```bash
# List all stocks (sorted by score)
python services/watchlist_manager/main.py list

# Detailed view with all metrics
python services/watchlist_manager/main.py list --detailed

# Sort by different criteria
python services/watchlist_manager/main.py list --sort-by price_change
python services/watchlist_manager/main.py list --sort-by added_date --ascending

# Show performance summary
python services/watchlist_manager/main.py list --show-summary
```

#### Update Watchlist

```bash
# Update all stocks with latest data
python services/watchlist_manager/main.py update
```

#### Clean Watchlist (Remove Stocks Not Meeting Criteria)

```bash
# Use default criteria
python services/watchlist_manager/main.py clean

# Custom criteria
python services/watchlist_manager/main.py clean \
  --max-volatility 30 \
  --max-per 40 \
  --max-pbr 3.0 \
  --max-debt-ratio 150 \
  --min-volume 200000
```

#### View Historical Performance

```bash
# Show all history for a stock
python services/watchlist_manager/main.py history 005930

# Show last 30 days
python services/watchlist_manager/main.py history 005930 --days 30
```

#### Export Watchlist

```bash
# Export to CSV
python services/watchlist_manager/main.py export --format csv --output my_watchlist.csv

# Export to JSON
python services/watchlist_manager/main.py export --format json --output my_watchlist.json

# Export to JSON with historical data
python services/watchlist_manager/main.py export --format json --include-history
```

#### Remove Stock from Watchlist

```bash
# Mark as inactive (soft delete)
python services/watchlist_manager/main.py remove 005930

# Permanently delete
python services/watchlist_manager/main.py remove 005930 --permanently
```

### Programmatic Usage

You can also use the `WatchlistManager` class directly in your Python code.

#### Basic Example

```python
from shared.database.connection import get_db
from services.watchlist_manager import WatchlistManager

# Initialize
db = next(get_db())
manager = WatchlistManager(db, user_id="my_user")

# Add stock to watchlist
entry = manager.add_to_watchlist(
    ticker='005930',
    target_price=75000,
    tags='tech,semiconductor'
)

# Get watchlist
watchlist = manager.get_watchlist(sort_by='score')

# Update daily
stats = manager.update_watchlist_daily()

# Export
manager.export_to_json('watchlist.json', include_history=True)
```

#### Advanced Example with Criteria Filtering

```python
from services.stock_screener.screening_engine import ScreeningCriteria

# Define criteria
criteria = ScreeningCriteria(
    max_volatility_pct=40.0,
    max_per=50.0,
    max_pbr=5.0,
    max_debt_ratio_pct=200.0,
    min_avg_volume=100000
)

# Remove stocks not meeting criteria
stats = manager.remove_stocks_not_meeting_criteria(criteria)
print(f"Removed {stats['removed']} stocks")
```

## API Reference

### WatchlistManager Class

#### Constructor

```python
WatchlistManager(db_session: Session, user_id: str = "default")
```

**Parameters:**
- `db_session`: SQLAlchemy database session
- `user_id`: User identifier for watchlist isolation

#### Methods

##### add_to_watchlist

```python
add_to_watchlist(
    ticker: str,
    target_price: Optional[float] = None,
    custom_reason: Optional[str] = None,
    tags: Optional[str] = None,
    notes: Optional[str] = None,
    alert_enabled: bool = False,
    alert_price_upper: Optional[float] = None,
    alert_price_lower: Optional[float] = None
) -> Optional[Watchlist]
```

Add a stock to the watchlist with automatic reason generation.

**Returns:** Watchlist entry or None if stock not found

##### get_watchlist

```python
get_watchlist(
    include_inactive: bool = False,
    sort_by: str = "score",
    ascending: bool = False
) -> List[Dict[str, Any]]
```

Get all watchlist entries with enriched data.

**Parameters:**
- `sort_by`: Field to sort by (score, added_date, ticker, price_change)
- `ascending`: Sort in ascending order

**Returns:** List of enriched watchlist entries

##### update_watchlist_daily

```python
update_watchlist_daily() -> Dict[str, Any]
```

Update all watchlist entries with new scores and create history snapshots.

**Returns:** Dictionary with update statistics

##### remove_stocks_not_meeting_criteria

```python
remove_stocks_not_meeting_criteria(
    criteria: ScreeningCriteria
) -> Dict[str, Any]
```

Remove stocks from watchlist that no longer meet specified criteria.

**Returns:** Dictionary with removal statistics

##### get_historical_performance

```python
get_historical_performance(
    ticker: str,
    days: Optional[int] = None
) -> List[Dict[str, Any]]
```

Get historical performance data for a watchlist stock.

**Returns:** List of historical snapshots

##### get_performance_summary

```python
get_performance_summary() -> Dict[str, Any]
```

Get overall performance summary of watchlist.

**Returns:** Dictionary with performance statistics

##### export_to_csv

```python
export_to_csv(filepath: str) -> bool
```

Export watchlist to CSV file.

**Returns:** True if successful

##### export_to_json

```python
export_to_json(
    filepath: str,
    include_history: bool = False
) -> bool
```

Export watchlist to JSON file.

**Returns:** True if successful

## Database Schema

### Watchlist Table

Stores watchlist entries with user-specific stock tracking.

**Key Fields:**
- `stock_id`: Foreign key to stocks table
- `user_id`: User identifier
- `ticker`: Stock ticker code
- `reason`: Reason for adding to watchlist
- `score`: Current composite score
- `target_price`: Target price for the stock
- `is_active`: Whether entry is active

### WatchlistHistory Table

Stores historical snapshots of watchlist stocks for performance tracking.

**Key Fields:**
- `watchlist_id`: Foreign key to watchlist
- `date`: Snapshot date
- `price`: Stock price at snapshot
- `composite_score`: Overall score
- `value_score`, `growth_score`, `quality_score`, `momentum_score`: Component scores
- `total_return_pct`: Total return since added
- `meets_criteria`: Whether stock still meets criteria

## Scheduling Daily Updates

To automate daily watchlist updates, you can use cron (Linux/Mac) or Task Scheduler (Windows).

### Using Cron

Add to your crontab:

```cron
# Update watchlist daily at 8 PM (after market close)
0 20 * * 1-5 cd /path/to/ko-stock-filter && python services/watchlist_manager/main.py update
```

### Using systemd Timer (Linux)

Create a systemd service and timer for automated updates.

## Examples

See `example_usage.py` for comprehensive examples including:

1. Adding stocks to watchlist
2. Viewing watchlist with different sorting
3. Updating watchlist daily
4. Cleaning watchlist based on criteria
5. Viewing historical performance
6. Exporting to CSV/JSON
7. Complete workflow demonstration

Run the examples:

```bash
python services/watchlist_manager/example_usage.py
```

## Testing

Run the test suite:

```bash
# Run all watchlist manager tests
pytest tests/test_watchlist_manager.py -v

# Run specific test
pytest tests/test_watchlist_manager.py::TestWatchlistManager::test_add_to_watchlist -v

# Run with coverage
pytest tests/test_watchlist_manager.py --cov=services.watchlist_manager --cov-report=html
```

## Performance Considerations

- **Database Indexes**: The system uses composite indexes for efficient queries on watchlist and history tables
- **Batch Updates**: Daily updates process all stocks in a single transaction
- **History Retention**: Consider implementing a cleanup policy for old history records (e.g., keep last 365 days)

## Best Practices

1. **Daily Updates**: Run daily updates after market close to capture latest data
2. **Criteria Checks**: Periodically run criteria checks to remove underperforming stocks
3. **Export Regularly**: Export your watchlist for backup and external analysis
4. **Review History**: Use historical performance data to refine your selection criteria
5. **Tag Organization**: Use consistent tags for easier filtering and organization

## Troubleshooting

### Common Issues

**Issue**: Stock not found when adding to watchlist
- **Solution**: Ensure the stock exists in the database. Run data collection first.

**Issue**: No history snapshots created
- **Solution**: Ensure price and score data is available for the stock.

**Issue**: Export fails
- **Solution**: Check file permissions and disk space. Ensure output directory exists.

## Future Enhancements

Potential future features:

- Real-time price alerts
- Email/SMS notifications for criteria violations
- Advanced charting and visualization
- Portfolio integration
- Backtest watchlist performance
- Machine learning-based reason generation

## Contributing

When contributing to the watchlist manager:

1. Add tests for new features
2. Update this README with new functionality
3. Follow the existing code style
4. Update the database migration if schema changes

## License

Part of the Korean Stock Trading System project.

## Support

For issues and questions:
- Check the examples in `example_usage.py`
- Review test cases in `tests/test_watchlist_manager.py`
- Refer to the main project documentation
