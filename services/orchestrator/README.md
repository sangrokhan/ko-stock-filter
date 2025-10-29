# Trading System Orchestrator

The Orchestrator Service coordinates all trading system operations with timezone-aware scheduling using APScheduler.

## Features

- **Automated Data Collection**: Runs daily at 16:00 (after market close)
- **Indicator Calculation**: Runs daily at 17:00
- **Watchlist Updates**: Runs daily at 18:00
- **Signal Generation**: Runs daily at 08:45 (before market open)
- **Position Monitoring**: Every 15 minutes during market hours (09:00-15:30)
- **Risk Limit Checks**: Every 30 minutes throughout the day

All schedules use **Asia/Seoul** timezone by default.

## Installation

Ensure APScheduler is installed:

```bash
pip install -r requirements.txt
```

## Usage

### Start the Orchestrator

Start with default settings (dry-run mode):

```bash
python -m services.orchestrator.main start
```

Start with custom user and portfolio value:

```bash
python -m services.orchestrator.main start --user-id trader1 --portfolio-value 50000000
```

### Dry-Run vs Live Trading

**Dry-Run Mode (Default)**: Simulates trading without executing real orders

```bash
python -m services.orchestrator.main start --dry-run
```

**Live Trading Mode** (CAUTION: Executes real trades):

```bash
python -m services.orchestrator.main start --no-dry-run
```

### Disable Specific Jobs

You can disable specific scheduled jobs:

```bash
# Disable signal generation and position monitoring
python -m services.orchestrator.main start \
  --disable-signal-generation \
  --disable-position-monitoring
```

Available disable flags:
- `--disable-data-collection`
- `--disable-indicator-calculation`
- `--disable-watchlist-update`
- `--disable-signal-generation`
- `--disable-position-monitoring`
- `--disable-risk-checks`

### Run a Specific Job Immediately

Run a single job without starting the full orchestrator:

```bash
# Run data collection now
python -m services.orchestrator.main run-job data_collection

# Run signal generation now
python -m services.orchestrator.main run-job signal_generation
```

Available jobs:
- `data_collection`
- `indicator_calculation`
- `watchlist_update`
- `signal_generation`
- `position_monitoring`
- `risk_checks`

### Check Status

Show the scheduled configuration:

```bash
python -m services.orchestrator.main status --user-id trader1
```

## Configuration

Configuration can be set via environment variables or command-line arguments.

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Orchestrator settings
ORCHESTRATOR_TIMEZONE=Asia/Seoul
ORCHESTRATOR_USER_ID=default_user
ORCHESTRATOR_DRY_RUN=true
ORCHESTRATOR_PORTFOLIO_VALUE=100000000

# Schedule times (24-hour format)
ORCHESTRATOR_DATA_COLLECTION_TIME=16:00
ORCHESTRATOR_INDICATOR_CALCULATION_TIME=17:00
ORCHESTRATOR_WATCHLIST_UPDATE_TIME=18:00
ORCHESTRATOR_SIGNAL_GENERATION_TIME=08:45

# Market hours
ORCHESTRATOR_MARKET_OPEN_TIME=09:00
ORCHESTRATOR_MARKET_CLOSE_TIME=15:30

# Intervals (in minutes)
ORCHESTRATOR_POSITION_MONITOR_INTERVAL=15
ORCHESTRATOR_RISK_CHECK_INTERVAL=30

# Enable/disable specific jobs
ORCHESTRATOR_ENABLE_DATA_COLLECTION=true
ORCHESTRATOR_ENABLE_INDICATOR_CALCULATION=true
ORCHESTRATOR_ENABLE_WATCHLIST_UPDATE=true
ORCHESTRATOR_ENABLE_SIGNAL_GENERATION=true
ORCHESTRATOR_ENABLE_POSITION_MONITORING=true
ORCHESTRATOR_ENABLE_RISK_CHECKS=true

# Risk parameters
ORCHESTRATOR_MAX_POSITION_SIZE_PCT=10.0
ORCHESTRATOR_MAX_POSITIONS=20
```

### Command-Line Arguments

Override configuration with command-line arguments:

```bash
python -m services.orchestrator.main start \
  --user-id trader1 \
  --timezone Asia/Seoul \
  --portfolio-value 50000000 \
  --dry-run
```

## Schedule Details

### Korean Stock Market Hours

- **Market Open**: 09:00 KST
- **Market Close**: 15:30 KST
- **Trading Days**: Monday - Friday (excluding holidays)

### Daily Schedule

| Time  | Job                      | Description                                    |
|-------|--------------------------|------------------------------------------------|
| 08:45 | Signal Generation        | Generate entry/exit signals before market open|
| 09:00 | Market Open              | Position monitoring starts                     |
| 09:00-15:30 | Position Monitoring | Check positions every 15 minutes            |
| 15:30 | Market Close             | Position monitoring pauses                     |
| 16:00 | Data Collection          | Collect daily price and fundamental data       |
| 17:00 | Indicator Calculation    | Calculate technical and financial indicators   |
| 18:00 | Watchlist Update         | Update watchlist with latest scores            |

### Continuous Monitoring

- **Risk Checks**: Every 30 minutes (24/7)
- **Position Monitoring**: Every 15 minutes during market hours only

## Architecture

The orchestrator coordinates these services:

1. **Data Collector** (`services/data_collector`)
   - Collects stock codes, prices, and fundamentals from KRX

2. **Indicator Calculator** (`services/indicator_calculator`)
   - Calculates technical indicators (RSI, MACD, etc.)
   - Calculates financial indicators

3. **Watchlist Manager** (`services/watchlist_manager`)
   - Maintains and updates stock watchlists
   - Tracks performance

4. **Trading Engine** (`services/trading_engine`)
   - Generates entry/exit signals
   - Executes orders (paper or live)
   - Monitors positions

5. **Risk Manager** (`services/risk_manager`)
   - Calculates portfolio metrics
   - Enforces risk limits
   - Monitors drawdowns

## Logging

The orchestrator logs all operations:

- Job execution start/end
- Success/failure status
- Statistics and summaries
- Errors and warnings

Logs use INFO level by default. Set to DEBUG for more detail:

```bash
export LOG_LEVEL=DEBUG
python -m services.orchestrator.main start
```

## Error Handling

- Jobs run independently - failure in one job doesn't stop others
- Missed jobs have 5-minute grace period
- Multiple pending executions are combined (coalesce)
- Only one instance of each job runs at a time

## Safety Features

- **Dry-Run Mode**: Default mode, no real trades executed
- **Trading Halt**: Automatic halt if loss exceeds limits
- **Risk Checks**: Continuous monitoring of portfolio risk
- **Position Limits**: Enforced maximum position sizes
- **Market Hours**: Position monitoring only during trading hours

## Shutdown

Stop the orchestrator gracefully with Ctrl+C or SIGTERM. All running jobs will complete before shutdown.

## Examples

### Development Setup

```bash
# Start orchestrator in dry-run mode with all jobs enabled
python -m services.orchestrator.main start \
  --user-id dev_user \
  --portfolio-value 10000000 \
  --dry-run
```

### Production Setup

```bash
# Start orchestrator in live mode (CAUTION!)
python -m services.orchestrator.main start \
  --user-id prod_user \
  --portfolio-value 100000000 \
  --no-dry-run
```

### Testing Individual Jobs

```bash
# Test data collection
python -m services.orchestrator.main run-job data_collection

# Test signal generation
python -m services.orchestrator.main run-job signal_generation

# Test risk checks
python -m services.orchestrator.main run-job risk_checks
```

## Monitoring

Check orchestrator logs for:
- Job execution times
- Success/failure status
- Trading activity
- Risk alerts
- Position alerts

Use external monitoring tools to:
- Track orchestrator uptime
- Alert on job failures
- Monitor portfolio metrics
- Track trading performance

## Troubleshooting

### Jobs Not Running

1. Check timezone configuration
2. Verify scheduler is started
3. Check logs for errors
4. Ensure database is accessible

### Position Monitoring Not Working

1. Verify current time is within market hours
2. Check if it's a weekday
3. Verify `enable_position_monitoring` is true

### Risk Checks Showing Halted

1. Review portfolio losses
2. Check `max_total_loss` threshold
3. Review risk metrics in database
4. May need manual intervention to resume trading

## API Integration

The orchestrator can be extended to expose a REST API for:
- Starting/stopping jobs
- Checking status
- Manually triggering jobs
- Updating configuration

(API implementation not included in current version)
