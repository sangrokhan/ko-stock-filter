"""
Date and time utility functions.
"""
from datetime import datetime, timedelta
from typing import List
import pytz


KST = pytz.timezone('Asia/Seoul')


def get_kst_now() -> datetime:
    """
    Get current time in Korean Standard Time.

    Returns:
        Current KST datetime
    """
    return datetime.now(KST)


def convert_to_kst(dt: datetime) -> datetime:
    """
    Convert datetime to Korean Standard Time.

    Args:
        dt: Datetime to convert

    Returns:
        KST datetime
    """
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(KST)


def is_market_open(dt: Optional[datetime] = None) -> bool:
    """
    Check if Korean stock market is open.
    Market hours: 09:00 - 15:30 KST, Monday-Friday

    Args:
        dt: Datetime to check (default: current time)

    Returns:
        True if market is open, False otherwise
    """
    if dt is None:
        dt = get_kst_now()
    elif dt.tzinfo is None:
        dt = KST.localize(dt)
    else:
        dt = convert_to_kst(dt)

    # Check if weekend
    if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Check market hours
    market_open = dt.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = dt.replace(hour=15, minute=30, second=0, microsecond=0)

    return market_open <= dt <= market_close


def get_trading_days(start_date: datetime, end_date: datetime) -> List[datetime]:
    """
    Get list of trading days between two dates.
    Excludes weekends (does not account for holidays).

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        List of trading days
    """
    trading_days = []
    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            trading_days.append(current_date)
        current_date += timedelta(days=1)

    return trading_days
