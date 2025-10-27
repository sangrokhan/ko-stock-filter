"""
Financial Indicator Calculator.

Calculates fundamental financial indicators including:
- PER (Price to Earnings Ratio)
- PBR (Price to Book Ratio)
- ROE (Return on Equity)
- Debt Ratio
- Operating Margin
- EPS growth rate
- Revenue growth rate
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class FinancialIndicator:
    """Container for calculated financial indicators."""

    def __init__(self):
        self.per: Optional[float] = None
        self.pbr: Optional[float] = None
        self.roe: Optional[float] = None
        self.debt_ratio: Optional[float] = None
        self.operating_margin: Optional[float] = None
        self.eps_growth: Optional[float] = None
        self.revenue_growth: Optional[float] = None
        self.eps: Optional[float] = None
        self.bps: Optional[float] = None
        self.calculation_date: datetime = datetime.utcnow()
        self.errors: list = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'per': self.per,
            'pbr': self.pbr,
            'roe': self.roe,
            'debt_ratio': self.debt_ratio,
            'operating_margin': self.operating_margin,
            'earnings_growth': self.eps_growth,  # Map to earnings_growth in DB
            'revenue_growth': self.revenue_growth,
            'eps': self.eps,
            'bps': self.bps,
            'date': self.calculation_date,
        }


class FinancialCalculator:
    """Calculator for financial indicators."""

    def __init__(self):
        """Initialize the financial calculator."""
        self.logger = logging.getLogger(__name__)

    def calculate_per(
        self,
        current_price: Optional[float],
        eps: Optional[float]
    ) -> Optional[float]:
        """
        Calculate Price to Earnings Ratio (PER).

        PER = Current Price / Earnings Per Share

        Args:
            current_price: Current stock price
            eps: Earnings per share

        Returns:
            PER value or None if calculation not possible
        """
        try:
            if current_price is None or eps is None:
                self.logger.debug("Missing data for PER calculation")
                return None

            if eps <= 0:
                self.logger.debug("EPS is zero or negative, cannot calculate PER")
                return None

            per = current_price / eps
            return round(per, 2)
        except (ZeroDivisionError, TypeError, ValueError) as e:
            self.logger.warning(f"Error calculating PER: {e}")
            return None

    def calculate_pbr(
        self,
        current_price: Optional[float],
        bps: Optional[float]
    ) -> Optional[float]:
        """
        Calculate Price to Book Ratio (PBR).

        PBR = Current Price / Book Value Per Share

        Args:
            current_price: Current stock price
            bps: Book value per share

        Returns:
            PBR value or None if calculation not possible
        """
        try:
            if current_price is None or bps is None:
                self.logger.debug("Missing data for PBR calculation")
                return None

            if bps <= 0:
                self.logger.debug("BPS is zero or negative, cannot calculate PBR")
                return None

            pbr = current_price / bps
            return round(pbr, 2)
        except (ZeroDivisionError, TypeError, ValueError) as e:
            self.logger.warning(f"Error calculating PBR: {e}")
            return None

    def calculate_roe(
        self,
        net_income: Optional[float],
        total_equity: Optional[float]
    ) -> Optional[float]:
        """
        Calculate Return on Equity (ROE).

        ROE = (Net Income / Total Equity) * 100

        Args:
            net_income: Net income in KRW millions
            total_equity: Total equity in KRW millions

        Returns:
            ROE percentage or None if calculation not possible
        """
        try:
            if net_income is None or total_equity is None:
                self.logger.debug("Missing data for ROE calculation")
                return None

            if total_equity <= 0:
                self.logger.debug("Total equity is zero or negative, cannot calculate ROE")
                return None

            roe = (net_income / total_equity) * 100
            return round(roe, 2)
        except (ZeroDivisionError, TypeError, ValueError) as e:
            self.logger.warning(f"Error calculating ROE: {e}")
            return None

    def calculate_debt_ratio(
        self,
        total_debt: Optional[float],
        total_assets: Optional[float]
    ) -> Optional[float]:
        """
        Calculate Debt Ratio.

        Debt Ratio = (Total Debt / Total Assets) * 100

        Args:
            total_debt: Total debt in KRW millions
            total_assets: Total assets in KRW millions

        Returns:
            Debt ratio percentage or None if calculation not possible
        """
        try:
            if total_debt is None or total_assets is None:
                self.logger.debug("Missing data for Debt Ratio calculation")
                return None

            if total_assets <= 0:
                self.logger.debug("Total assets is zero or negative, cannot calculate Debt Ratio")
                return None

            debt_ratio = (total_debt / total_assets) * 100
            return round(debt_ratio, 2)
        except (ZeroDivisionError, TypeError, ValueError) as e:
            self.logger.warning(f"Error calculating Debt Ratio: {e}")
            return None

    def calculate_operating_margin(
        self,
        operating_profit: Optional[float],
        revenue: Optional[float]
    ) -> Optional[float]:
        """
        Calculate Operating Margin.

        Operating Margin = (Operating Profit / Revenue) * 100

        Args:
            operating_profit: Operating profit in KRW millions
            revenue: Total revenue in KRW millions

        Returns:
            Operating margin percentage or None if calculation not possible
        """
        try:
            if operating_profit is None or revenue is None:
                self.logger.debug("Missing data for Operating Margin calculation")
                return None

            if revenue <= 0:
                self.logger.debug("Revenue is zero or negative, cannot calculate Operating Margin")
                return None

            operating_margin = (operating_profit / revenue) * 100
            return round(operating_margin, 2)
        except (ZeroDivisionError, TypeError, ValueError) as e:
            self.logger.warning(f"Error calculating Operating Margin: {e}")
            return None

    def calculate_eps_growth(
        self,
        current_eps: Optional[float],
        previous_eps: Optional[float]
    ) -> Optional[float]:
        """
        Calculate EPS Growth Rate.

        EPS Growth = ((Current EPS - Previous EPS) / Previous EPS) * 100

        Args:
            current_eps: Current period earnings per share
            previous_eps: Previous period earnings per share

        Returns:
            EPS growth percentage or None if calculation not possible
        """
        try:
            if current_eps is None or previous_eps is None:
                self.logger.debug("Missing data for EPS Growth calculation")
                return None

            if previous_eps == 0:
                self.logger.debug("Previous EPS is zero, cannot calculate growth rate")
                return None

            eps_growth = ((current_eps - previous_eps) / abs(previous_eps)) * 100
            return round(eps_growth, 2)
        except (ZeroDivisionError, TypeError, ValueError) as e:
            self.logger.warning(f"Error calculating EPS Growth: {e}")
            return None

    def calculate_revenue_growth(
        self,
        current_revenue: Optional[float],
        previous_revenue: Optional[float]
    ) -> Optional[float]:
        """
        Calculate Revenue Growth Rate.

        Revenue Growth = ((Current Revenue - Previous Revenue) / Previous Revenue) * 100

        Args:
            current_revenue: Current period revenue in KRW millions
            previous_revenue: Previous period revenue in KRW millions

        Returns:
            Revenue growth percentage or None if calculation not possible
        """
        try:
            if current_revenue is None or previous_revenue is None:
                self.logger.debug("Missing data for Revenue Growth calculation")
                return None

            if previous_revenue <= 0:
                self.logger.debug("Previous revenue is zero or negative, cannot calculate growth rate")
                return None

            revenue_growth = ((current_revenue - previous_revenue) / previous_revenue) * 100
            return round(revenue_growth, 2)
        except (ZeroDivisionError, TypeError, ValueError) as e:
            self.logger.warning(f"Error calculating Revenue Growth: {e}")
            return None

    def calculate_eps(
        self,
        net_income: Optional[float],
        shares_outstanding: Optional[int]
    ) -> Optional[float]:
        """
        Calculate Earnings Per Share (EPS).

        EPS = Net Income / Shares Outstanding

        Args:
            net_income: Net income in KRW millions
            shares_outstanding: Number of shares outstanding

        Returns:
            EPS value or None if calculation not possible
        """
        try:
            if net_income is None or shares_outstanding is None:
                self.logger.debug("Missing data for EPS calculation")
                return None

            if shares_outstanding <= 0:
                self.logger.debug("Shares outstanding is zero or negative, cannot calculate EPS")
                return None

            # Convert net income from millions to actual KRW, then divide by shares
            eps = (net_income * 1_000_000) / shares_outstanding
            return round(eps, 2)
        except (ZeroDivisionError, TypeError, ValueError) as e:
            self.logger.warning(f"Error calculating EPS: {e}")
            return None

    def calculate_bps(
        self,
        total_equity: Optional[float],
        shares_outstanding: Optional[int]
    ) -> Optional[float]:
        """
        Calculate Book Value Per Share (BPS).

        BPS = Total Equity / Shares Outstanding

        Args:
            total_equity: Total equity in KRW millions
            shares_outstanding: Number of shares outstanding

        Returns:
            BPS value or None if calculation not possible
        """
        try:
            if total_equity is None or shares_outstanding is None:
                self.logger.debug("Missing data for BPS calculation")
                return None

            if shares_outstanding <= 0:
                self.logger.debug("Shares outstanding is zero or negative, cannot calculate BPS")
                return None

            # Convert equity from millions to actual KRW, then divide by shares
            bps = (total_equity * 1_000_000) / shares_outstanding
            return round(bps, 2)
        except (ZeroDivisionError, TypeError, ValueError) as e:
            self.logger.warning(f"Error calculating BPS: {e}")
            return None

    def calculate_all_indicators(
        self,
        current_data: Dict[str, Any],
        previous_data: Optional[Dict[str, Any]] = None
    ) -> FinancialIndicator:
        """
        Calculate all financial indicators for a stock.

        Args:
            current_data: Dictionary containing current financial data
                Required keys: current_price, net_income, total_equity, total_debt,
                total_assets, operating_profit, revenue, shares_outstanding
            previous_data: Dictionary containing previous period financial data
                Required keys: revenue, eps (for growth calculations)

        Returns:
            FinancialIndicator object with all calculated indicators
        """
        indicator = FinancialIndicator()

        # Extract current data with safe conversion
        current_price = self._to_float(current_data.get('current_price'))
        net_income = self._to_float(current_data.get('net_income'))
        total_equity = self._to_float(current_data.get('total_equity'))
        total_debt = self._to_float(current_data.get('total_debt'))
        total_assets = self._to_float(current_data.get('total_assets'))
        operating_profit = self._to_float(current_data.get('operating_profit'))
        revenue = self._to_float(current_data.get('revenue'))
        shares_outstanding = self._to_int(current_data.get('shares_outstanding'))

        # Calculate per-share metrics first
        indicator.eps = self.calculate_eps(net_income, shares_outstanding)
        indicator.bps = self.calculate_bps(total_equity, shares_outstanding)

        # Calculate valuation ratios
        indicator.per = self.calculate_per(current_price, indicator.eps)
        indicator.pbr = self.calculate_pbr(current_price, indicator.bps)

        # Calculate profitability ratios
        indicator.roe = self.calculate_roe(net_income, total_equity)
        indicator.operating_margin = self.calculate_operating_margin(operating_profit, revenue)

        # Calculate financial health ratios
        indicator.debt_ratio = self.calculate_debt_ratio(total_debt, total_assets)

        # Calculate growth metrics if previous data is available
        if previous_data:
            previous_revenue = self._to_float(previous_data.get('revenue'))
            previous_eps = self._to_float(previous_data.get('eps'))

            indicator.revenue_growth = self.calculate_revenue_growth(revenue, previous_revenue)
            indicator.eps_growth = self.calculate_eps_growth(indicator.eps, previous_eps)

        return indicator

    def _to_float(self, value: Any) -> Optional[float]:
        """
        Safely convert value to float.

        Args:
            value: Value to convert

        Returns:
            Float value or None
        """
        if value is None:
            return None
        try:
            if isinstance(value, Decimal):
                return float(value)
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value: Any) -> Optional[int]:
        """
        Safely convert value to int.

        Args:
            value: Value to convert

        Returns:
            Int value or None
        """
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
