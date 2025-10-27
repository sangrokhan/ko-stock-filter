# Database Schema Documentation

This document describes the PostgreSQL database schema for the Korean Stock Trading System, implemented with SQLAlchemy ORM and Alembic migrations.

## Table of Contents

- [Overview](#overview)
- [Tables](#tables)
- [Schema Diagram](#schema-diagram)
- [Setup Instructions](#setup-instructions)
- [Migration Management](#migration-management)
- [Usage Examples](#usage-examples)

## Overview

The database schema is designed to support:
- Stock information and metadata
- Historical and real-time price data
- Technical indicators (RSI, MACD, Moving Averages, etc.)
- Fundamental indicators (PER, PBR, ROE, Financial Ratios)
- Trading history and order management
- Portfolio tracking
- Watchlist management

## Tables

### 1. stocks

Core table containing basic stock information.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| ticker | String(20) | Stock code (e.g., '005930' for Samsung) - Unique |
| name_kr | String(100) | Korean name |
| name_en | String(100) | English name |
| market | String(20) | Market type (KOSPI, KOSDAQ, KONEX) |
| sector | String(50) | Business sector |
| industry | String(100) | Industry classification |
| market_cap | BigInteger | Market capitalization in KRW |
| listed_shares | BigInteger | Total number of listed shares |
| listed_date | DateTime | IPO date |
| is_active | Boolean | Whether stock is actively traded |
| created_at | DateTime | Record creation timestamp |
| updated_at | DateTime | Record update timestamp |

**Indexes:**
- `ix_stocks_ticker` (unique)
- `ix_stocks_market`
- `ix_stocks_sector`
- `ix_stocks_is_active`

### 2. stock_prices

Historical and real-time daily stock price data.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| stock_id | Integer | Foreign key to stocks.id |
| date | DateTime | Trading date |
| open | Numeric(15,2) | Opening price |
| high | Numeric(15,2) | Highest price |
| low | Numeric(15,2) | Lowest price |
| close | Numeric(15,2) | Closing price |
| volume | BigInteger | Trading volume |
| adjusted_close | Numeric(15,2) | Adjusted closing price for splits/dividends |
| trading_value | BigInteger | Total trading value in KRW |
| change_pct | Float | Daily change percentage |
| created_at | DateTime | Record creation timestamp |

**Indexes:**
- `ix_stock_prices_stock_id`
- `ix_stock_prices_date`
- `ix_stock_prices_stock_date` (composite: stock_id, date)
- `ix_stock_prices_date_volume` (composite: date, volume)

**Foreign Keys:**
- `stock_id` → `stocks.id` (CASCADE on delete)

### 3. technical_indicators

Technical analysis indicators calculated from price data.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| stock_id | Integer | Foreign key to stocks.id |
| date | DateTime | Indicator calculation date |
| **Momentum Indicators** | | |
| rsi_14 | Float | 14-day Relative Strength Index |
| rsi_9 | Float | 9-day Relative Strength Index |
| stochastic_k | Float | Stochastic %K |
| stochastic_d | Float | Stochastic %D |
| **Trend Indicators** | | |
| macd | Float | MACD line |
| macd_signal | Float | MACD signal line |
| macd_histogram | Float | MACD histogram |
| adx | Float | Average Directional Index |
| **Moving Averages** | | |
| sma_5 | Float | 5-day Simple Moving Average |
| sma_20 | Float | 20-day Simple Moving Average |
| sma_50 | Float | 50-day Simple Moving Average |
| sma_120 | Float | 120-day Simple Moving Average |
| sma_200 | Float | 200-day Simple Moving Average |
| ema_12 | Float | 12-day Exponential Moving Average |
| ema_26 | Float | 26-day Exponential Moving Average |
| **Volatility Indicators** | | |
| bollinger_upper | Float | Bollinger Upper Band |
| bollinger_middle | Float | Bollinger Middle Band |
| bollinger_lower | Float | Bollinger Lower Band |
| atr | Float | Average True Range |
| **Volume Indicators** | | |
| obv | BigInteger | On Balance Volume |
| volume_ma_20 | BigInteger | 20-day Volume Moving Average |
| created_at | DateTime | Record creation timestamp |

**Indexes:**
- `ix_tech_indicators_stock_date` (composite: stock_id, date)

**Foreign Keys:**
- `stock_id` → `stocks.id` (CASCADE on delete)

### 4. fundamental_indicators

Fundamental financial metrics and ratios.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| stock_id | Integer | Foreign key to stocks.id |
| date | DateTime | Reporting date or calculation date |
| **Valuation Ratios** | | |
| per | Float | Price to Earnings Ratio |
| pbr | Float | Price to Book Ratio |
| pcr | Float | Price to Cashflow Ratio |
| psr | Float | Price to Sales Ratio |
| **Profitability Ratios** | | |
| roe | Float | Return on Equity (%) |
| roa | Float | Return on Assets (%) |
| roic | Float | Return on Invested Capital (%) |
| operating_margin | Float | Operating Profit Margin (%) |
| net_margin | Float | Net Profit Margin (%) |
| **Financial Health** | | |
| debt_ratio | Float | Total Debt to Total Assets (%) |
| debt_to_equity | Float | Debt to Equity Ratio |
| current_ratio | Float | Current Assets to Current Liabilities |
| quick_ratio | Float | Quick Ratio (Acid Test) |
| interest_coverage | Float | Interest Coverage Ratio |
| **Growth Metrics** | | |
| revenue_growth | Float | YoY Revenue Growth (%) |
| earnings_growth | Float | YoY Earnings Growth (%) |
| equity_growth | Float | YoY Equity Growth (%) |
| **Dividend Metrics** | | |
| dividend_yield | Float | Dividend Yield (%) |
| dividend_payout_ratio | Float | Dividend Payout Ratio (%) |
| **Per Share Metrics** | | |
| eps | Float | Earnings Per Share |
| bps | Float | Book value Per Share |
| cps | Float | Cashflow Per Share |
| sps | Float | Sales Per Share |
| dps | Float | Dividend Per Share |
| **Absolute Values** | | (in KRW millions) |
| revenue | BigInteger | Total Revenue |
| operating_profit | BigInteger | Operating Profit |
| net_income | BigInteger | Net Income |
| total_assets | BigInteger | Total Assets |
| total_equity | BigInteger | Total Equity |
| total_debt | BigInteger | Total Debt |
| created_at | DateTime | Record creation timestamp |
| updated_at | DateTime | Record update timestamp |

**Indexes:**
- `ix_fund_indicators_stock_date` (composite: stock_id, date)
- `ix_fund_indicators_per_pbr` (composite: per, pbr)
- `ix_fund_indicators_roe`

**Foreign Keys:**
- `stock_id` → `stocks.id` (CASCADE on delete)

### 5. trades

Trade execution history and order management.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| order_id | String(50) | Unique order identifier |
| ticker | String(20) | Stock code |
| action | String(10) | BUY or SELL |
| order_type | String(20) | MARKET, LIMIT, STOP_LOSS |
| quantity | Integer | Number of shares |
| price | Numeric(15,2) | Order price (limit/stop price) |
| executed_price | Numeric(15,2) | Actual execution price |
| executed_quantity | Integer | Actual executed quantity |
| total_amount | BigInteger | Total transaction amount in KRW |
| commission | Integer | Commission fees in KRW |
| tax | Integer | Tax amount in KRW |
| status | String(20) | PENDING, EXECUTED, PARTIALLY_FILLED, CANCELLED, FAILED |
| reason | Text | Reason for trade or failure reason |
| strategy | String(50) | Trading strategy that generated this order |
| created_at | DateTime | Order creation timestamp |
| executed_at | DateTime | Execution timestamp |
| cancelled_at | DateTime | Cancellation timestamp |
| updated_at | DateTime | Record update timestamp |

**Indexes:**
- `ix_trades_order_id` (unique)
- `ix_trades_ticker`
- `ix_trades_action`
- `ix_trades_status`
- `ix_trades_created_at`
- `ix_trades_executed_at`
- `ix_trades_ticker_date` (composite: ticker, created_at)
- `ix_trades_status_date` (composite: status, created_at)

### 6. portfolios

Current portfolio holdings and positions.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | String(50) | User identifier |
| ticker | String(20) | Stock code |
| quantity | Integer | Number of shares held |
| avg_price | Numeric(15,2) | Average purchase price per share |
| current_price | Numeric(15,2) | Current market price per share |
| current_value | BigInteger | Current total value (quantity × current_price) |
| invested_amount | BigInteger | Total invested amount (quantity × avg_price) |
| unrealized_pnl | BigInteger | Unrealized profit/loss in KRW |
| unrealized_pnl_pct | Float | Unrealized profit/loss percentage |
| realized_pnl | BigInteger | Realized profit/loss in KRW |
| total_commission | Integer | Total commission paid |
| total_tax | Integer | Total tax paid |
| first_purchase_date | DateTime | Date of first purchase |
| last_transaction_date | DateTime | Date of last transaction |
| created_at | DateTime | Record creation timestamp |
| updated_at | DateTime | Record update timestamp |

**Indexes:**
- `ix_portfolios_user_id`
- `ix_portfolios_ticker`
- `ix_portfolios_user_ticker` (composite unique: user_id, ticker)

### 7. watchlist

Stocks being watched by users.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| stock_id | Integer | Foreign key to stocks.id |
| user_id | String(50) | User identifier |
| ticker | String(20) | Stock code (denormalized for quick access) |
| reason | Text | Reason for adding to watchlist |
| score | Float | Custom score or rating (0-100) |
| target_price | Numeric(15,2) | Target buy/sell price |
| notes | Text | Additional notes |
| tags | String(200) | Comma-separated tags |
| alert_enabled | Boolean | Whether price alerts are enabled |
| alert_price_upper | Numeric(15,2) | Alert if price goes above this |
| alert_price_lower | Numeric(15,2) | Alert if price goes below this |
| is_active | Boolean | Whether watchlist entry is active |
| added_date | DateTime | Date added to watchlist |
| last_viewed | DateTime | Last time user viewed this stock |
| created_at | DateTime | Record creation timestamp |
| updated_at | DateTime | Record update timestamp |

**Indexes:**
- `ix_watchlist_user_id`
- `ix_watchlist_ticker`
- `ix_watchlist_is_active`
- `ix_watchlist_added_date`
- `ix_watchlist_user_ticker` (composite: user_id, ticker)
- `ix_watchlist_user_score` (composite: user_id, score)
- `ix_watchlist_user_added` (composite: user_id, added_date)

**Foreign Keys:**
- `stock_id` → `stocks.id` (CASCADE on delete)

## Schema Diagram

```
┌─────────────┐
│   stocks    │
│─────────────│
│ id (PK)     │
│ ticker (UK) │
│ name_kr     │
│ market      │
│ sector      │
│ ...         │
└─────────────┘
      │
      │ 1:N relationships
      ├──────────────────┬──────────────────┬─────────────────┐
      │                  │                  │                 │
┌─────▼────────┐  ┌─────▼────────┐  ┌─────▼────────┐  ┌────▼─────┐
│stock_prices  │  │technical_    │  │fundamental_  │  │watchlist │
│              │  │indicators    │  │indicators    │  │          │
│ stock_id(FK) │  │ stock_id(FK) │  │ stock_id(FK) │  │stock_id  │
│ date         │  │ date         │  │ date         │  │user_id   │
│ open/high/   │  │ rsi_14       │  │ per/pbr/roe  │  │reason    │
│ low/close    │  │ macd         │  │ debt_ratio   │  │score     │
│ volume       │  │ sma_*        │  │ eps/bps      │  │...       │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────┘

┌──────────────┐         ┌──────────────┐
│   trades     │         │  portfolios  │
│──────────────│         │──────────────│
│ id (PK)      │         │ id (PK)      │
│ order_id(UK) │         │ user_id      │
│ ticker       │         │ ticker       │
│ action       │         │ quantity     │
│ price        │         │ avg_price    │
│ status       │         │ current_val  │
│ ...          │         │ pnl          │
└──────────────┘         └──────────────┘
```

## Setup Instructions

### Prerequisites

- PostgreSQL 15+
- Python 3.11+
- Install dependencies: `pip install -r requirements.txt`

### Environment Configuration

Create a `.env` file in the project root:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/stock_trading

# Other settings
DEBUG=false
```

### Initialize Database

#### Option 1: Using the initialization script

```bash
# Create all tables
python shared/database/init_db.py create

# Verify schema
python shared/database/init_db.py verify

# Show all tables
python shared/database/init_db.py show

# Recreate all tables (WARNING: deletes all data)
python shared/database/init_db.py recreate --force
```

#### Option 2: Using Alembic migrations

```bash
# Run migrations to create tables
alembic upgrade head

# Check current migration version
alembic current

# Show migration history
alembic history
```

## Migration Management

### Creating New Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration template
alembic revision -m "Description of changes"
```

### Applying Migrations

```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade by 1 version
alembic upgrade +1

# Upgrade to specific version
alembic upgrade <revision_id>
```

### Rolling Back Migrations

```bash
# Downgrade by 1 version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>

# Downgrade to base (empty database)
alembic downgrade base
```

### Migration Information

```bash
# Show current version
alembic current

# Show migration history
alembic history

# Show SQL that would be executed
alembic upgrade head --sql
```

## Usage Examples

### Python Code Examples

#### 1. Query Stock Information

```python
from shared.database.connection import get_db
from shared.database.models import Stock

db = next(get_db())

# Find stock by ticker
samsung = db.query(Stock).filter(Stock.ticker == "005930").first()
print(f"{samsung.name_kr} - {samsung.market}")

# Get all KOSPI stocks
kospi_stocks = db.query(Stock).filter(Stock.market == "KOSPI").all()
```

#### 2. Get Stock Prices

```python
from datetime import datetime, timedelta
from shared.database.models import Stock, StockPrice

# Get last 30 days of prices
thirty_days_ago = datetime.now() - timedelta(days=30)
prices = db.query(StockPrice).join(Stock).filter(
    Stock.ticker == "005930",
    StockPrice.date >= thirty_days_ago
).order_by(StockPrice.date.desc()).all()

for price in prices:
    print(f"{price.date}: {price.close} KRW (Volume: {price.volume})")
```

#### 3. Get Technical Indicators

```python
from shared.database.models import TechnicalIndicator

indicators = db.query(TechnicalIndicator).join(Stock).filter(
    Stock.ticker == "005930"
).order_by(TechnicalIndicator.date.desc()).first()

print(f"RSI(14): {indicators.rsi_14}")
print(f"MACD: {indicators.macd}")
print(f"SMA(20): {indicators.sma_20}")
```

#### 4. Screen Stocks by Fundamental Indicators

```python
from shared.database.models import FundamentalIndicator

# Find value stocks (low PER, high ROE)
value_stocks = db.query(Stock, FundamentalIndicator).join(
    FundamentalIndicator
).filter(
    FundamentalIndicator.per < 10,
    FundamentalIndicator.per > 0,
    FundamentalIndicator.roe > 15,
    FundamentalIndicator.debt_ratio < 50
).all()

for stock, indicators in value_stocks:
    print(f"{stock.name_kr}: PER={indicators.per:.2f}, ROE={indicators.roe:.2f}%")
```

#### 5. Manage Watchlist

```python
from shared.database.models import Watchlist

# Add to watchlist
watchlist_entry = Watchlist(
    stock_id=samsung.id,
    user_id="user123",
    ticker="005930",
    reason="Strong fundamentals, low PER",
    score=85.5,
    target_price=75000,
    alert_enabled=True,
    alert_price_lower=70000
)
db.add(watchlist_entry)
db.commit()

# Get user's watchlist
my_watchlist = db.query(Watchlist).filter(
    Watchlist.user_id == "user123",
    Watchlist.is_active == True
).order_by(Watchlist.score.desc()).all()
```

#### 6. Track Portfolio

```python
from shared.database.models import Portfolio

# Get portfolio summary
portfolio = db.query(Portfolio).filter(
    Portfolio.user_id == "user123"
).all()

total_value = sum(p.current_value for p in portfolio if p.current_value)
total_pnl = sum(p.unrealized_pnl for p in portfolio if p.unrealized_pnl)

print(f"Total Portfolio Value: {total_value:,} KRW")
print(f"Total P&L: {total_pnl:,} KRW")
```

#### 7. Analyze Trade History

```python
from shared.database.models import Trade

# Get all executed trades for a stock
trades = db.query(Trade).filter(
    Trade.ticker == "005930",
    Trade.status == "EXECUTED"
).order_by(Trade.executed_at.desc()).all()

total_bought = sum(t.executed_quantity for t in trades if t.action == "BUY")
total_sold = sum(t.executed_quantity for t in trades if t.action == "SELL")
```

## Performance Tips

1. **Use Indexes**: The schema includes optimized indexes for common queries
2. **Batch Operations**: Use bulk inserts for large datasets
3. **Connection Pooling**: Configured in `connection.py` with pool size of 10
4. **Query Optimization**: Use `.join()` for related data instead of N+1 queries
5. **Partitioning**: Consider table partitioning for `stock_prices` if dataset grows very large

## Backup and Maintenance

### Regular Backups

```bash
# Backup database
pg_dump -U username stock_trading > backup_$(date +%Y%m%d).sql

# Restore database
psql -U username stock_trading < backup_20251027.sql
```

### Database Maintenance

```sql
-- Analyze tables for query optimization
ANALYZE stocks;
ANALYZE stock_prices;

-- Vacuum to reclaim storage
VACUUM ANALYZE;

-- Reindex for better performance
REINDEX DATABASE stock_trading;
```

## Security Considerations

1. **Never commit** `.env` files with database credentials
2. Use **strong passwords** for database users
3. Enable **SSL connections** in production
4. Implement **row-level security** if needed for multi-tenant scenarios
5. Regular **security updates** for PostgreSQL
6. Use **prepared statements** (SQLAlchemy does this automatically)

## Troubleshooting

### Common Issues

1. **Migration conflicts**: Run `alembic history` to check migration state
2. **Connection errors**: Verify `DATABASE_URL` in `.env` file
3. **Permission errors**: Ensure database user has necessary privileges
4. **Slow queries**: Check indexes with `EXPLAIN ANALYZE` in PostgreSQL

## License

This database schema is part of the Korean Stock Trading System project.
