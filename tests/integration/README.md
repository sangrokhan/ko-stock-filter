# Integration Tests

Comprehensive integration tests for the Korean Stock Trading System.

## Overview

This integration test suite provides end-to-end testing of the trading system, including:

- **End-to-end workflows** - Complete trading pipelines from data collection to order execution
- **Database operations** - CRUD operations across all models with transaction handling
- **Service communication** - HTTP API testing and inter-service communication
- **Error handling** - Fault tolerance, recovery mechanisms, and edge cases

## Architecture

### Test Environment

Integration tests run against a dedicated test environment using Docker Compose:

- **PostgreSQL Test Database** - Isolated test database on port 5433
- **Redis Test Cache** - Separate Redis instance on port 6380
- **Microservices** - All 5 core services running in test mode
  - Data Collector (port 8101)
  - Indicator Calculator (port 8102)
  - Stock Screener (port 8103)
  - Trading Engine (port 8104)
  - Risk Manager (port 8105)

### Test Structure

```
tests/integration/
├── conftest.py                      # Fixtures and test configuration
├── test_utils.py                    # Utility functions for testing
├── test_e2e_workflow.py            # End-to-end workflow tests
├── test_database_crud.py           # Database CRUD operations
├── test_service_communication.py   # Service API tests
├── test_error_handling.py          # Error handling and recovery
└── README.md                        # This file
```

## Prerequisites

### Required Software

- Docker and Docker Compose
- Python 3.11+
- PostgreSQL client tools (optional, for debugging)

### Python Dependencies

```bash
pip install -r requirements.txt
```

Key test dependencies:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `requests` - HTTP client for API testing
- `sqlalchemy` - Database ORM

## Setup

### 1. Environment Configuration

Create a `.env.test` file with test configuration:

```bash
# Test Database
TEST_DATABASE_URL=postgresql://test_user:test_password@localhost:5433/stock_trading_test

# Test Services
TEST_DATA_COLLECTOR_URL=http://localhost:8101
TEST_INDICATOR_CALCULATOR_URL=http://localhost:8102
TEST_STOCK_SCREENER_URL=http://localhost:8103
TEST_TRADING_ENGINE_URL=http://localhost:8104
TEST_RISK_MANAGER_URL=http://localhost:8105

# Test Settings
LOG_LEVEL=DEBUG
ENVIRONMENT=test
PAPER_TRADING_MODE=true
```

### 2. Start Test Environment

```bash
# Navigate to docker directory
cd docker

# Start test services
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be ready (health checks)
docker-compose -f docker-compose.test.yml ps

# View logs
docker-compose -f docker-compose.test.yml logs -f
```

### 3. Verify Services are Running

```bash
# Check PostgreSQL
docker exec stock-trading-db-test pg_isready -U test_user

# Check Redis
docker exec stock-trading-redis-test redis-cli ping

# Check service health endpoints
curl http://localhost:8101/health
curl http://localhost:8102/health
curl http://localhost:8103/health
curl http://localhost:8104/health
curl http://localhost:8105/health
```

## Running Tests

### Run All Integration Tests

```bash
# From project root
pytest tests/integration/ -v

# With coverage
pytest tests/integration/ -v --cov=services --cov=shared --cov-report=html
```

### Run Specific Test Suites

```bash
# End-to-end workflow tests only
pytest tests/integration/test_e2e_workflow.py -v

# Database CRUD tests only
pytest tests/integration/test_database_crud.py -v

# Service communication tests only
pytest tests/integration/test_service_communication.py -v

# Error handling tests only
pytest tests/integration/test_error_handling.py -v
```

### Run Tests by Marker

```bash
# Run only E2E tests
pytest tests/integration/ -v -m e2e

# Run only database tests
pytest tests/integration/ -v -m database

# Run only service tests
pytest tests/integration/ -v -m service

# Run only error handling tests
pytest tests/integration/ -v -m error_handling
```

### Run with Specific Options

```bash
# Verbose output with detailed logs
pytest tests/integration/ -vv --log-cli-level=DEBUG

# Stop on first failure
pytest tests/integration/ -x

# Run in parallel (requires pytest-xdist)
pytest tests/integration/ -n auto

# Generate HTML report
pytest tests/integration/ --html=report.html --self-contained-html
```

## Test Suites

### 1. End-to-End Workflow Tests (`test_e2e_workflow.py`)

Tests complete trading workflows:

- **Complete Trading Workflow** - Data collection → Indicators → Screening → Signals → Execution
- **Watchlist to Trade** - Adding stocks to watchlist → Monitoring → Signal generation → Trade execution
- **Risk Management Workflow** - Position sizing → Risk validation → Order execution → Portfolio update
- **Multi-Stock Screening** - Screening multiple stocks → Building watchlist → Generating signals
- **Position Monitoring** - Monitoring positions → Stop-loss/take-profit triggers

**Key Features:**
- Tests all services working together
- Validates data flow through the system
- Checks business logic end-to-end

### 2. Database CRUD Tests (`test_database_crud.py`)

Tests database operations:

- **Basic CRUD** - Create, Read, Update, Delete for all models
- **Foreign Key Relationships** - Cascade deletes, referential integrity
- **Transaction Management** - Commits, rollbacks, isolation
- **Constraint Validation** - Unique constraints, check constraints
- **Bulk Operations** - Bulk inserts, batch updates
- **Complex Queries** - Joins, aggregations, filtering

**Models Tested:**
- Stock, StockPrice, TechnicalIndicator, FundamentalIndicator
- Trade, Portfolio, PortfolioRiskMetrics
- Watchlist, WatchlistHistory
- CompositeScore, StabilityScore

### 3. Service Communication Tests (`test_service_communication.py`)

Tests HTTP APIs and service interactions:

- **Health Checks** - All service health endpoints
- **API Endpoints** - Request/response validation
- **Inter-Service Communication** - Orchestrated workflows across services
- **Error Responses** - 4xx and 5xx error handling
- **Request Validation** - Parameter validation, type checking
- **Concurrent Requests** - Thread safety, race conditions
- **Response Formats** - JSON structure, content-type headers

**Services Tested:**
- Data Collector API
- Indicator Calculator API
- Stock Screener API
- Trading Engine API
- Risk Manager API

### 4. Error Handling Tests (`test_error_handling.py`)

Tests fault tolerance and recovery:

- **Database Errors** - Constraint violations, foreign key errors, transaction rollbacks
- **API Errors** - Invalid requests, missing parameters, malformed JSON
- **Service Failures** - Timeouts, unavailable services, network errors
- **Business Logic Errors** - Invalid orders, insufficient funds, duplicate prevention
- **Data Validation Errors** - Invalid price data, negative quantities
- **Concurrent Operations** - Update conflicts, race conditions
- **Recovery Mechanisms** - Retry logic, fallback strategies

## Fixtures and Utilities

### Database Fixtures

- `integration_db_engine` - SQLAlchemy engine for test database
- `integration_db_session` - Database session per test (auto-rollback)
- `clean_database` - Ensures clean database state

### Sample Data Fixtures

- `sample_stocks` - 5 Korean stocks (Samsung, SK Hynix, Naver, Hyundai, LG Chem)
- `sample_stock_prices` - 30 days of OHLCV data per stock
- `sample_technical_indicators` - Technical indicators for each stock
- `sample_fundamental_indicators` - Fundamental metrics for each stock
- `sample_portfolio` - Portfolio positions for testing
- `sample_watchlist` - Watchlist entries for testing

### Service Fixtures

- `wait_for_services` - Waits for all services to be healthy
- `service_urls` - Dictionary of service URLs
- `api_client` - Configured requests session
- `test_user_id` - Consistent test user ID
- `test_timeout` - Standard timeout for API requests

### Utility Functions

- `wait_for_condition()` - Wait for a condition to become true
- `wait_for_service_health()` - Wait for service health check
- `assert_response_success()` - Assert HTTP response is successful
- `assert_response_contains_fields()` - Assert response has required fields
- `retry_on_failure()` - Retry with exponential backoff
- `validate_stock_data()` - Validate stock data structure
- `validate_price_data()` - Validate OHLCV data structure

## Test Data

### Sample Stocks

| Ticker | Name | Market | Sector | Market Cap |
|--------|------|--------|--------|------------|
| 005930 | 삼성전자 | KOSPI | 전기전자 | 400T KRW |
| 000660 | SK하이닉스 | KOSPI | 전기전자 | 80T KRW |
| 035420 | NAVER | KOSPI | 서비스업 | 30T KRW |
| 005380 | 현대차 | KOSPI | 운수장비 | 40T KRW |
| 051910 | LG화학 | KOSPI | 화학 | 35T KRW |

### Price Data

- 30 days of historical OHLCV data per stock
- Realistic price variations
- Valid volume data

## Debugging

### View Test Logs

```bash
# Run with verbose logging
pytest tests/integration/ -vv --log-cli-level=DEBUG

# Save logs to file
pytest tests/integration/ -v --log-file=test.log
```

### Debug Database State

```bash
# Connect to test database
docker exec -it stock-trading-db-test psql -U test_user -d stock_trading_test

# View tables
\dt

# Query data
SELECT * FROM stock;
SELECT * FROM stock_price LIMIT 10;
```

### Inspect Service Logs

```bash
# View all service logs
docker-compose -f docker/docker-compose.test.yml logs

# View specific service
docker-compose -f docker/docker-compose.test.yml logs data-collector-test

# Follow logs in real-time
docker-compose -f docker/docker-compose.test.yml logs -f trading-engine-test
```

### Debug Failed Tests

```bash
# Run with Python debugger
pytest tests/integration/test_e2e_workflow.py --pdb

# Run single test with verbose output
pytest tests/integration/test_e2e_workflow.py::TestEndToEndWorkflow::test_complete_trading_workflow -vv

# Show local variables on failure
pytest tests/integration/ -l
```

## Cleanup

### Stop Test Environment

```bash
# Stop services
cd docker
docker-compose -f docker-compose.test.yml down

# Stop and remove volumes
docker-compose -f docker-compose.test.yml down -v

# Remove all test containers and networks
docker-compose -f docker-compose.test.yml down --remove-orphans
```

### Clean Test Data

```bash
# Reset test database
docker exec stock-trading-db-test psql -U test_user -d stock_trading_test -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Clear Redis cache
docker exec stock-trading-redis-test redis-cli FLUSHALL
```

## Best Practices

### Writing Integration Tests

1. **Use Fixtures** - Leverage existing fixtures for common setup
2. **Clean State** - Each test should start with clean database state
3. **Test Isolation** - Tests should not depend on each other
4. **Meaningful Assertions** - Assert on business logic, not implementation details
5. **Error Messages** - Use descriptive assertion messages
6. **Test Data** - Use realistic test data that matches production scenarios

### Example Test

```python
@pytest.mark.integration
def test_complete_workflow(
    integration_db_session,
    service_urls,
    api_client,
    sample_stocks,
    test_timeout,
):
    """
    Test complete workflow with descriptive docstring.
    """
    # Arrange - Set up test data
    stock = sample_stocks[0]

    # Act - Perform the action
    response = api_client.post(
        f"{service_urls['trading_engine']}/api/v1/orders/execute",
        json={
            "stock_id": stock.id,
            "order_type": "buy",
            "quantity": 10,
        },
        timeout=test_timeout,
    )

    # Assert - Verify results
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "executed"
```

## Continuous Integration

### GitHub Actions

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Start test services
        run: |
          cd docker
          docker-compose -f docker-compose.test.yml up -d

      - name: Wait for services
        run: sleep 30

      - name: Run tests
        run: |
          pytest tests/integration/ -v --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Performance

### Test Execution Time

- **All Integration Tests**: ~5-10 minutes
- **End-to-End Tests**: ~2-3 minutes
- **Database Tests**: ~1-2 minutes
- **Service Communication Tests**: ~1-2 minutes
- **Error Handling Tests**: ~1-2 minutes

### Optimization Tips

1. **Parallel Execution** - Use `pytest-xdist` for parallel test runs
2. **Selective Testing** - Run only relevant test suites during development
3. **Fast Fixtures** - Use `tmpfs` for database and Redis in Docker
4. **Connection Pooling** - Reuse database connections where possible

## Troubleshooting

### Common Issues

**Services not starting:**
- Check Docker logs: `docker-compose -f docker-compose.test.yml logs`
- Verify ports are not in use: `netstat -tuln | grep 543`
- Rebuild images: `docker-compose -f docker-compose.test.yml build`

**Database connection errors:**
- Verify PostgreSQL is running: `docker ps`
- Check connection string in `.env.test`
- Ensure port 5433 is accessible

**Test timeouts:**
- Increase timeout values in fixtures
- Check service health endpoints
- Review service logs for errors

**Flaky tests:**
- Add proper wait conditions
- Use `wait_for_condition()` utility
- Increase timeouts for slow operations

## Contributing

When adding new integration tests:

1. Follow existing test structure and naming conventions
2. Add appropriate pytest markers (`@pytest.mark.integration`)
3. Use existing fixtures where possible
4. Document complex test scenarios
5. Ensure tests are idempotent and isolated
6. Update this README if adding new test suites

## Support

For issues or questions:
- Review test logs and service logs
- Check Docker Compose configuration
- Verify environment variables
- Consult service documentation

## License

Same as main project.
