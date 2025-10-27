"""
Korean Stock Market Calendar and Hours Detection.

Handles market hours (09:00-15:30 KST) and holiday detection.
"""
from datetime import datetime, time, date
from typing import Optional
import pytz
from dateutil.relativedelta import relativedelta


class KoreanMarketCalendar:
    """Korean Stock Market (KRX) calendar and trading hours."""

    # Market trading hours (KST)
    MARKET_OPEN = time(9, 0)  # 09:00 KST
    MARKET_CLOSE = time(15, 30)  # 15:30 KST

    # Timezone
    KST = pytz.timezone('Asia/Seoul')

    def __init__(self):
        """Initialize market calendar with Korean holidays."""
        self._holidays = self._get_holidays_2024_2025()

    def _get_holidays_2024_2025(self) -> set:
        """
        Get Korean stock market holidays for 2024-2025.

        Returns:
            Set of holiday dates
        """
        holidays = set()

        # Fixed holidays
        # New Year's Day (January 1)
        holidays.add(date(2024, 1, 1))
        holidays.add(date(2025, 1, 1))

        # Independence Movement Day (March 1)
        holidays.add(date(2024, 3, 1))
        holidays.add(date(2025, 3, 1))

        # Labor Day (May 1)
        holidays.add(date(2024, 5, 1))
        holidays.add(date(2025, 5, 1))

        # Children's Day (May 5)
        holidays.add(date(2024, 5, 5))
        holidays.add(date(2025, 5, 5))

        # Memorial Day (June 6)
        holidays.add(date(2024, 6, 6))
        holidays.add(date(2025, 6, 6))

        # Liberation Day (August 15)
        holidays.add(date(2024, 8, 15))
        holidays.add(date(2025, 8, 15))

        # National Foundation Day (October 3)
        holidays.add(date(2024, 10, 3))
        holidays.add(date(2025, 10, 3))

        # Hangeul Day (October 9)
        holidays.add(date(2024, 10, 9))
        holidays.add(date(2025, 10, 9))

        # Christmas Day (December 25)
        holidays.add(date(2024, 12, 25))
        holidays.add(date(2025, 12, 25))

        # Lunar New Year 2024 (Feb 9-12)
        holidays.add(date(2024, 2, 9))
        holidays.add(date(2024, 2, 10))
        holidays.add(date(2024, 2, 11))
        holidays.add(date(2024, 2, 12))

        # Lunar New Year 2025 (Jan 28-30)
        holidays.add(date(2025, 1, 28))
        holidays.add(date(2025, 1, 29))
        holidays.add(date(2025, 1, 30))

        # Buddha's Birthday 2024 (May 15)
        holidays.add(date(2024, 5, 15))

        # Buddha's Birthday 2025 (May 5 - combined with Children's Day)
        # Already added as Children's Day

        # Chuseok (Korean Thanksgiving) 2024 (Sep 16-18)
        holidays.add(date(2024, 9, 16))
        holidays.add(date(2024, 9, 17))
        holidays.add(date(2024, 9, 18))

        # Chuseok 2025 (Oct 5-7)
        holidays.add(date(2025, 10, 5))
        holidays.add(date(2025, 10, 6))
        holidays.add(date(2025, 10, 7))

        # Substitute holidays (when holiday falls on weekend)
        holidays.add(date(2024, 2, 12))  # Lunar New Year substitute
        holidays.add(date(2024, 4, 10))  # Election Day

        # Year-end market closures (December 31)
        # Check if December 31 is a trading day or not
        # Usually, KRX is closed on Dec 31
        holidays.add(date(2024, 12, 31))
        holidays.add(date(2025, 12, 31))

        return holidays

    def is_holiday(self, check_date: Optional[date] = None) -> bool:
        """
        Check if a given date is a market holiday.

        Args:
            check_date: Date to check. If None, uses today.

        Returns:
            True if the date is a holiday
        """
        if check_date is None:
            check_date = datetime.now(self.KST).date()

        # Weekend check
        if check_date.weekday() >= 5:  # Saturday=5, Sunday=6
            return True

        # Holiday check
        return check_date in self._holidays

    def is_market_open(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if the market is currently open.

        Args:
            check_time: Datetime to check. If None, uses current time.

        Returns:
            True if market is open
        """
        if check_time is None:
            check_time = datetime.now(self.KST)
        else:
            # Ensure timezone is KST
            if check_time.tzinfo is None:
                check_time = self.KST.localize(check_time)
            else:
                check_time = check_time.astimezone(self.KST)

        # Check if it's a holiday or weekend
        if self.is_holiday(check_time.date()):
            return False

        # Check if current time is within market hours
        current_time = check_time.time()
        return self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE

    def get_next_market_open(self, from_time: Optional[datetime] = None) -> datetime:
        """
        Get the next market opening time.

        Args:
            from_time: Start time to search from. If None, uses current time.

        Returns:
            Next market opening datetime
        """
        if from_time is None:
            from_time = datetime.now(self.KST)
        else:
            if from_time.tzinfo is None:
                from_time = self.KST.localize(from_time)
            else:
                from_time = from_time.astimezone(self.KST)

        # Start from the next day if we're past market close
        if from_time.time() > self.MARKET_CLOSE:
            check_date = from_time.date() + relativedelta(days=1)
        else:
            check_date = from_time.date()

        # Find next trading day
        while self.is_holiday(check_date):
            check_date += relativedelta(days=1)

        # Combine with market open time
        next_open = datetime.combine(check_date, self.MARKET_OPEN)
        return self.KST.localize(next_open)

    def get_market_close_today(self, ref_time: Optional[datetime] = None) -> datetime:
        """
        Get today's market closing time.

        Args:
            ref_time: Reference time. If None, uses current time.

        Returns:
            Today's market closing datetime
        """
        if ref_time is None:
            ref_time = datetime.now(self.KST)
        else:
            if ref_time.tzinfo is None:
                ref_time = self.KST.localize(ref_time)
            else:
                ref_time = ref_time.astimezone(self.KST)

        close_time = datetime.combine(ref_time.date(), self.MARKET_CLOSE)
        return self.KST.localize(close_time)

    def seconds_until_market_open(self) -> int:
        """
        Calculate seconds until next market open.

        Returns:
            Number of seconds until market opens
        """
        now = datetime.now(self.KST)
        next_open = self.get_next_market_open(now)
        return int((next_open - now).total_seconds())

    def seconds_until_market_close(self) -> Optional[int]:
        """
        Calculate seconds until market close today.

        Returns:
            Number of seconds until market closes, or None if market is closed
        """
        now = datetime.now(self.KST)

        if not self.is_market_open(now):
            return None

        close_time = self.get_market_close_today(now)
        return int((close_time - now).total_seconds())
