"""
Utility functions for integration tests.

Provides helper functions for common testing operations like
waiting for async tasks, validating responses, and test data generation.
"""

import time
from typing import Callable, Any, Dict, Optional
from datetime import datetime, timedelta

import requests
from requests.exceptions import RequestException


def wait_for_condition(
    condition: Callable[[], bool],
    timeout: int = 30,
    interval: float = 0.5,
    error_message: str = "Condition not met within timeout"
) -> bool:
    """
    Wait for a condition to become true.

    Args:
        condition: A callable that returns True when the condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        error_message: Error message if timeout is reached

    Returns:
        True if condition was met

    Raises:
        TimeoutError: If condition is not met within timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(interval)

    raise TimeoutError(error_message)


def wait_for_service_health(
    service_url: str,
    timeout: int = 30,
    health_endpoint: str = "/health"
) -> bool:
    """
    Wait for a service to become healthy.

    Args:
        service_url: Base URL of the service
        timeout: Maximum time to wait in seconds
        health_endpoint: Health check endpoint path

    Returns:
        True if service became healthy

    Raises:
        TimeoutError: If service doesn't become healthy within timeout
    """
    health_url = f"{service_url}{health_endpoint}"

    def is_healthy():
        try:
            response = requests.get(health_url, timeout=5)
            return response.status_code == 200
        except RequestException:
            return False

    return wait_for_condition(
        condition=is_healthy,
        timeout=timeout,
        interval=1,
        error_message=f"Service at {service_url} did not become healthy within {timeout} seconds"
    )


def assert_response_success(response: requests.Response, expected_status: int = 200):
    """
    Assert that an HTTP response was successful.

    Args:
        response: The response to check
        expected_status: Expected HTTP status code

    Raises:
        AssertionError: If response status doesn't match expected
    """
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response body: {response.text}"
    )


def assert_response_contains_fields(response_data: Dict[str, Any], required_fields: list[str]):
    """
    Assert that response data contains all required fields.

    Args:
        response_data: The response data dictionary
        required_fields: List of field names that must be present

    Raises:
        AssertionError: If any required field is missing
    """
    missing_fields = [field for field in required_fields if field not in response_data]

    assert not missing_fields, (
        f"Response is missing required fields: {missing_fields}. "
        f"Available fields: {list(response_data.keys())}"
    )


def generate_price_data(
    base_price: float = 50000,
    num_days: int = 30,
    volatility: float = 0.02
) -> list[Dict[str, Any]]:
    """
    Generate sample OHLCV price data for testing.

    Args:
        base_price: Starting price
        num_days: Number of days of data to generate
        volatility: Price volatility factor (0.0 - 1.0)

    Returns:
        List of dictionaries containing OHLCV data
    """
    prices = []
    current_price = base_price
    base_date = datetime.now().date() - timedelta(days=num_days)

    for day in range(num_days):
        # Random walk with mean reversion
        import random
        change = random.uniform(-volatility, volatility)
        current_price = current_price * (1 + change)

        # Generate OHLC from current price
        open_price = current_price * random.uniform(0.99, 1.01)
        close_price = current_price * random.uniform(0.99, 1.01)
        high_price = max(open_price, close_price) * random.uniform(1.0, 1.02)
        low_price = min(open_price, close_price) * random.uniform(0.98, 1.0)
        volume = int(1000000 * random.uniform(0.5, 2.0))

        prices.append({
            "date": (base_date + timedelta(days=day)).isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume,
        })

    return prices


def retry_on_failure(
    func: Callable,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry a function on failure with exponential backoff.

    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to catch and retry on

    Returns:
        Result of successful function call

    Raises:
        Last exception if all attempts fail
    """
    last_exception = None
    current_delay = delay

    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            last_exception = e

            if attempt < max_attempts - 1:
                time.sleep(current_delay)
                current_delay *= backoff
            else:
                raise last_exception


def validate_stock_data(stock_data: Dict[str, Any]) -> bool:
    """
    Validate that stock data has all required fields.

    Args:
        stock_data: Stock data dictionary to validate

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails
    """
    required_fields = ["ticker", "name", "market"]

    missing = [field for field in required_fields if field not in stock_data]

    if missing:
        raise ValueError(f"Stock data missing required fields: {missing}")

    # Validate ticker format (Korean stocks are 6 digits)
    if not stock_data["ticker"].isdigit() or len(stock_data["ticker"]) != 6:
        raise ValueError(f"Invalid ticker format: {stock_data['ticker']}")

    # Validate market
    valid_markets = ["KOSPI", "KOSDAQ"]
    if stock_data["market"] not in valid_markets:
        raise ValueError(f"Invalid market: {stock_data['market']}")

    return True


def validate_price_data(price_data: Dict[str, Any]) -> bool:
    """
    Validate that price data has all required OHLCV fields.

    Args:
        price_data: Price data dictionary to validate

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails
    """
    required_fields = ["date", "open", "high", "low", "close", "volume"]

    missing = [field for field in required_fields if field not in price_data]

    if missing:
        raise ValueError(f"Price data missing required fields: {missing}")

    # Validate OHLC relationships
    if not (price_data["low"] <= price_data["open"] <= price_data["high"]):
        raise ValueError("Invalid OHLC: open price outside low-high range")

    if not (price_data["low"] <= price_data["close"] <= price_data["high"]):
        raise ValueError("Invalid OHLC: close price outside low-high range")

    # Validate volume is positive
    if price_data["volume"] <= 0:
        raise ValueError("Volume must be positive")

    return True


def compare_floats(a: float, b: float, tolerance: float = 0.01) -> bool:
    """
    Compare two floating point numbers with tolerance.

    Args:
        a: First number
        b: Second number
        tolerance: Acceptable difference (relative)

    Returns:
        True if numbers are equal within tolerance
    """
    if a == 0 and b == 0:
        return True

    if a == 0 or b == 0:
        return abs(a - b) < tolerance

    return abs((a - b) / max(abs(a), abs(b))) < tolerance


def wait_for_database_record(
    session,
    model_class,
    filter_condition,
    timeout: int = 10
) -> Optional[Any]:
    """
    Wait for a database record to appear.

    Args:
        session: SQLAlchemy session
        model_class: Model class to query
        filter_condition: SQLAlchemy filter condition
        timeout: Maximum time to wait in seconds

    Returns:
        The record if found, None if timeout

    Example:
        record = wait_for_database_record(
            session,
            Stock,
            Stock.ticker == "005930",
            timeout=5
        )
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        record = session.query(model_class).filter(filter_condition).first()
        if record:
            return record
        time.sleep(0.5)

    return None


def create_test_trade_data(
    stock_id: int,
    user_id: str,
    order_type: str = "buy",
    quantity: int = 100,
    price: float = 50000
) -> Dict[str, Any]:
    """
    Create test trade data for API requests.

    Args:
        stock_id: Stock ID
        user_id: User ID
        order_type: Type of order (buy/sell)
        quantity: Number of shares
        price: Price per share

    Returns:
        Dictionary with trade data
    """
    return {
        "user_id": user_id,
        "stock_id": stock_id,
        "order_type": order_type,
        "order_action": "market",
        "quantity": quantity,
        "price": price,
        "stop_loss_price": price * 0.95 if order_type == "buy" else None,
        "take_profit_price": price * 1.10 if order_type == "buy" else None,
    }
