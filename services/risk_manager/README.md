# Risk Management System

Comprehensive portfolio risk management system for Korean stock trading platform.

## Features

### 1. Portfolio Value & P&L Tracking
- **Total Portfolio Value**: Real-time calculation of portfolio value (positions + cash)
- **P&L Calculation**:
  - Total P&L (realized + unrealized)
  - Realized P&L from closed positions
  - Unrealized P&L from open positions
  - Daily P&L tracking

### 2. Position Size Management
- **Individual Position Tracking**: Monitor each position's size relative to portfolio
- **Position Limits**: Enforce maximum position size (default: 10% of portfolio)
- **Position Concentration Analysis**: Track largest positions and concentration risk
- **Automated Position Sizing**: Calculate optimal position sizes based on risk parameters

### 3. Drawdown Monitoring
- **Current Drawdown**: Real-time drawdown from peak portfolio value
- **Maximum Drawdown**: Track worst historical drawdown
- **Peak Value Tracking**: Monitor all-time high portfolio value
- **Drawdown Duration**: Track days since peak value

### 4. Loss Limits & Trading Halt
- **30% Maximum Loss Limit**: Automatically halt trading when total loss reaches 30%
- **Loss Tracking**: Monitor loss from initial capital and peak value
- **Trading Halt Enforcement**: Prevent new buy orders when limit is reached
- **Manual Override**: Admin function to resume trading after review

### 5. Risk Validation
- **Order Validation**: Check all orders against risk parameters before execution
- **Position Size Validation**: Ensure orders don't exceed position size limits
- **Cash Balance Checks**: Verify sufficient funds for orders
- **Risk Warnings**: Provide early warnings as limits are approached

## Architecture

### Components

1. **RiskManagerService** (`main.py`)
   - Core risk management logic
   - Portfolio metrics calculation
   - Order validation
   - Risk assessment

2. **REST API** (`api.py`)
   - FastAPI endpoints for risk management
   - Portfolio monitoring
   - Order validation
   - Risk status reporting

3. **Risk Monitor** (`utils/risk_monitor.py`)
   - Continuous monitoring service
   - Automated alerts
   - Periodic risk updates

4. **Risk Reporter** (`utils/risk_report.py`)
   - Comprehensive risk reports
   - Trend analysis
   - Recommendations

5. **Database Model** (`PortfolioRiskMetrics`)
   - Historical risk metrics
   - Trading halt status
   - Performance tracking

## Database Schema

### PortfolioRiskMetrics Table

Tracks comprehensive portfolio-level risk metrics:

- **Value Metrics**: total_value, cash_balance, invested_amount, peak_value, initial_capital
- **P&L Metrics**: total_pnl, realized_pnl, unrealized_pnl, daily_pnl
- **Drawdown Metrics**: current_drawdown, max_drawdown, drawdown_duration_days
- **Position Metrics**: position_count, largest_position_pct, total_exposure_pct
- **Loss Tracking**: total_loss_from_initial, total_loss_from_initial_pct
- **Risk Status**: is_trading_halted, trading_halt_reason, risk_warnings

## Risk Parameters

Default risk parameters (configurable):

```python
RiskParameters(
    max_position_size=10.0,      # 10% maximum per position
    max_portfolio_risk=2.0,      # 2% portfolio risk per trade
    max_drawdown=20.0,           # 20% maximum drawdown
    stop_loss_pct=5.0,           # 5% stop loss
    max_leverage=1.0,            # No leverage
    max_total_loss=30.0          # 30% maximum total loss (TRADING HALT)
)
```

## Installation

### 1. Database Migration

Run the migration to create the `portfolio_risk_metrics` table:

```bash
cd services/risk_manager/migrations
python add_portfolio_risk_metrics.py
```

To rollback (WARNING: deletes data):

```bash
python add_portfolio_risk_metrics.py --rollback
```

### 2. Start the API Server

```bash
cd services/risk_manager
python api.py
```

The API will be available at `http://localhost:8005`

### 3. Start Risk Monitor (Optional)

For continuous monitoring:

```bash
cd services/risk_manager/utils
python risk_monitor.py --interval 60
```

For a single check:

```bash
python risk_monitor.py --once
```

## Usage

### Initialize Portfolio

Before using risk management, initialize a portfolio with initial capital:

```bash
curl -X POST "http://localhost:8005/portfolio/user123/initialize" \
  -H "Content-Type: application/json" \
  -d '{"initial_capital": 10000000, "cash_balance": 10000000}'
```

### Validate Order

Before placing an order, validate it against risk limits:

```bash
curl -X POST "http://localhost:8005/orders/user123/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "005930",
    "side": "BUY",
    "quantity": 10,
    "price": 70000
  }'
```

Response:
```json
{
  "is_valid": true,
  "reason": "Order validated successfully",
  "warnings": [],
  "suggested_quantity": null
}
```

### Get Portfolio Metrics

```bash
curl "http://localhost:8005/portfolio/user123/metrics"
```

Response:
```json
{
  "user_id": "user123",
  "total_value": 9500000,
  "total_pnl": -500000,
  "total_pnl_pct": -5.0,
  "current_drawdown": 5.0,
  "total_loss_from_initial_pct": 5.0,
  "is_trading_halted": false,
  "position_count": 3,
  "largest_position_pct": 8.5
}
```

### Check if Trading is Allowed

```bash
curl "http://localhost:8005/portfolio/user123/is-trading-allowed"
```

Response:
```json
{
  "is_trading_allowed": true,
  "is_trading_halted": false,
  "total_loss_pct": 5.0,
  "max_loss_limit": 30.0,
  "reason": "Trading allowed"
}
```

### Get Risk Status

```bash
curl "http://localhost:8005/portfolio/user123/risk-status"
```

Response:
```json
{
  "status": "OK",
  "metrics": {
    "total_value": 9500000,
    "current_drawdown": 5.0,
    "total_loss_from_initial_pct": 5.0
  },
  "violations": [],
  "warnings": []
}
```

### Update Risk Metrics

Manually trigger metrics calculation and update:

```bash
curl -X POST "http://localhost:8005/portfolio/user123/update-metrics"
```

### Generate Risk Report

```bash
cd services/risk_manager/utils
python risk_report.py --user user123
```

For JSON output:
```bash
python risk_report.py --user user123 --json
```

## API Endpoints

### Portfolio Management
- `POST /portfolio/{user_id}/initialize` - Initialize portfolio with capital
- `GET /portfolio/{user_id}/metrics` - Get current portfolio metrics
- `POST /portfolio/{user_id}/update-metrics` - Update risk metrics
- `GET /portfolio/{user_id}/summary` - Get comprehensive summary
- `GET /portfolio/{user_id}/risk-status` - Get risk status
- `GET /portfolio/{user_id}/risk-history` - Get historical metrics
- `GET /portfolio/{user_id}/is-trading-allowed` - Check if trading allowed

### Order Validation
- `POST /orders/{user_id}/validate` - Validate order against risk limits

### Position Sizing
- `POST /position-size/calculate` - Calculate recommended position size

### Risk Parameters
- `GET /risk-parameters` - Get current risk parameters
- `PUT /risk-parameters` - Update risk parameters

### Service Control
- `POST /start` - Start risk manager service
- `POST /stop` - Stop risk manager service
- `POST /portfolio/{user_id}/resume-trading` - Resume trading (admin)

## Risk Scenarios

### Scenario 1: Normal Trading
- Loss < 30%
- Position sizes within limits
- Drawdown acceptable
- **Status**: Trading allowed

### Scenario 2: Warning Level (24-29% loss)
- Loss approaching 30% limit
- Risk warnings issued
- Position validation more strict
- **Status**: Trading allowed with warnings

### Scenario 3: Trading Halt (≥30% loss)
- Loss reached 30% limit
- All BUY orders blocked
- SELL orders still allowed (risk reduction)
- Manual review required
- **Status**: Trading halted

### Scenario 4: Position Size Violation
- Position exceeds 10% of portfolio
- Order rejected
- Suggested quantity provided
- **Status**: Order rejected

## Monitoring & Alerts

The risk monitor continuously checks:

1. **Trading Halt Status**: Critical alert if 30% loss reached
2. **Loss Approaching Limit**: Warning at 24% (80% of limit)
3. **Drawdown Exceeded**: Warning if drawdown > max_drawdown
4. **Position Concentration**: Warning if position > max_position_size

Alert levels:
- **CRITICAL**: Immediate action required (trading halted)
- **WARNING**: Review and potential action needed
- **INFO**: Informational, monitor closely

## Best Practices

1. **Initialize Portfolio Properly**: Always set initial_capital correctly
2. **Update Metrics Regularly**: Run risk monitor or update manually
3. **Monitor Warnings**: Act on warnings before critical limits
4. **Review Trading Halts**: Don't resume without addressing issues
5. **Diversify Positions**: Keep positions below 10% limit
6. **Use Stop Losses**: Set appropriate stop losses on positions
7. **Regular Reports**: Generate risk reports weekly

## Integration with Trading Engine

The risk management system should be integrated into the trading flow:

```python
from services.risk_manager.main import RiskManagerService

risk_manager = RiskManagerService()

# Before placing order
order = {'ticker': '005930', 'side': 'BUY', 'quantity': 10, 'price': 70000}
validation = risk_manager.validate_order(order, user_id, db)

if validation.is_valid:
    # Place order
    trading_engine.place_order(order)
else:
    # Reject order
    logger.warning(f"Order rejected: {validation.reason}")
    if validation.suggested_quantity:
        logger.info(f"Suggested quantity: {validation.suggested_quantity}")
```

## Testing

Example test scenarios:

```python
# Test 1: Validate order within limits
order = {'ticker': '005930', 'side': 'BUY', 'quantity': 10, 'price': 70000}
result = risk_manager.validate_order(order, 'user123', db)
assert result.is_valid == True

# Test 2: Reject oversized position
order = {'ticker': '005930', 'side': 'BUY', 'quantity': 1000, 'price': 70000}
result = risk_manager.validate_order(order, 'user123', db)
assert result.is_valid == False
assert result.suggested_quantity is not None

# Test 3: Block trading when halted
metrics = risk_manager.calculate_portfolio_metrics('user123', db)
assert metrics.is_trading_halted == (metrics.total_loss_from_initial_pct >= 30.0)

# Test 4: Allow sell orders when halted
order = {'ticker': '005930', 'side': 'SELL', 'quantity': 10, 'price': 70000}
result = risk_manager.validate_order(order, 'user123', db)
assert result.is_valid == True  # Always allow risk reduction
```

## Troubleshooting

### Trading Unexpectedly Halted
- Check `total_loss_from_initial_pct`
- Verify `initial_capital` was set correctly
- Review trade history for large losses

### Position Size Rejected
- Check current portfolio value
- Verify existing position sizes
- Consider suggested_quantity from validation

### Metrics Not Updating
- Ensure risk monitor is running
- Check database connectivity
- Manually trigger update via API

### False Positive Alerts
- Review risk parameters
- Adjust thresholds if needed
- Check initial_capital accuracy

## Support

For issues or questions:
1. Check logs: `services/risk_manager/` directory
2. Review API documentation: `http://localhost:8005/docs`
3. Generate risk report for detailed analysis
4. Contact development team

## License

Part of ko-stock-filter trading system.
