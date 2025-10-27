"""
Data validation utilities.
"""
import re
from datetime import datetime
from typing import Optional


def validate_korean_ticker(ticker: str) -> bool:
    """
    Validate Korean stock ticker format.

    Args:
        ticker: Stock ticker symbol

    Returns:
        True if valid, False otherwise
    """
    # Korean stock tickers are typically 6-digit codes
    pattern = r'^\d{6}$'
    return bool(re.match(pattern, ticker))


def validate_date_format(date_str: str, format: str = "%Y-%m-%d") -> bool:
    """
    Validate date string format.

    Args:
        date_str: Date string to validate
        format: Expected date format

    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(date_str, format)
        return True
    except ValueError:
        return False


def validate_price(price: float) -> bool:
    """
    Validate stock price.

    Args:
        price: Price to validate

    Returns:
        True if valid, False otherwise
    """
    return price > 0


def validate_quantity(quantity: int) -> bool:
    """
    Validate trade quantity.

    Args:
        quantity: Quantity to validate

    Returns:
        True if valid, False otherwise
    """
    return quantity > 0 and isinstance(quantity, int)
