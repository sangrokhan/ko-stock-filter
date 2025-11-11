# Tests

This directory contains the test suite for the Korean Stock Trading System.

## Test Structure

```
tests/
├── conftest.py                      # Pytest fixtures and configuration
├── test_stock_code_collector.py     # Tests for stock code collection
├── test_seed_stock_data.py          # Tests for data seeding script
├── test_price_collector.py          # Tests for price data collection
├── test_fundamental_collector.py    # Tests for fundamental data collection
├── test_technical_calculator.py     # Tests for technical indicators
├── test_financial_calculator.py     # Tests for financial calculations
├── test_stock_scorer.py             # Tests for stock scoring
├── test_stock_screener.py           # Tests for stock screening
├── test_stability_calculator.py     # Tests for stability calculations
├── test_watchlist_manager.py        # Tests for watchlist management
├── test_order_executor.py           # Tests for order execution
├── test_price_monitor.py            # Tests for price monitoring
├── test_ticker_retrieval.py         # Tests for ticker retrieval
├── test_utilities.py                # Tests for utility functions
└── integration/                     # Integration tests
    ├── conftest.py                  # Integration test fixtures
    ├── test_e2e_workflow.py         # End-to-end workflow tests
    ├── test_database_crud.py        # Database CRUD tests
    ├── test_error_handling.py       # Error handling tests
    ├── test_service_communication.py # Service communication tests
    └── test_utils.py                # Integration test utilities
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements.txt
# or
pip install -e ".[dev]"
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_stock_code_collector.py
pytest tests/test_seed_stock_data.py
```

### Run Specific Test Class or Method

```bash
# Run specific test class
pytest tests/test_stock_code_collector.py::TestStockCodeCollector

# Run specific test method
pytest tests/test_stock_code_collector.py::TestStockCodeCollector::test_collect_single_stock_new_stock
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage Report

```bash
# Generate coverage report
pytest --cov=services --cov=shared --cov=scripts --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Run Only Unit Tests (exclude integration tests)

```bash
pytest tests/ --ignore=tests/integration/
```

### Run Only Integration Tests

```bash
pytest tests/integration/
```

### Run Tests in Parallel

```bash
# Install pytest-xdist first
pip install pytest-xdist

# Run tests in parallel
pytest -n auto
```

### Run Tests with Markers

```bash
# Run only fast tests
pytest -m "not slow"

# Run only tests that require network
pytest -m "network"
```

## Test Coverage

### Recently Added Tests

#### test_stock_code_collector.py
Tests for the `StockCodeCollector` class in `services/data_collector/stock_code_collector.py`:

**Coverage:**
- ✅ `fetch_stock_codes()` - Fetch stock codes from markets
- ✅ `fetch_stock_details()` - Fetch market cap and shares
- ✅ `collect_single_stock()` - Collect single stock (new feature)
- ✅ `collect_all_stock_codes()` - Collect all stocks from all markets
- ✅ `_save_stocks_to_db()` - Save stocks to database with batching
- ✅ `update_stock_details()` - Update stock details

**Test Scenarios:**
- New stock collection
- Existing stock update
- Stock not found handling
- API error handling
- Batch commit logic
- Multiple market handling
- Partial failures

#### test_seed_stock_data.py
Tests for the `DataSeeder` class in `scripts/seed_stock_data.py`:

**Coverage:**
- ✅ Initialization with various options
- ✅ Dry-run mode behavior
- ✅ Stock metadata seeding
- ✅ Price data seeding
- ✅ Fundamental data seeding
- ✅ Complete seeding workflow
- ✅ Skip options (--skip-prices, --skip-fundamentals)
- ✅ Database checks (existing data detection)
- ✅ Error handling and recovery

**Test Scenarios:**
- New stock seeding
- Existing stock detection
- Sufficient data skip logic
- Collector failures
- Partial success handling
- Date range calculations
- Ticker filtering

## Test Fixtures

Common fixtures available in `conftest.py`:

### Database Fixtures
- `test_db_engine` - In-memory SQLite database engine
- `test_db_session` - Database session for tests
- `sample_stock` - Sample stock record
- `sample_stock_prices` - Sample price data (30 days)

### Data Fixtures
- `sample_stock_data` - Sample stock metadata
- `sample_price_data` - Sample price records
- `sample_fundamental_data` - Sample fundamental indicators
- `sample_technical_data` - Sample technical indicators
- `sample_price_dataframe` - Sample price DataFrame (pandas)

### Mock Fixtures
- `mock_fdr_data` - Mock FinanceDataReader data
- `mock_pykrx_fundamental` - Mock pykrx fundamental data
- `mock_pykrx_market_cap` - Mock pykrx market cap data
- `mock_redis` - Mock Redis client
- `mock_external_api` - Mock external API responses
- `mock_celery_task` - Mock Celery task

### Environment Fixtures
- `mock_environment_variables` - Mock environment variables (autouse)

## Writing New Tests

### Test Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `TestClassName`
- Test methods: `test_<functionality>_<scenario>`

Example:
```python
class TestStockCodeCollector:
    def test_collect_single_stock_new_stock(self):
        """Test collecting a single new stock."""
        pass

    def test_collect_single_stock_existing_stock(self):
        """Test updating an existing stock."""
        pass
```

### Using Mocks

Always mock external dependencies (APIs, network calls, file I/O):

```python
from unittest.mock import Mock, patch

@patch('services.data_collector.stock_code_collector.fdr.StockListing')
def test_fetch_stock_codes_success(self, mock_stock_listing, collector):
    """Test successful stock codes fetch."""
    mock_stock_listing.return_value = pd.DataFrame(...)
    result = collector.fetch_stock_codes('KOSPI')
    assert result is not None
```

### Using Database Fixtures

Use `test_db_session` for database operations:

```python
def test_save_stock(test_db_session):
    """Test saving a stock to database."""
    stock = Stock(ticker='005930', name_kr='삼성전자')
    test_db_session.add(stock)
    test_db_session.commit()

    saved_stock = test_db_session.query(Stock).filter(
        Stock.ticker == '005930'
    ).first()
    assert saved_stock is not None
```

### Parametrize Tests

Use `pytest.mark.parametrize` for testing multiple scenarios:

```python
@pytest.mark.parametrize("days,expected", [
    (30, 30),
    (90, 90),
    (365, 365),
])
def test_date_range_calculation(days, expected):
    """Test date range calculation for different days values."""
    seeder = DataSeeder(days=days)
    actual_days = (seeder.end_date - seeder.start_date).days
    assert actual_days == expected
```

## Continuous Integration

Tests are automatically run on:
- Pull request creation
- Push to main branch
- Scheduled daily runs

### CI Configuration

See `.github/workflows/test.yml` for CI configuration.

## Troubleshooting

### Common Issues

**Issue: Tests fail with "No module named pytest"**
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

**Issue: Tests fail with database errors**
```bash
# Make sure to use test_db_session fixture
def test_something(test_db_session):
    # Use test_db_session instead of creating your own
```

**Issue: Tests fail with import errors**
```bash
# Make sure project root is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

**Issue: Tests are slow**
```bash
# Run tests in parallel
pip install pytest-xdist
pytest -n auto
```

## Best Practices

1. **Isolate tests**: Each test should be independent
2. **Mock external dependencies**: Don't make real API calls
3. **Use fixtures**: Reuse common test data and setup
4. **Test edge cases**: Test both success and failure scenarios
5. **Keep tests fast**: Mock slow operations (network, disk I/O)
6. **Clear test names**: Test name should describe what is being tested
7. **Add docstrings**: Explain what each test does
8. **Clean up**: Tests should clean up after themselves (fixtures handle this)

## Test Metrics

### Target Coverage
- Overall: > 80%
- Critical paths: > 90%
- New features: 100%

### Performance Targets
- Unit tests: < 5 minutes for full suite
- Integration tests: < 10 minutes for full suite
- Single test: < 1 second (excluding integration tests)

## Contributing

When adding new features:
1. Write tests first (TDD approach recommended)
2. Ensure all tests pass
3. Maintain or improve coverage
4. Add docstrings to test methods
5. Update this README if adding new test patterns

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Python Testing with pytest](https://pragprog.com/titles/bopytest/python-testing-with-pytest/)
