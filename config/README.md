# Configuration Management

This directory contains YAML configuration files for all services in the Korean Stock Trading System. The configuration system uses a combination of YAML files for non-sensitive parameters and environment variables for sensitive data.

## Overview

The configuration system is built on:
- **Pydantic** for type validation and data modeling
- **YAML** files for easy-to-edit service configurations
- **python-dotenv** for environment variable management
- **Hierarchical override**: Environment variables override YAML values

## Directory Structure

```
config/
├── README.md                    # This file
├── trading_engine.yaml          # Trading signal generation & execution
├── risk_manager.yaml            # Risk management & position sizing
├── stock_screener.yaml          # Stock filtering & screening
├── indicator_calculator.yaml    # Technical indicator parameters
├── data_collector.yaml          # Data collection scheduling
├── price_monitor.yaml           # Real-time price monitoring
├── database.yaml                # Database connection settings
├── redis.yaml                   # Redis cache settings
└── logging.yaml                 # Application logging
```

## Configuration Hierarchy

Values are loaded in the following order (later overrides earlier):

1. **YAML default values** (in these files)
2. **Environment variables** (from `.env` file or system)

## Usage

### Basic Usage

```python
from shared.configs.loader import (
    load_trading_engine_config,
    load_risk_manager_config,
    load_stock_screener_config
)

# Load validated configuration
trading_config = load_trading_engine_config()

# Access nested configuration
risk_tolerance = trading_config.signal_generator.risk_tolerance
max_positions = trading_config.signal_validator.max_positions

print(f"Risk Tolerance: {risk_tolerance}%")
print(f"Max Positions: {max_positions}")
```

### Advanced Usage with Custom Config Directory

```python
from shared.configs.loader import ConfigLoader
from shared.configs.models import TradingEngineConfig

# Create loader with custom directory
loader = ConfigLoader(config_dir="/path/to/custom/config")

# Load and validate
config = loader.load_and_validate(
    'trading_engine.yaml',
    TradingEngineConfig,
    env_prefix='TRADING_ENGINE_'
)
```

### Overriding with Environment Variables

Environment variables use underscore notation for nested YAML keys:

**YAML structure:**
```yaml
signal_generator:
  risk_tolerance: 2.0
  max_position_size_pct: 10.0
```

**Environment variable override:**
```bash
# Override risk_tolerance
export TRADING_ENGINE_SIGNAL_GENERATOR_RISK_TOLERANCE=2.5

# Override max_position_size_pct
export TRADING_ENGINE_SIGNAL_GENERATOR_MAX_POSITION_SIZE_PCT=8.0
```

## Configuration Files

### trading_engine.yaml

Configures trading signal generation, validation, and order execution:

- **Signal Generator**: Risk tolerance, conviction weights, position sizing
- **Signal Validator**: Position limits, concentration limits, data quality
- **Commission**: Fee structures, transaction taxes
- **General**: Dry run mode, notifications

Key parameters:
- `signal_generator.risk_tolerance`: Portfolio risk per trade (%)
- `signal_generator.min_conviction_score`: Minimum score to generate signal (0-100)
- `signal_validator.max_positions`: Maximum concurrent positions
- `dry_run`: Enable paper trading mode

### risk_manager.yaml

Configures risk management and position sizing:

- **Risk Parameters**: Stop loss, take profit, max drawdown, leverage
- **Position Sizing**: Method selection, Kelly criterion, fixed percentage
- **Circuit Breaker**: Emergency stop on excessive losses

Key parameters:
- `risk_parameters.max_position_size_pct`: Max single position size (%)
- `risk_parameters.stop_loss_pct`: Default stop loss (%)
- `position_sizing.method`: Position sizing algorithm
- `enable_circuit_breaker`: Enable emergency trading halt

### stock_screener.yaml

Configures stock filtering and screening criteria:

- **Thresholds**: Volatility, valuation (P/E, P/B), financial health, liquidity
- **Sector Filter**: Include/exclude specific sectors
- **Data Requirements**: Minimum history length

Key parameters:
- `thresholds.max_volatility_pct`: Max annualized volatility
- `thresholds.max_per`: Max P/E ratio
- `thresholds.min_avg_volume`: Min daily trading volume

### indicator_calculator.yaml

Configures technical indicator calculation:

- **RSI**: Period, overbought/oversold thresholds
- **MACD**: Fast, slow, and signal periods
- **Moving Averages**: SMA and EMA periods
- **Bollinger Bands**: Period and standard deviation
- **ATR**: Period for volatility measurement

Key parameters:
- `indicators.rsi_period`: RSI lookback period (default: 14)
- `indicators.macd_fast_period`: MACD fast EMA (default: 12)
- `enable_caching`: Cache calculated indicators

### data_collector.yaml

Configures automated data collection:

- **Scheduler**: Cron expressions for market, financial, and fundamental data
- **Retry Policy**: Max retries and delay on failures
- **General**: Batch size, request timeouts

Key parameters:
- `scheduler.market_data_cron`: When to collect market data
- `scheduler.max_retries`: Retry attempts on failure
- `enable_scheduler`: Enable/disable automated collection

### price_monitor.yaml

Configures real-time price monitoring:

- **Polling**: Update frequency
- **Alerts**: Price change threshold for notifications
- **Market Hours**: Trading session times
- **Concurrency**: Max concurrent update operations

Key parameters:
- `poll_interval_seconds`: How often to check prices
- `significant_change_threshold_pct`: Alert threshold (%)
- `alert_enabled`: Enable price alerts

## Environment Variables

Sensitive configuration (API keys, credentials) should be set in `.env` file. See `.env.example` for template.

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/stock_trading

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API Keys
KOREAINVESTMENT_API_KEY=your_key_here
KOREAINVESTMENT_API_SECRET=your_secret_here
KRX_API_KEY=your_key_here
```

### Optional Overrides

Any YAML parameter can be overridden via environment variables using the format:

```
{SERVICE_PREFIX}_{SECTION}_{PARAMETER}
```

Examples:
```bash
TRADING_ENGINE_DRY_RUN=false
RISK_MANAGER_RISK_PARAMETERS_STOP_LOSS_PCT=7.0
STOCK_SCREENER_THRESHOLDS_MAX_PER=40.0
```

## Configuration Validation

All configurations are validated using Pydantic models on startup:

- **Type checking**: Ensures correct data types
- **Range validation**: Values within acceptable ranges
- **Required fields**: Mandatory parameters must be set
- **Custom validation**: Business logic validation (e.g., weights sum to 1.0)

If validation fails, the system will raise a `ConfigurationError` with detailed error messages.

## Best Practices

### 1. Separation of Concerns
- **YAML files**: Non-sensitive parameters, easily adjustable
- **.env file**: Sensitive data (API keys, passwords)
- **Never commit** `.env` file to version control

### 2. Development vs Production

Create separate `.env` files:
```bash
.env.development
.env.production
.env.test
```

Use environment variable to select:
```bash
export ENV=production
```

### 3. Configuration Changes

To change configuration:

1. **For non-sensitive parameters**: Edit YAML files directly
2. **For sensitive data**: Update `.env` file
3. **For temporary overrides**: Use environment variables
4. **Restart services** after changes

### 4. Validation

Always validate configuration changes:

```python
from shared.configs.loader import load_trading_engine_config

try:
    config = load_trading_engine_config()
    print("Configuration valid!")
except Exception as e:
    print(f"Configuration error: {e}")
```

### 5. Documentation

When adding new parameters:
1. Add to appropriate Pydantic model in `shared/configs/models.py`
2. Add to YAML file with sensible default
3. Document in this README
4. Add example override to `.env.example`

## Troubleshooting

### Configuration file not found

**Error**: `Config file not found: /path/to/config/file.yaml`

**Solution**: Ensure config files exist in `/config` directory relative to project root.

### Validation failed

**Error**: `Configuration validation failed for trading_engine.yaml`

**Solution**: Check error message for specific validation errors. Common issues:
- Invalid data type (e.g., string instead of number)
- Value out of range (e.g., percentage > 100)
- Required field missing
- Weights don't sum to 1.0

### Environment variable not working

**Problem**: Environment variable not overriding YAML value

**Solution**:
1. Check variable name format: `{PREFIX}_{SECTION}_{PARAM}`
2. Ensure underscores for nested keys
3. Verify `.env` file is in project root
4. Check for typos in variable name

### YAML syntax error

**Error**: `Invalid YAML in /path/to/config/file.yaml`

**Solution**:
1. Check YAML indentation (use spaces, not tabs)
2. Ensure colons followed by space
3. Validate YAML syntax with online validator

## Examples

See `examples/config_usage_example.py` for complete usage examples.

## Support

For issues or questions:
1. Check this README
2. Review `.env.example` for configuration options
3. Examine Pydantic models in `shared/configs/models.py`
4. Consult service documentation
