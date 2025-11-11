# Korean Stock Trading System

A comprehensive microservices-based stock trading system for the Korean stock market (KRX - Korea Exchange). This system provides data collection, technical analysis, stock screening, automated trading, and risk management capabilities.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Services](#services)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)
- [License](#license)

## Overview

This system is designed to facilitate algorithmic trading on Korean stock exchanges (KOSPI, KOSDAQ) with the following key features:

- **Real-time Data Collection**: Collect live market data from Korean exchanges
- **Technical Analysis**: Calculate various technical indicators (RSI, MACD, Moving Averages, etc.)
- **Stock Screening**: Filter stocks based on technical and fundamental criteria
- **Trading Engine**: Execute trades with multiple order types (Market, Limit, Stop Loss)
- **Risk Management**: Manage portfolio risk, position sizing, and exposure

## Architecture

The system follows a microservices architecture pattern with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway (Future)                     │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬─────────────┬─────────────┐
    │            │            │             │             │
┌───▼───┐  ┌────▼────┐  ┌───▼────┐  ┌─────▼──┐  ┌──────▼───┐
│ Data  │  │Indicator│  │ Stock  │  │Trading │  │   Risk   │
│Collect│  │Calculat-│  │Screener│  │ Engine │  │ Manager  │
│  or   │  │   or    │  │        │  │        │  │          │
└───┬───┘  └────┬────┘  └───┬────┘  └────┬───┘  └─────┬────┘
    │           │            │            │            │
    └───────────┴────────────┴────────────┴────────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
            ┌───────▼────────┐   ┌──────▼──────┐
            │   PostgreSQL   │   │    Redis    │
            │   (Database)   │   │   (Cache)   │
            └────────────────┘   └─────────────┘
```

## Services

### 1. Data Collector Service
- Collects real-time and historical stock data from Korean exchanges
- Integrates with KRX APIs and other data providers
- Stores data in PostgreSQL database
- **Port**: 8001

### 2. Indicator Calculator Service
- Calculates technical indicators (RSI, MACD, Moving Averages, Bollinger Bands)
- Processes historical price data
- Provides indicator values via API
- **Port**: 8002

### 3. Stock Screener Service
- Filters stocks based on various criteria
- Supports technical and fundamental screening
- Provides ranked lists of stocks
- **Port**: 8003

### 4. Trading Engine Service
- Executes trades on Korean stock exchanges
- Manages order lifecycle (creation, execution, cancellation)
- Supports multiple order types (Market, Limit, Stop Loss)
- **Port**: 8004

### 5. Risk Manager Service
- Manages trading risk and position sizing
- Validates orders against risk parameters
- Monitors portfolio exposure and drawdown
- **Port**: 8005

## Project Structure

```
ko-stock-filter/
├── services/                    # Microservices
│   ├── data_collector/         # Data collection service
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── indicator_calculator/   # Technical indicator service
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── stock_screener/         # Stock screening service
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── trading_engine/         # Trading execution service
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── requirements.txt
│   └── risk_manager/           # Risk management service
│       ├── __init__.py
│       ├── main.py
│       └── requirements.txt
├── shared/                      # Shared modules
│   ├── database/               # Database models and connections
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── connection.py
│   ├── utilities/              # Shared utilities
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── validators.py
│   │   └── date_utils.py
│   └── configs/                # Configuration management
│       ├── __init__.py
│       ├── config.py
│       └── .env.example
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   └── test_utilities.py
├── docker/                      # Docker configuration
│   ├── docker-compose.yml
│   ├── Dockerfile.base
│   ├── Dockerfile.data_collector
│   ├── Dockerfile.indicator_calculator
│   ├── Dockerfile.stock_screener
│   ├── Dockerfile.trading_engine
│   ├── Dockerfile.risk_manager
│   └── .dockerignore
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for containerized deployment)
- PostgreSQL 15+
- Redis 7+

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ko-stock-filter.git
cd ko-stock-filter
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up configuration:
```bash
cp shared/configs/.env.example .env
# Edit .env with your configuration
```

### Running with Docker Compose

The easiest way to run all services:

```bash
cd docker
docker-compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- All microservices (ports 8001-8005)

### Running Individual Services

To run a service locally:

```bash
# Data Collector
cd services/data_collector
uvicorn main:app --host 0.0.0.0 --port 8001

# Indicator Calculator
cd services/indicator_calculator
uvicorn main:app --host 0.0.0.0 --port 8002

# Stock Screener
cd services/stock_screener
uvicorn main:app --host 0.0.0.0 --port 8003

# Trading Engine
cd services/trading_engine
uvicorn main:app --host 0.0.0.0 --port 8004

# Risk Manager
cd services/risk_manager
uvicorn main:app --host 0.0.0.0 --port 8005
```

### Data Seeding

Before running the services, you need to seed the database with stock data. The system provides a data seeding script that populates the database with representative Korean stocks and their historical data.

#### Quick Start

Seed database with 1 year of data for 35 representative stocks:
```bash
python scripts/seed_stock_data.py
```

#### Data Seeding Options

Seed with custom time period (e.g., 200 days):
```bash
python scripts/seed_stock_data.py --days 200
```

Seed specific stocks only:
```bash
python scripts/seed_stock_data.py --tickers "005930,000660,035420"
```

Dry run (test without actually seeding):
```bash
python scripts/seed_stock_data.py --dry-run
```

Skip price data collection:
```bash
python scripts/seed_stock_data.py --skip-prices
```

Skip fundamental data collection:
```bash
python scripts/seed_stock_data.py --skip-fundamentals
```

#### Default Stock List

The script seeds 35 representative Korean stocks by default:
- **KOSPI Large Cap**: Samsung Electronics, SK Hynix, NAVER, LG Chem, Kakao, Hyundai Motor, etc.
- **KOSPI Mid Cap**: Samsung SDS, Orion, SK, Lotte Chemical, etc.
- **KOSDAQ Growth**: Ecopro BM, Ecopro, Alteogen, Kakao Games, etc.

See [scripts/README.md](scripts/README.md) for the complete list and more details.

#### Data Requirements

The seeding script ensures sufficient data for technical indicator calculations:
- **SMA 200**: Requires at least 200 days of price data
- **MACD**: Requires at least 26 days of price data
- **RSI**: Requires at least 14 days of price data

Default collection period is 365 days to ensure adequate data for all indicators.

#### Next Steps After Seeding

After seeding the data, run these services to calculate indicators and scores:
1. **Indicator Calculator Service**: Computes technical indicators (RSI, MACD, moving averages, etc.)
2. **Stock Scorer Service**: Calculates composite investment scores
3. **Stability Calculator Service**: Computes stability and risk scores

```bash
# Example workflow
python scripts/seed_stock_data.py --days 365
# Then start the indicator calculator and scorer services
```

**Note**: Data seeding may take 10-30 minutes depending on network speed and the number of stocks being seeded. The script includes rate limiting to avoid overwhelming external APIs.

## Configuration

Configuration is managed through environment variables. Copy `shared/configs/.env.example` to `.env` and configure:

### Database Configuration
```env
DATABASE_URL=postgresql://user:password@localhost:5432/stock_trading
```

### Redis Configuration
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### API Keys
```env
KRX_API_KEY=your_krx_api_key
KOREAINVESTMENT_API_KEY=your_api_key
KOREAINVESTMENT_API_SECRET=your_api_secret
```

### Risk Parameters
```env
DEFAULT_STOP_LOSS_PCT=5.0
MAX_POSITION_SIZE_PCT=10.0
MAX_PORTFOLIO_RISK_PCT=2.0
```

## Development

### Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Run code formatting:
```bash
black services/ shared/
isort services/ shared/
```

Run linting:
```bash
flake8 services/ shared/
mypy services/ shared/
```

### Adding a New Service

1. Create service directory: `services/your_service/`
2. Add `__init__.py`, `main.py`, and `requirements.txt`
3. Create Dockerfile: `docker/Dockerfile.your_service`
4. Add service to `docker-compose.yml`
5. Update this README

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov=shared --cov-report=html

# Run specific test file
pytest tests/test_utilities.py

# Run with verbose output
pytest -v
```

Coverage reports are generated in `htmlcov/` directory.

## Deployment

### Docker Deployment

Build and deploy all services:

```bash
cd docker
docker-compose build
docker-compose up -d
```

### Production Considerations

1. **Environment Variables**: Use secure secret management (e.g., AWS Secrets Manager, HashiCorp Vault)
2. **Database**: Set up PostgreSQL with replication and backups
3. **Monitoring**: Implement logging and monitoring (Prometheus, Grafana)
4. **API Gateway**: Add Kong or Nginx as API gateway
5. **Load Balancing**: Use load balancers for each service
6. **Security**: Implement authentication and authorization

## API Documentation

Each service provides OpenAPI documentation:

- Data Collector: http://localhost:8001/docs
- Indicator Calculator: http://localhost:8002/docs
- Stock Screener: http://localhost:8003/docs
- Trading Engine: http://localhost:8004/docs
- Risk Manager: http://localhost:8005/docs

## Database Schema

Key tables:
- `stocks`: Stock information (ticker, name, market, sector)
- `stock_prices`: Historical and real-time price data
- `technical_indicators`: Calculated technical indicators
- `trades`: Trade execution records
- `portfolios`: Portfolio holdings and positions

## Roadmap

- [ ] Implement Korean stock data provider integrations
- [ ] Add WebSocket support for real-time data streaming
- [ ] Implement backtesting engine
- [ ] Add machine learning models for prediction
- [ ] Create web dashboard for monitoring
- [ ] Add support for options and futures trading
- [ ] Implement automated strategy execution
- [ ] Add comprehensive logging and alerting

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. Trading stocks involves risk. Always do your own research and consult with financial advisors before making investment decisions. The authors are not responsible for any financial losses incurred through the use of this software.

## Contact

For questions or support, please open an issue on GitHub.

## Acknowledgments

- Korean Exchange (KRX) for market data
- FastAPI framework
- SQLAlchemy ORM
- Docker and containerization community
