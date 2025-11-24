# CLAUDE.md - AI Assistant Guide for Korean Stock Trading System

> **Last Updated**: 2025-11-24
> **For**: AI Assistants (Claude, etc.) working on this codebase
> **Purpose**: Comprehensive guide to codebase structure, conventions, and development workflows

---

## Table of Contents

1. [Repository Overview](#repository-overview)
2. [Codebase Structure](#codebase-structure)
3. [Key Architectural Patterns](#key-architectural-patterns)
4. [Development Workflows](#development-workflows)
5. [Configuration Management](#configuration-management)
6. [Database Schema & Models](#database-schema--models)
7. [Service Communication](#service-communication)
8. [Testing Conventions](#testing-conventions)
9. [Code Conventions & Standards](#code-conventions--standards)
10. [Common Development Tasks](#common-development-tasks)
11. [Deployment Guidelines](#deployment-guidelines)
12. [Important Gotchas](#important-gotchas)

---

## Repository Overview

### Purpose
Korean Stock Trading System - A production-grade, microservices-based algorithmic trading platform for Korean stock markets (KOSPI, KOSDAQ, KRX).

### Key Features
- **Data Collection**: Real-time and historical stock data ingestion
- **Technical Analysis**: 20+ technical indicators (RSI, MACD, Bollinger Bands, ATR, etc.)
- **Fundamental Analysis**: 15+ financial ratios (PER, PBR, ROE, debt ratios, etc.)
- **Stock Screening**: 25+ filter criteria for stock selection
- **Scoring System**: Value, growth, quality, momentum scores with percentile ranking
- **Trading Engine**: Signal generation, validation, and execution (live + paper trading)
- **Risk Management**: 5 position sizing methods, circuit breakers, stop-loss/take-profit
- **Backtesting**: Historical strategy analysis with performance metrics
- **Monitoring**: Real-time price monitoring, alerts, health checks, Prometheus metrics

### Technology Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI (async web framework)
- **Database**: PostgreSQL 15 (with SQLAlchemy ORM)
- **Cache**: Redis 7
- **Containerization**: Docker + Docker Compose
- **Scheduler**: APScheduler (timezone-aware for Asia/Seoul)
- **Monitoring**: Prometheus + Grafana
- **Testing**: pytest with fixtures and mocks
- **CI/CD**: GitHub Actions (unit tests, integration tests, code quality checks)

---

## Codebase Structure

### High-Level Directory Layout

```
ko-stock-filter/
├── services/              # 12 microservices (core business logic)
├── shared/                # Shared code (database, config, monitoring, utilities)
├── tests/                 # Test suite (unit + integration tests)
├── config/                # YAML configuration files for each service
├── deployment/            # Production deployment scripts and configs
├── docker/                # Docker Compose orchestration
├── scripts/               # Utility scripts (data seeding, etc.)
├── .github/workflows/     # CI/CD pipelines
├── Makefile               # Development commands
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project metadata and tool configs
└── .env.example           # Environment variable template
```

### Services Directory (`services/`)

Each service follows a consistent structure:

```
services/SERVICE_NAME/
├── main.py                 # FastAPI app + CLI entry point
├── api.py                  # HTTP REST endpoints (if applicable)
├── [service]_engine.py     # Core business logic / processing
├── [service]_service.py    # Service layer (CRUD operations)
├── [service]_repository.py # Data access layer (optional)
└── tests/                  # Service-specific unit tests (optional)
```

**12 Services**:

| Service | Port | Purpose | Key Files |
|---------|------|---------|-----------|
| `data_collector` | 8001 | KRX data ingestion | `stock_code_collector.py`, `price_collector.py`, `fundamental_collector.py` |
| `indicator_calculator` | 8002 | Technical & financial indicators | `technical_calculator.py`, `financial_calculator.py` |
| `stability_calculator` | - | Risk metrics (volatility, beta) | `stability_calculator.py` |
| `stock_scorer` | - | Investment score calculation | `stock_scorer.py`, `score_service.py` |
| `stock_screener` | 8003 | Stock filtering engine | `screening_engine.py` |
| `watchlist_manager` | - | Portfolio tracking | `watchlist_manager.py` |
| `price_monitor` | - | Real-time price monitoring | `price_monitor.py`, `market_calendar.py` |
| `trading_engine` | 8004 | Signal generation & execution | `signal_generator.py`, `order_executor.py`, `paper_trading_executor.py` |
| `risk_manager` | 8005 | Risk controls & position sizing | `position_sizing.py`, `position_monitor.py` |
| `orchestrator` | - | Master scheduler | `scheduler.py` (19K lines) |
| `backtesting` | - | Strategy analysis | `backtesting_engine.py`, `parameter_optimizer.py` |
| `web_viewer` | 8080 | Dashboard & visualization | `main.py` |

### Shared Directory (`shared/`)

Reusable code across all services:

```
shared/
├── database/               # SQLAlchemy models, connections, migrations
│   ├── models.py           # 13 core database tables (606 lines)
│   ├── connection.py       # Database engine and session factory
│   ├── init_db.py          # Database initialization
│   └── alembic/            # Database migrations
│
├── configs/                # Configuration management
│   ├── models.py           # Pydantic validation models (278 lines)
│   ├── loader.py           # YAML + env var merging
│   ├── config.py           # Global settings singleton
│   └── .env.example        # Environment template
│
├── monitoring/             # Observability (662 lines)
│   ├── metrics.py          # Prometheus metrics
│   ├── health_check.py     # Service health endpoints
│   ├── alerts.py           # Alert management
│   ├── reports.py          # Performance reporting
│   └── structured_logger.py # JSON logging
│
└── utilities/              # Common helpers
    ├── date_utils.py       # Korean trading calendar
    ├── logger.py           # Logging configuration
    └── validators.py       # Data validation
```

### Config Directory (`config/`)

YAML configuration files for each service (tier 2 of configuration):

- `trading_engine.yaml` - Signal generation, order parameters, commissions
- `risk_manager.yaml` - Risk limits, position sizing methods
- `stock_screener.yaml` - Screening thresholds (volatility, valuation, liquidity)
- `indicator_calculator.yaml` - Indicator periods (RSI, MACD, BB, ATR)
- `data_collector.yaml` - Collection schedules, batch sizes
- `price_monitor.yaml` - Monitoring intervals, alert thresholds
- `database.yaml` - Connection pool settings
- `redis.yaml` - Cache configuration
- `logging.yaml` - Log levels and formats

---

## Key Architectural Patterns

### 1. Microservices with Orchestrator

**Pattern**: Services are independent but coordinated by a central orchestrator.

- **Orchestrator** (`services/orchestrator/scheduler.py`):
  - Uses APScheduler with Asia/Seoul timezone
  - Schedules 6 main jobs:
    1. Data collection (16:00 after market close)
    2. Indicator calculation (17:00 after data ready)
    3. Watchlist update (18:00 after scoring)
    4. Signal generation (08:45 before market open)
    5. Position monitoring (09:00-15:30 every 15 min)
    6. Risk checks (every 30 minutes)

- **Service Communication**: HTTP REST APIs (synchronous)
  - Services expose FastAPI endpoints
  - Services call each other via HTTP client (httpx/aiohttp)
  - Redis used for caching, not inter-service messaging

### 2. Repository Pattern

**Pattern**: Separate data access logic from business logic.

```python
# Repository Layer (optional - not all services use this)
class StockRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_stock_by_ticker(self, ticker: str) -> Optional[Stock]:
        return self.db.query(Stock).filter(Stock.ticker == ticker).first()

# Service Layer
class StockService:
    def __init__(self, repository: StockRepository):
        self.repository = repository

    def process_stock_data(self, ticker: str):
        stock = self.repository.get_stock_by_ticker(ticker)
        # Business logic here

# API Layer
@app.get("/stocks/{ticker}")
def get_stock(ticker: str, db: Session = Depends(get_db)):
    service = StockService(StockRepository(db))
    return service.process_stock_data(ticker)
```

### 3. Dependency Injection

**Pattern**: FastAPI `Depends()` for database sessions and configuration.

```python
from shared.database.connection import get_db
from shared.configs.config import get_settings

@app.get("/stocks")
def list_stocks(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    # Database session auto-cleanup via Depends
    # Settings cached globally
```

### 4. Three-Tier Configuration System

**Priority Order** (highest to lowest):

1. **Environment Variables** (highest priority)
   - Format: `SERVICE_SECTION_KEY` (uppercase, underscored)
   - Example: `TRADING_ENGINE_SIGNAL_GENERATOR_RISK_TOLERANCE=2.5`

2. **YAML Configuration Files** (service-specific)
   - Location: `config/SERVICE_NAME.yaml`
   - Loaded by `shared/configs/loader.py`

3. **Pydantic Defaults** (hardcoded fallbacks)
   - Defined in `shared/configs/models.py`

### 5. Trading Pipeline Pattern

**Sequence**: Data → Indicators → Scoring → Screening → Signals → Validation → Execution

```
Data Collector (8001)
    ↓ (stores OHLCV data)
Indicator Calculator (8002)
    ↓ (calculates RSI, MACD, etc.)
Stability Calculator
    ↓ (risk metrics)
Stock Scorer
    ↓ (composite scores)
Stock Screener (8003)
    ↓ (filters stocks)
Trading Engine (8004)
    ↓ (generates signals)
Risk Manager (8005)
    ↓ (validates, sizes positions)
Order Execution
    ↓ (paper or live trading)
Trade Logging
```

---

## Development Workflows

### Initial Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd ko-stock-filter

# 2. Install dependencies
make install
# OR manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# 4. Set up database
make db-migrate
# OR manually:
alembic upgrade head

# 5. Seed data (optional)
python scripts/seed_stock_data.py --days 365
```

### Common Makefile Commands

```bash
# Development
make install          # Install dependencies and set up environment
make clean            # Clean up generated files and caches
make test             # Run tests with coverage
make lint             # Run flake8 and mypy
make format           # Format code with black and isort
make run-dev          # Start all services with Docker Compose

# Docker
make docker-build     # Build all Docker images
make docker-up        # Start all services with Docker Compose
make docker-down      # Stop all Docker services
make docker-logs      # View Docker logs
make docker-clean     # Clean Docker resources

# Database
make db-migrate       # Run database migrations
make db-upgrade       # Upgrade database schema
make db-downgrade     # Downgrade database schema
make backup           # Backup database
make restore          # Restore database from backup

# Monitoring
make health           # Run health checks
make logs             # View application logs
make status           # Check service status
```

### Running Services

**Option 1: Docker Compose (Recommended)**

```bash
# Start all services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

**Option 2: Individual Services (Development)**

```bash
# Terminal 1: Data Collector
cd services/data_collector
uvicorn main:app --host 0.0.0.0 --port 8001

# Terminal 2: Indicator Calculator
cd services/indicator_calculator
uvicorn main:app --host 0.0.0.0 --port 8002

# Terminal 3: Trading Engine
cd services/trading_engine
uvicorn main:app --host 0.0.0.0 --port 8004

# ... etc
```

### Git Workflow

**Branch Naming**:
- Feature branches: `claude/feature-name-SESSION_ID`
- Bug fixes: `claude/fix-bug-name-SESSION_ID`
- Main branch: `main`

**Commit Messages**:
```bash
# Good commit messages
git commit -m "feat: Add Kelly criterion position sizing"
git commit -m "fix: Correct RSI calculation for edge cases"
git commit -m "refactor: Extract signal validation logic"
git commit -m "test: Add comprehensive tests for stock scorer"
git commit -m "docs: Update CLAUDE.md with testing conventions"

# Commit prefixes
# feat: New feature
# fix: Bug fix
# refactor: Code restructuring
# test: Add/modify tests
# docs: Documentation changes
# chore: Maintenance tasks
```

---

## Configuration Management

### Configuration Layers

**1. Environment Variables (.env file)**

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/stock_trading

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API Keys
KOREAINVESTMENT_API_KEY=xxxxx
KOREAINVESTMENT_API_SECRET=xxxxx

# Service-specific overrides
TRADING_ENGINE_SIGNAL_GENERATOR_RISK_TOLERANCE=2.5
RISK_MANAGER_RISK_PARAMETERS_MAX_POSITION_SIZE_PCT=8.0
```

**2. YAML Configuration Files**

```yaml
# config/trading_engine.yaml
signal_generator:
  risk_tolerance: 2.0              # % of portfolio
  max_position_size_pct: 10.0      # % per position
  min_conviction_score: 60.0       # 0-100 scale
  use_limit_orders: true
  conviction_weights:
    weight_value: 0.30
    weight_momentum: 0.30
    weight_volume: 0.20
    weight_quality: 0.20
```

**3. Pydantic Models**

```python
# shared/configs/models.py
class TradingEngineConfig(BaseModel):
    signal_generator: SignalGeneratorConfig
    signal_validator: SignalValidatorConfig
    order_executor: OrderExecutorConfig

class SignalGeneratorConfig(BaseModel):
    risk_tolerance: float = 2.0
    max_position_size_pct: float = 10.0
    min_conviction_score: float = 60.0
```

### Loading Configuration

```python
from shared.configs.config import get_settings

# In service code
settings = get_settings()
risk_tolerance = settings.trading_engine.signal_generator.risk_tolerance

# Settings are cached globally (singleton pattern)
```

---

## Database Schema & Models

### Core Tables (13 total)

**Location**: `shared/database/models.py`

#### 1. Stock (Master Data)
```python
Stock:
  - id: Integer (PK)
  - ticker: String(10) unique, indexed
  - name_kr: String(100)
  - name_en: String(100)
  - market: Enum(KOSPI, KOSDAQ, KONEX)
  - sector: String(50)
  - industry: String(100)
  - market_cap: BigInteger
  - listed_shares: BigInteger
  - is_active: Boolean
  - created_at: DateTime
  - updated_at: DateTime
```

#### 2. StockPrice (OHLCV Data)
```python
StockPrice:
  - id: Integer (PK)
  - stock_id: Integer (FK → Stock)
  - date: Date
  - open: Decimal(15,2)
  - high: Decimal(15,2)
  - low: Decimal(15,2)
  - close: Decimal(15,2)
  - volume: BigInteger
  - adjusted_close: Decimal(15,2)
  - trading_value: BigInteger
  - change_pct: Decimal(10,4)
  - created_at: DateTime

  # Composite index: (stock_id, date)
```

#### 3. TechnicalIndicator (38 fields)
```python
TechnicalIndicator:
  - stock_id: Integer (FK → Stock, PK)
  - date: Date (PK)

  # Momentum Indicators
  - rsi_14, rsi_9: Decimal(10,4)
  - stochastic_k, stochastic_d: Decimal(10,4)
  - adx: Decimal(10,4)

  # Trend Indicators
  - macd, macd_signal, macd_histogram: Decimal(15,6)

  # Moving Averages
  - sma_5, sma_20, sma_50, sma_120, sma_200: Decimal(15,2)
  - ema_12, ema_26: Decimal(15,2)

  # Volatility Indicators
  - bollinger_upper, bollinger_middle, bollinger_lower: Decimal(15,2)
  - atr: Decimal(15,2)

  # Volume Indicators
  - obv: BigInteger
  - volume_ma_20: BigInteger

  # Composite index: (stock_id, date)
```

#### 4. FundamentalIndicator (40 fields)
```python
FundamentalIndicator:
  - stock_id: Integer (FK → Stock, PK)
  - date: Date (PK)

  # Valuation Ratios
  - per, pbr, pcr, psr: Decimal(10,4)

  # Profitability Ratios
  - roe, roa, roic: Decimal(10,4)
  - gross_margin, operating_margin, net_margin: Decimal(10,4)

  # Financial Health
  - debt_ratio, current_ratio, quick_ratio: Decimal(10,4)
  - interest_coverage: Decimal(10,4)

  # Growth Metrics
  - revenue_growth, earnings_growth: Decimal(10,4)

  # Dividend Metrics
  - dividend_yield, dividend_payout_ratio: Decimal(10,4)

  # Per-share Metrics
  - eps, bps, sps, cps: Decimal(15,2)
```

#### 5. CompositeScore (Investment Scoring)
```python
CompositeScore:
  - stock_id: Integer (FK → Stock, PK)
  - date: Date (PK)
  - value_score: Decimal(5,2)      # 0-100
  - growth_score: Decimal(5,2)     # 0-100
  - quality_score: Decimal(5,2)    # 0-100
  - momentum_score: Decimal(5,2)   # 0-100
  - composite_score: Decimal(5,2)  # 0-100 (weighted average)
  - percentile_rank: Integer       # 0-100 (vs all stocks)
  - component_weights: JSON        # Weights used
  # ... 27 sub-metrics (per, pbr, roe, rsi, etc.)
```

#### 6. Trade (Execution Records)
```python
Trade:
  - order_id: String(50) (PK)
  - ticker: String(10)
  - action: Enum(BUY, SELL)
  - order_type: Enum(MARKET, LIMIT, STOP_LOSS)
  - quantity: Integer
  - price: Decimal(15,2)           # Requested price
  - executed_price: Decimal(15,2)  # Actual execution price
  - executed_quantity: Integer
  - total_amount: Decimal(15,2)
  - commission: Decimal(10,2)
  - tax: Decimal(10,2)
  - status: Enum(PENDING, EXECUTED, CANCELLED, FAILED)
  - reason: Text
  - strategy: String(50)
  - created_at: DateTime
  - executed_at: DateTime
```

#### 7. Portfolio (Holdings)
```python
Portfolio:
  - id: Integer (PK)
  - user_id: String(50)
  - ticker: String(10)
  - quantity: Integer
  - avg_price: Decimal(15,2)
  - current_price: Decimal(15,2)
  - current_value: Decimal(15,2)
  - unrealized_pnl: Decimal(15,2)
  - realized_pnl: Decimal(15,2)
  - stop_loss_price: Decimal(15,2)
  - stop_loss_pct: Decimal(5,2)
  - take_profit_price: Decimal(15,2)
  - take_profit_pct: Decimal(5,2)
  - trailing_stop_price: Decimal(15,2)
  - highest_price_since_purchase: Decimal(15,2)
  - updated_at: DateTime
```

### Database Connection

```python
from shared.database.connection import get_db, get_engine
from sqlalchemy.orm import Session

# In FastAPI routes
@app.get("/stocks")
def list_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).filter(Stock.is_active == True).all()
    return stocks

# Standalone scripts
from shared.database.connection import get_engine
from sqlalchemy.orm import sessionmaker

engine = get_engine()
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()
try:
    stocks = db.query(Stock).all()
finally:
    db.close()
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new column to stocks table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# View migration history
alembic history
```

---

## Service Communication

### HTTP REST APIs

Services communicate via synchronous HTTP calls:

```python
import httpx

# In Trading Engine calling Risk Manager
async def validate_order(order_data: dict):
    risk_manager_url = os.getenv('RISK_MANAGER_URL', 'http://localhost:8005')
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{risk_manager_url}/validate",
            json=order_data,
            timeout=10.0
        )
        return response.json()
```

### Service Dependencies

**Data Flow**:
```
data-collector (8001)
    ↓
indicator-calculator (8002)
    ↓
stability-calculator
    ↓
stock-scorer
    ↓
stock-screener (8003)
    ↓
trading-engine (8004)
    ↓
risk-manager (8005)
```

**Docker Compose Dependencies**:
```yaml
# In docker-compose.full.yml
indicator-calculator:
  depends_on:
    - postgres
    - redis
    - data-collector

trading-engine:
  depends_on:
    - indicator-calculator
    - stock-screener
    - risk-manager
```

---

## Testing Conventions

### Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures (304 lines)
├── test_*.py                      # Unit tests
└── integration/                   # Integration tests
    ├── test_e2e_workflow.py
    └── test_service_communication.py
```

### Key Fixtures (conftest.py)

```python
@pytest.fixture
def test_db_engine():
    """In-memory SQLite database for tests"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def test_db_session(test_db_engine):
    """Database session with auto-cleanup"""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def sample_stock(test_db_session):
    """Samsung Electronics test data"""
    stock = Stock(
        ticker='005930',
        name_kr='삼성전자',
        name_en='Samsung Electronics',
        market='KOSPI',
        sector='Technology'
    )
    test_db_session.add(stock)
    test_db_session.commit()
    return stock

@pytest.fixture
def sample_stock_prices(test_db_session, sample_stock):
    """30 days of OHLCV data"""
    # ... generates price data

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    return MagicMock()
```

### Test Patterns

**1. Fixture-based Setup**
```python
def test_stock_creation(test_db_session, sample_stock):
    assert test_db_session.query(Stock).count() == 1
    assert sample_stock.ticker == '005930'
```

**2. Parameterized Tests**
```python
@pytest.mark.parametrize("ticker,expected_valid", [
    ('005930', True),   # Valid Samsung Electronics
    ('999999', False),  # Invalid ticker
    ('AAPL', False),    # Not Korean format
])
def test_ticker_validation(ticker, expected_valid):
    assert validate_ticker(ticker) == expected_valid
```

**3. Mock External Dependencies**
```python
def test_price_collector(mock_redis, monkeypatch):
    # Mock external API
    def mock_fetch(*args, **kwargs):
        return {"price": 71000}

    monkeypatch.setattr("services.data_collector.price_collector.fetch_data", mock_fetch)

    collector = PriceCollector(redis_client=mock_redis)
    # Test with mocked data
```

**4. Async Tests**
```python
@pytest.mark.asyncio
async def test_async_data_collection():
    data = await collect_stock_data('005930')
    assert len(data) > 0
```

### Running Tests

```bash
# All tests
make test
# OR
pytest tests/ -v --cov=services --cov=shared --cov-report=html

# Specific test file
pytest tests/test_stock_scorer.py -v

# Ignore integration tests (faster)
pytest tests/ --ignore=tests/integration/ -v

# With coverage threshold check
pytest --cov=services --cov=shared --cov-fail-under=15
```

### CI/CD Testing

**GitHub Actions** (`.github/workflows/unit-tests.yml`):
- Runs on push to `main`, `develop`, `claude/*` branches
- Python 3.11
- Pytest with coverage reports
- Uploads to Codecov
- Code quality checks (black, flake8, mypy, isort)
- **Note**: Tests currently in warning mode (don't block CI)

---

## Code Conventions & Standards

### Code Formatting

**Tools**:
- **Black**: Code formatter (line length: 100)
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

```bash
# Format code
make format
# OR
black services/ shared/ tests/
isort services/ shared/ tests/

# Check formatting
black --check services/ shared/ tests/

# Lint
make lint
# OR
flake8 services/ shared/ --max-line-length=100
mypy services/ shared/ --ignore-missing-imports
```

### Type Hints

**Always use type hints** for function signatures:

```python
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date

def calculate_rsi(
    prices: List[Decimal],
    period: int = 14
) -> Optional[Decimal]:
    """Calculate Relative Strength Index."""
    if len(prices) < period:
        return None
    # ... calculation
    return rsi_value

def get_stock_by_ticker(
    db: Session,
    ticker: str
) -> Optional[Stock]:
    """Retrieve stock by ticker symbol."""
    return db.query(Stock).filter(Stock.ticker == ticker).first()
```

### Logging Standards

**Structured JSON Logging**:

```python
import logging
from shared.utilities.logger import setup_logger

logger = setup_logger(__name__)

# Good logging
logger.info("Trade executed", extra={
    "ticker": "005930",
    "quantity": 100,
    "price": 70500,
    "total_amount": 7050000,
    "commission": 1057,
    "status": "EXECUTED"
})

# Log levels
logger.debug("Function entry", extra={"args": args})
logger.info("Business event", extra={"event": "trade_executed"})
logger.warning("Risk limit warning", extra={"limit": "max_position_size"})
logger.error("Operation failed", extra={"error": str(e)}, exc_info=True)
```

### Error Handling

**Custom Exceptions**:

```python
# Define in service modules
class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass

class ValidationError(Exception):
    """Raised when data validation fails."""
    pass

class TradeExecutionError(Exception):
    """Raised when trade execution fails."""
    pass
```

**Error Handling Pattern**:

```python
try:
    order = execute_order(signal)
    logger.info("Order executed", extra={"order_id": order.id})
except TradeExecutionError as e:
    logger.error(f"Trade failed: {e}", extra={"signal": signal.dict()})
    # Don't halt - continue with next signal
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    # Alert on unexpected errors
```

### Pydantic Models

**Always use Pydantic for data validation**:

```python
from pydantic import BaseModel, Field, validator

class TradeRequest(BaseModel):
    ticker: str = Field(..., regex=r'^\d{6}$')  # 6-digit Korean ticker
    quantity: int = Field(..., ge=1, le=10000)  # 1-10K shares
    price: float = Field(..., gt=0)
    order_type: OrderType  # Enum validation

    @validator('ticker')
    def validate_ticker(cls, v):
        if not is_valid_korean_ticker(v):
            raise ValueError('Invalid Korean stock ticker')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "005930",
                "quantity": 100,
                "price": 70500,
                "order_type": "MARKET"
            }
        }
```

### Documentation Standards

**Docstrings** (Google style):

```python
def calculate_position_size(
    portfolio_value: Decimal,
    risk_per_trade: Decimal,
    entry_price: Decimal,
    stop_loss_price: Decimal
) -> int:
    """Calculate position size using fixed percentage risk method.

    Args:
        portfolio_value: Total portfolio value in KRW
        risk_per_trade: Risk percentage per trade (e.g., 2.0 for 2%)
        entry_price: Intended entry price per share
        stop_loss_price: Stop loss price per share

    Returns:
        Number of shares to purchase (integer)

    Raises:
        ValueError: If stop_loss_price >= entry_price

    Example:
        >>> calculate_position_size(
        ...     portfolio_value=Decimal('10000000'),
        ...     risk_per_trade=Decimal('2.0'),
        ...     entry_price=Decimal('70000'),
        ...     stop_loss_price=Decimal('66500')
        ... )
        57
    """
    if stop_loss_price >= entry_price:
        raise ValueError("Stop loss must be below entry price")

    risk_amount = portfolio_value * (risk_per_trade / 100)
    risk_per_share = entry_price - stop_loss_price
    position_size = int(risk_amount / risk_per_share)

    return position_size
```

---

## Common Development Tasks

### Adding a New Service

1. **Create service directory**:
```bash
mkdir services/new_service
touch services/new_service/__init__.py
touch services/new_service/main.py
```

2. **Implement service**:
```python
# services/new_service/main.py
from fastapi import FastAPI, Depends
from shared.database.connection import get_db

app = FastAPI(title="New Service")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

3. **Create Dockerfile**:
```dockerfile
# docker/Dockerfile.new_service
FROM stock-trading-base:latest
COPY services/new_service/ /app/services/new_service/
CMD ["uvicorn", "services.new_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

4. **Add to Docker Compose**:
```yaml
# docker/docker-compose.full.yml
new-service:
  build:
    context: ..
    dockerfile: docker/Dockerfile.new_service
  container_name: new-service
  ports:
    - "8XXX:8000"
  depends_on:
    - postgres
    - redis
  networks:
    - stock-trading-network
```

5. **Add configuration** (if needed):
```yaml
# config/new_service.yaml
parameter1: value1
parameter2: value2
```

6. **Write tests**:
```python
# tests/test_new_service.py
def test_new_service_health():
    # Test implementation
    pass
```

### Adding a New Database Table

1. **Define model**:
```python
# shared/database/models.py
class NewTable(Base):
    __tablename__ = 'new_table'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

2. **Create migration**:
```bash
alembic revision --autogenerate -m "Add new_table"
```

3. **Review and apply migration**:
```bash
# Review generated migration in alembic/versions/
alembic upgrade head
```

4. **Update tests**:
```python
# tests/conftest.py
@pytest.fixture
def sample_new_table_data(test_db_session):
    data = NewTable(name="Test")
    test_db_session.add(data)
    test_db_session.commit()
    return data
```

### Adding a New Technical Indicator

1. **Add column to TechnicalIndicator model**:
```python
# shared/database/models.py
class TechnicalIndicator(Base):
    # ... existing columns
    new_indicator = Column(Decimal(10, 4))
```

2. **Create migration**:
```bash
alembic revision --autogenerate -m "Add new_indicator to technical_indicators"
alembic upgrade head
```

3. **Implement calculation**:
```python
# services/indicator_calculator/technical_calculator.py
def calculate_new_indicator(prices: List[Decimal]) -> Decimal:
    """Calculate new indicator."""
    # Implementation
    return result
```

4. **Update calculator service**:
```python
# services/indicator_calculator/main.py
indicator_data['new_indicator'] = calculate_new_indicator(prices)
```

5. **Add tests**:
```python
# tests/test_technical_calculator.py
def test_new_indicator_calculation():
    prices = [Decimal('100'), Decimal('105'), Decimal('103')]
    result = calculate_new_indicator(prices)
    assert result > 0
```

---

## Deployment Guidelines

### Docker Deployment (Recommended)

**Build images**:
```bash
make docker-build
# Builds: base image → 12 service images
```

**Start services**:
```bash
make docker-up
# Starts: postgres, redis, db-migrate, 12 services
```

**Check status**:
```bash
make docker-ps
```

**View logs**:
```bash
make docker-logs
# OR specific service:
cd docker && docker compose -f docker-compose.full.yml logs -f trading-engine
```

**Stop services**:
```bash
make docker-down
```

### Systemd Deployment (Production)

```bash
# Install systemd services
sudo make deploy-systemd

# Check status
systemctl status stock-trading-orchestrator

# View logs
journalctl -u stock-trading-orchestrator -f

# Restart service
sudo systemctl restart stock-trading-orchestrator
```

### Environment Variables for Production

**Required**:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_HOST`, `REDIS_PORT` - Redis connection
- `KOREAINVESTMENT_API_KEY`, `KOREAINVESTMENT_API_SECRET` - Trading API credentials
- `FORCE_PAPER_TRADING=false` - Disable for live trading (be careful!)

**Optional but Recommended**:
- `LOG_LEVEL=INFO` - Production log level
- `ENABLE_METRICS=true` - Prometheus metrics
- `SLACK_WEBHOOK_URL` - Trading alerts
- `SENTRY_DSN` - Error tracking

### Health Checks

All services expose `/health` endpoint:

```bash
curl http://localhost:8001/health  # Data Collector
curl http://localhost:8002/health  # Indicator Calculator
curl http://localhost:8004/health  # Trading Engine
```

Response:
```json
{
  "status": "healthy",
  "service": "data-collector",
  "version": "0.1.0",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}
```

### Monitoring

**Prometheus Metrics**: `/metrics` endpoint on all services

**Grafana Dashboards**: `docker/grafana/dashboards/`

**Log Aggregation**: JSON logs for ELK/Loki ingestion

---

## Important Gotchas

### 1. Korean Market Hours

**Trading hours** (Asia/Seoul timezone):
- Regular: 09:00 - 15:30 KST
- Pre-market: 08:30 - 09:00 KST
- After-hours: 15:40 - 16:00 KST

**Data collection timing**:
- End-of-day data: Available after 16:00 KST
- Fundamental data: Updated quarterly

**Holidays**: Korean stock market holidays differ from US/EU. Use `shared/utilities/date_utils.py` for calendar checks.

### 2. Database Connection Pooling

**Always use `get_db()` dependency in FastAPI**:
```python
# GOOD
@app.get("/stocks")
def list_stocks(db: Session = Depends(get_db)):
    return db.query(Stock).all()

# BAD (connection leak)
@app.get("/stocks")
def list_stocks():
    engine = create_engine(DATABASE_URL)
    session = Session(engine)
    return session.query(Stock).all()  # Never closed!
```

### 3. Decimal Precision for Financial Data

**Always use `Decimal` for money/prices**:
```python
from decimal import Decimal

# GOOD
price = Decimal('70500.00')
total = price * quantity

# BAD (floating point errors)
price = 70500.00
total = price * quantity  # May have precision issues
```

### 4. Paper Trading vs Live Trading

**Default is PAPER TRADING** (`FORCE_PAPER_TRADING=true` in `.env.example`)

**To enable live trading**:
1. Set `FORCE_PAPER_TRADING=false` in `.env`
2. Configure broker API credentials
3. Update `config/trading_engine.yaml`: `dry_run: false`
4. **Test thoroughly in paper mode first!**

### 5. Korean Ticker Format

**Korean stock tickers are 6-digit strings**: `"005930"` (Samsung)

**Always validate**:
```python
def validate_ticker(ticker: str) -> bool:
    return bool(re.match(r'^\d{6}$', ticker))
```

**Don't use integers**:
```python
# WRONG
ticker = 5930  # Missing leading zeros!

# CORRECT
ticker = "005930"
```

### 6. Async vs Sync

**FastAPI routes can be sync or async**:
```python
# Sync (blocks worker)
@app.get("/stocks")
def list_stocks(db: Session = Depends(get_db)):
    return db.query(Stock).all()

# Async (non-blocking)
@app.get("/stocks")
async def list_stocks(db: Session = Depends(get_db)):
    # Use asyncio-compatible DB driver for true async
    return db.query(Stock).all()
```

**Note**: Current implementation uses synchronous SQLAlchemy. For true async, would need `sqlalchemy[asyncio]` and `asyncpg`.

### 7. Configuration Override Priority

**Remember priority order**:
1. Environment variables (highest)
2. YAML files
3. Pydantic defaults (lowest)

**Example**:
```yaml
# config/trading_engine.yaml
signal_generator:
  risk_tolerance: 2.0
```

```bash
# .env file
TRADING_ENGINE_SIGNAL_GENERATOR_RISK_TOLERANCE=3.5
```

**Result**: `3.5` is used (env var wins)

### 8. Time Zones

**All times stored in UTC in database**:
```python
from datetime import datetime
import pytz

# Store in UTC
created_at = datetime.utcnow()

# Display in KST
kst = pytz.timezone('Asia/Seoul')
display_time = created_at.astimezone(kst)
```

**Scheduler uses Asia/Seoul timezone** (see `services/orchestrator/scheduler.py`)

### 9. Test Database Isolation

**Tests use in-memory SQLite**, not PostgreSQL:
```python
# conftest.py
@pytest.fixture
def test_db_engine():
    engine = create_engine("sqlite:///:memory:")  # In-memory
    Base.metadata.create_all(engine)
    yield engine
```

**SQLite limitations**:
- No `ENUM` type (uses `String`)
- Different date/time handling
- Less strict foreign key checks

**For integration tests**, use Docker Compose test database.

### 10. API Rate Limiting

**External APIs have rate limits**:
- Korea Investment API: ~20 requests/second
- KRX API: Varies by endpoint

**Always implement rate limiting**:
```python
import time
from datetime import datetime

class RateLimiter:
    def __init__(self, calls_per_second: int = 5):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0

    def wait(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()
```

---

## Quick Reference

### Service Ports

| Service | Port |
|---------|------|
| Data Collector | 8001 |
| Indicator Calculator | 8002 |
| Stock Screener | 8003 |
| Trading Engine | 8004 |
| Risk Manager | 8005 |
| Web Viewer | 8080 |
| PostgreSQL | 5432 |
| Redis | 6379 |

### Key Files

| File | Purpose |
|------|---------|
| `Makefile` | Development commands |
| `docker-compose.full.yml` | Production Docker setup |
| `shared/database/models.py` | Database schema |
| `shared/configs/models.py` | Configuration schemas |
| `tests/conftest.py` | Test fixtures |
| `.env.example` | Environment template |
| `pyproject.toml` | Project metadata, tool configs |

### Useful Commands

```bash
# Development
make install && make db-migrate
make docker-up && make docker-logs

# Testing
make test
pytest tests/test_stock_scorer.py -v

# Formatting
make format && make lint

# Database
alembic revision --autogenerate -m "message"
alembic upgrade head

# Docker
docker compose -f docker/docker-compose.full.yml ps
docker compose -f docker/docker-compose.full.yml logs -f trading-engine
```

---

## Questions or Issues?

**For AI Assistants**:
- Review this CLAUDE.md thoroughly before making changes
- Check `README.md` for user-facing documentation
- Review `deployment/DEPLOYMENT_CHECKLIST.md` for production readiness
- Consult `tests/conftest.py` for testing patterns

**For Humans**:
- See `README.md` for general project documentation
- See `deployment/README.md` for deployment guide
- Open issues on GitHub for bugs/features

---

**Last Updated**: 2025-11-24
**Version**: 0.1.0
**Maintainer**: AI Assistant (Claude)
