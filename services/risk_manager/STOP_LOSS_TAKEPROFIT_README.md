# Stop-Loss and Take-Profit System

Comprehensive risk management system with automated stop-loss, trailing stop-loss, take-profit, and position sizing features.

## Features

### 1. Individual Stock Stop-Loss (-10%)
- Each position has a configurable stop-loss threshold (default: -10%)
- Automatically triggers exit signal when price falls below stop-loss price
- Calculated as: `stop_loss_price = avg_price * (1 - stop_loss_pct / 100)`

### 2. Trailing Stop-Loss
- Moves up automatically as stock price increases
- Never moves down - locks in profits
- Distance from highest price is configurable (default: 10%)
- Triggers when price falls below trailing stop price
- **Example:**
  - Buy at 70,000 KRW
  - Price rises to 90,000 KRW
  - Trailing stop moves up to 81,000 KRW (10% below peak)
  - Price falls to 80,000 KRW (still held)
  - Price falls to 79,000 KRW (trailing stop triggered - exit)

### 3. Take-Profit (+20%)
- Configurable take-profit target (default: +20%)
- Can use absolute price or technical signals
- Technical signals include:
  - RSI > 70 (overbought)
  - MACD bearish crossover
  - Price above upper Bollinger Band
  - Price significantly above moving averages
- Requires 2+ technical signals to trigger

### 4. Position Sizing (Kelly Criterion)
Multiple position sizing methods available:

#### **Kelly Criterion** (Optimal Bet Sizing)
- Calculates optimal position size based on historical win rate and profit/loss ratio
- Formula: `f* = (p * b - q) / b`
  - p = win rate
  - b = avg_win / avg_loss ratio
  - q = 1 - p
- **Conservative variations:**
  - **Half Kelly** (default): 50% of full Kelly - more conservative
  - **Quarter Kelly**: 25% of full Kelly - very conservative

#### **Fixed Percent**
- Fixed percentage of portfolio per position (e.g., 5%)
- Simple and predictable

#### **Fixed Risk**
- Fixed dollar/percentage risk per trade (e.g., 2%)
- Based on stop-loss distance

#### **Volatility Adjusted**
- Position size inversely proportional to volatility
- Higher volatility = smaller position

### 5. Emergency Liquidation (28% Portfolio Loss)
- Automatic liquidation of all positions if portfolio loss exceeds 28%
- Critical safety measure to prevent catastrophic losses
- Generates "emergency_liquidation" signals with highest urgency
- Trading is halted until manual review and resume

## Database Schema

### Portfolio Model (Updated)
```python
# Stop-Loss and Take-Profit Fields
stop_loss_price: Decimal              # Stop-loss trigger price
stop_loss_pct: Float = 10.0          # Stop-loss percentage
trailing_stop_price: Decimal          # Trailing stop-loss price
trailing_stop_enabled: Bool = True    # Enable trailing stop
trailing_stop_distance_pct: Float = 10.0  # Trailing stop distance
highest_price_since_purchase: Decimal     # Highest price achieved
take_profit_price: Decimal            # Take-profit trigger price
take_profit_pct: Float = 20.0        # Take-profit percentage
take_profit_use_technical: Bool = False  # Use technical signals
```

## API Endpoints

### Position Sizing

#### Calculate Position Size (with Kelly Criterion)
```bash
POST /position-size/calculate
```

**Parameters:**
- `ticker`: Stock ticker
- `entry_price`: Entry price per share
- `stop_loss_price`: Stop-loss price
- `portfolio_value`: Total portfolio value
- `method`: Sizing method (default: "kelly_half")
  - Options: kelly_criterion, kelly_half, kelly_quarter, fixed_percent, fixed_risk, volatility_adjusted
- `user_id`: User ID (optional, for historical performance)

**Response:**
```json
{
  "ticker": "005930",
  "entry_price": 70000,
  "stop_loss_price": 63000,
  "portfolio_value": 100000000,
  "recommended_shares": 275,
  "position_value": 19250000,
  "position_pct": 19.25,
  "method": "Kelly Criterion (fraction=0.5)",
  "kelly_fraction": 0.193,
  "risk_amount": 2000000,
  "notes": "Full Kelly=38.6%, Adjusted Kelly=19.3%"
}
```

### Position Limit Management

#### Initialize Position Limits
```bash
POST /portfolio/{user_id}/positions/{ticker}/initialize-limits
```

**Parameters:**
- `stop_loss_pct`: Stop-loss percentage (default: 10.0)
- `take_profit_pct`: Take-profit percentage (default: 20.0)
- `trailing_stop_enabled`: Enable trailing stop (default: true)
- `trailing_stop_distance_pct`: Trailing stop distance (default: 10.0)

**Example:**
```bash
curl -X POST "http://localhost:8005/portfolio/user123/positions/005930/initialize-limits?stop_loss_pct=10.0&take_profit_pct=20.0"
```

#### Update Position Limits
```bash
PUT /portfolio/{user_id}/positions/{ticker}/limits
```

**Body:**
```json
{
  "stop_loss_pct": 12.0,
  "take_profit_pct": 25.0,
  "trailing_stop_enabled": true,
  "trailing_stop_distance_pct": 8.0,
  "take_profit_use_technical": true
}
```

#### Get Position Limits
```bash
GET /portfolio/{user_id}/positions/{ticker}/limits
```

#### Get All Positions Limits
```bash
GET /portfolio/{user_id}/all-positions-limits
```

### Position Monitoring

#### Monitor Positions
```bash
POST /portfolio/{user_id}/monitor
```

Checks all positions for:
- Stop-loss triggers
- Trailing stop triggers
- Take-profit triggers
- Emergency liquidation conditions

**Response:**
```json
{
  "user_id": "user123",
  "positions_checked": 5,
  "exit_signals_count": 2,
  "exit_signals": [
    {
      "ticker": "005930",
      "signal_type": "stop_loss",
      "current_price": 62000,
      "trigger_price": 63000,
      "quantity": 10,
      "reason": "Stop-loss triggered: Price 62,000 <= Stop 63,000 (Loss: -11.43%)",
      "urgency": "high",
      "technical_signals": null
    },
    {
      "ticker": "000660",
      "signal_type": "take_profit",
      "current_price": 61000,
      "trigger_price": 60000,
      "quantity": 20,
      "reason": "Take-profit triggered: Price 61,000 >= Target 60,000 (Profit: 22.00%)",
      "urgency": "normal",
      "technical_signals": null
    }
  ],
  "trailing_stops_updated": 3,
  "warnings": [],
  "emergency_liquidation_triggered": false
}
```

## Usage Examples

### 1. Opening a New Position

```python
import requests

# Step 1: Calculate position size using Kelly Criterion
response = requests.post(
    "http://localhost:8005/position-size/calculate",
    params={
        "ticker": "005930",
        "entry_price": 70000,
        "stop_loss_price": 63000,
        "portfolio_value": 100000000,
        "method": "kelly_half",
        "user_id": "user123"
    }
)
sizing = response.json()
shares_to_buy = sizing['recommended_shares']

# Step 2: Execute buy order (your trading logic here)
# ... buy 275 shares at 70,000 KRW

# Step 3: Initialize stop-loss and take-profit limits
response = requests.post(
    f"http://localhost:8005/portfolio/user123/positions/005930/initialize-limits",
    params={
        "stop_loss_pct": 10.0,
        "take_profit_pct": 20.0,
        "trailing_stop_enabled": True,
        "trailing_stop_distance_pct": 10.0
    }
)
print(response.json())
```

### 2. Monitoring Positions (Run Periodically)

```python
import requests
import time

def monitor_loop():
    """Monitor positions every minute."""
    while True:
        response = requests.post("http://localhost:8005/portfolio/user123/monitor")
        result = response.json()

        if result['exit_signals_count'] > 0:
            print(f"⚠️  {result['exit_signals_count']} exit signals!")

            for signal in result['exit_signals']:
                print(f"  {signal['ticker']}: {signal['signal_type']} - {signal['reason']}")

                # Execute sell order based on signal
                if signal['urgency'] == 'critical':
                    # Emergency liquidation - sell immediately at market
                    execute_market_sell(signal['ticker'], signal['quantity'])
                elif signal['urgency'] == 'high':
                    # Stop-loss or trailing stop - sell quickly
                    execute_limit_sell(signal['ticker'], signal['quantity'], signal['current_price'])
                else:
                    # Take-profit - can use limit order
                    execute_limit_sell(signal['ticker'], signal['quantity'], signal['trigger_price'])

        if result['trailing_stops_updated'] > 0:
            print(f"✅ Updated {result['trailing_stops_updated']} trailing stops")

        time.sleep(60)  # Check every minute

monitor_loop()
```

### 3. Adjusting Position Limits

```python
import requests

# Update stop-loss to be tighter (8% instead of 10%)
response = requests.put(
    "http://localhost:8005/portfolio/user123/positions/005930/limits",
    json={
        "stop_loss_pct": 8.0,
        "take_profit_pct": 25.0,
        "trailing_stop_enabled": True,
        "trailing_stop_distance_pct": 8.0
    }
)
print(response.json())
```

### 4. Viewing All Position Limits

```python
import requests

response = requests.get("http://localhost:8005/portfolio/user123/all-positions-limits")
data = response.json()

print(f"Total positions: {data['count']}")
for position in data['positions']:
    print(f"\n{position['ticker']}:")
    print(f"  Quantity: {position['quantity']}")
    print(f"  Avg Price: {position['avg_price']:,.0f} KRW")
    print(f"  Current Price: {position['current_price']:,.0f} KRW")
    print(f"  P&L: {position['unrealized_pnl_pct']:.2f}%")
    print(f"  Stop-Loss: {position['stop_loss_price']:,.0f} KRW ({position['stop_loss_pct']}%)")
    print(f"  Take-Profit: {position['take_profit_price']:,.0f} KRW ({position['take_profit_pct']}%)")
    if position['trailing_stop_enabled']:
        print(f"  Trailing Stop: {position['trailing_stop_price']:,.0f} KRW")
        print(f"  Highest Price: {position['highest_price_since_purchase']:,.0f} KRW")
```

## Position Sizing Strategy Comparison

| Method | Risk Level | Recommended For | Pros | Cons |
|--------|-----------|-----------------|------|------|
| **Kelly Criterion** | High | Experienced traders with good historical data | Optimal long-term growth | Can be aggressive, requires accurate inputs |
| **Half Kelly** | Medium | Most traders (default) | Balanced growth and safety | Still requires historical data |
| **Quarter Kelly** | Low | Conservative traders | Very safe | Lower returns |
| **Fixed Percent** | Medium | Consistent position sizes | Simple, predictable | Doesn't account for risk |
| **Fixed Risk** | Medium | Risk-conscious traders | Controls loss per trade | Position sizes vary widely |
| **Volatility Adjusted** | Medium | Diversified portfolios | Accounts for stock risk | Requires volatility data |

## Risk Management Parameters

### Default Settings
```python
max_position_size = 10.0%          # Max single position
max_portfolio_risk = 2.0%          # Max risk per trade
max_drawdown = 20.0%               # Max drawdown before warning
stop_loss_pct = 10.0%              # Individual stock stop-loss
max_total_loss = 28.0%             # Emergency liquidation threshold
```

### Customizing Parameters
```python
from services.risk_manager.main import RiskManagerService, RiskParameters

# Create custom risk parameters
custom_params = RiskParameters(
    max_position_size=8.0,         # More conservative 8% max
    max_portfolio_risk=1.5,        # Lower risk per trade
    max_drawdown=15.0,             # Tighter drawdown limit
    stop_loss_pct=8.0,             # Tighter stop-loss
    max_leverage=1.0,              # No leverage
    max_total_loss=25.0            # Lower emergency threshold
)

# Initialize service with custom parameters
risk_manager = RiskManagerService(risk_params=custom_params)
```

## Testing

Run the test suite:

```bash
# Test position monitor
pytest services/risk_manager/tests/test_position_monitor.py -v

# Test position sizing
pytest services/risk_manager/tests/test_position_sizing.py -v

# Run all risk manager tests
pytest services/risk_manager/tests/ -v
```

## Integration with Trading System

### 1. Before Opening Position
1. Calculate position size using Kelly Criterion or other method
2. Validate order against risk limits
3. Execute buy order
4. Initialize stop-loss and take-profit limits

### 2. During Position Holding
1. Monitor positions periodically (every minute recommended)
2. Update trailing stops as prices rise
3. Generate exit signals when limits are breached

### 3. Position Exit
1. Receive exit signal from monitor
2. Execute sell order based on urgency:
   - **Critical**: Market order (emergency liquidation)
   - **High**: Limit order near current price (stop-loss/trailing stop)
   - **Normal**: Limit order at target price (take-profit)

### 4. After Position Close
1. Update portfolio metrics
2. Record trade for historical performance
3. Use historical data to improve Kelly Criterion calculations

## Emergency Procedures

### If 28% Loss Threshold is Reached
1. All positions are flagged for emergency liquidation
2. Trading is automatically halted
3. Manual review required before resuming
4. Use `/portfolio/{user_id}/resume-trading` endpoint to resume (admin only)

### If Individual Stop-Loss is Hit
1. Exit signal generated with "high" urgency
2. Sell position quickly to limit further losses
3. Review why stop-loss was hit
4. Adjust strategy if needed

## Best Practices

1. **Start Conservative**: Use Half Kelly or Quarter Kelly initially
2. **Monitor Regularly**: Check positions at least every 5-10 minutes during trading hours
3. **Respect Signals**: Always act on emergency liquidation signals immediately
4. **Adjust Gradually**: Don't make dramatic changes to risk parameters
5. **Track History**: Maintain good trade history for accurate Kelly calculations
6. **Use Trailing Stops**: Enable trailing stops to lock in profits automatically
7. **Technical Signals**: Enable technical take-profit for more sophisticated exits
8. **Test First**: Always test with small positions before scaling up

## Performance Metrics

The system tracks:
- Win rate
- Average win percentage
- Average loss percentage
- Profit factor
- Sharpe ratio
- Current drawdown
- Maximum drawdown
- Total loss from initial capital

Access these via `/portfolio/{user_id}/risk-status` endpoint.

## Support

For issues or questions:
1. Check API documentation: `http://localhost:8005/docs`
2. Review logs: Risk manager logs all important decisions
3. Test in isolation: Use test suite to verify behavior
4. Monitor closely: Watch the first few trades carefully

## Version History

- **v2.0.0** (2025-10-28):
  - Added stop-loss and take-profit logic
  - Implemented trailing stop-loss
  - Added Kelly Criterion position sizing
  - Reduced emergency liquidation to 28%
  - Added comprehensive API endpoints
  - Added technical signal take-profit
