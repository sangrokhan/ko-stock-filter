"""
Tests for Financial Indicator Calculator.
"""
import pytest
from services.indicator_calculator.financial_calculator import (
    FinancialCalculator,
    FinancialIndicator
)


class TestFinancialCalculator:
    """Test suite for FinancialCalculator."""

    def setup_method(self):
        """Setup test fixtures."""
        self.calculator = FinancialCalculator()

    def test_calculate_per_success(self):
        """Test PER calculation with valid data."""
        per = self.calculator.calculate_per(current_price=50000, eps=5000)
        assert per == 10.0

    def test_calculate_per_with_negative_eps(self):
        """Test PER calculation with negative EPS."""
        per = self.calculator.calculate_per(current_price=50000, eps=-5000)
        assert per is None

    def test_calculate_per_with_zero_eps(self):
        """Test PER calculation with zero EPS."""
        per = self.calculator.calculate_per(current_price=50000, eps=0)
        assert per is None

    def test_calculate_per_with_missing_data(self):
        """Test PER calculation with missing data."""
        per = self.calculator.calculate_per(current_price=None, eps=5000)
        assert per is None

    def test_calculate_pbr_success(self):
        """Test PBR calculation with valid data."""
        pbr = self.calculator.calculate_pbr(current_price=50000, bps=25000)
        assert pbr == 2.0

    def test_calculate_pbr_with_zero_bps(self):
        """Test PBR calculation with zero BPS."""
        pbr = self.calculator.calculate_pbr(current_price=50000, bps=0)
        assert pbr is None

    def test_calculate_pbr_with_missing_data(self):
        """Test PBR calculation with missing data."""
        pbr = self.calculator.calculate_pbr(current_price=50000, bps=None)
        assert pbr is None

    def test_calculate_roe_success(self):
        """Test ROE calculation with valid data."""
        roe = self.calculator.calculate_roe(net_income=1000, total_equity=10000)
        assert roe == 10.0

    def test_calculate_roe_with_negative_income(self):
        """Test ROE calculation with negative net income."""
        roe = self.calculator.calculate_roe(net_income=-1000, total_equity=10000)
        assert roe == -10.0

    def test_calculate_roe_with_zero_equity(self):
        """Test ROE calculation with zero equity."""
        roe = self.calculator.calculate_roe(net_income=1000, total_equity=0)
        assert roe is None

    def test_calculate_roe_with_missing_data(self):
        """Test ROE calculation with missing data."""
        roe = self.calculator.calculate_roe(net_income=None, total_equity=10000)
        assert roe is None

    def test_calculate_debt_ratio_success(self):
        """Test Debt Ratio calculation with valid data."""
        debt_ratio = self.calculator.calculate_debt_ratio(
            total_debt=3000,
            total_assets=10000
        )
        assert debt_ratio == 30.0

    def test_calculate_debt_ratio_with_zero_assets(self):
        """Test Debt Ratio calculation with zero assets."""
        debt_ratio = self.calculator.calculate_debt_ratio(
            total_debt=3000,
            total_assets=0
        )
        assert debt_ratio is None

    def test_calculate_debt_ratio_with_missing_data(self):
        """Test Debt Ratio calculation with missing data."""
        debt_ratio = self.calculator.calculate_debt_ratio(
            total_debt=None,
            total_assets=10000
        )
        assert debt_ratio is None

    def test_calculate_operating_margin_success(self):
        """Test Operating Margin calculation with valid data."""
        operating_margin = self.calculator.calculate_operating_margin(
            operating_profit=1500,
            revenue=10000
        )
        assert operating_margin == 15.0

    def test_calculate_operating_margin_with_negative_profit(self):
        """Test Operating Margin calculation with negative operating profit."""
        operating_margin = self.calculator.calculate_operating_margin(
            operating_profit=-1500,
            revenue=10000
        )
        assert operating_margin == -15.0

    def test_calculate_operating_margin_with_zero_revenue(self):
        """Test Operating Margin calculation with zero revenue."""
        operating_margin = self.calculator.calculate_operating_margin(
            operating_profit=1500,
            revenue=0
        )
        assert operating_margin is None

    def test_calculate_operating_margin_with_missing_data(self):
        """Test Operating Margin calculation with missing data."""
        operating_margin = self.calculator.calculate_operating_margin(
            operating_profit=1500,
            revenue=None
        )
        assert operating_margin is None

    def test_calculate_eps_growth_success(self):
        """Test EPS Growth calculation with valid data."""
        eps_growth = self.calculator.calculate_eps_growth(
            current_eps=5500,
            previous_eps=5000
        )
        assert eps_growth == 10.0

    def test_calculate_eps_growth_negative(self):
        """Test EPS Growth calculation with negative growth."""
        eps_growth = self.calculator.calculate_eps_growth(
            current_eps=4500,
            previous_eps=5000
        )
        assert eps_growth == -10.0

    def test_calculate_eps_growth_with_zero_previous(self):
        """Test EPS Growth calculation with zero previous EPS."""
        eps_growth = self.calculator.calculate_eps_growth(
            current_eps=5000,
            previous_eps=0
        )
        assert eps_growth is None

    def test_calculate_eps_growth_with_missing_data(self):
        """Test EPS Growth calculation with missing data."""
        eps_growth = self.calculator.calculate_eps_growth(
            current_eps=None,
            previous_eps=5000
        )
        assert eps_growth is None

    def test_calculate_revenue_growth_success(self):
        """Test Revenue Growth calculation with valid data."""
        revenue_growth = self.calculator.calculate_revenue_growth(
            current_revenue=11000,
            previous_revenue=10000
        )
        assert revenue_growth == 10.0

    def test_calculate_revenue_growth_negative(self):
        """Test Revenue Growth calculation with negative growth."""
        revenue_growth = self.calculator.calculate_revenue_growth(
            current_revenue=9000,
            previous_revenue=10000
        )
        assert revenue_growth == -10.0

    def test_calculate_revenue_growth_with_zero_previous(self):
        """Test Revenue Growth calculation with zero previous revenue."""
        revenue_growth = self.calculator.calculate_revenue_growth(
            current_revenue=10000,
            previous_revenue=0
        )
        assert revenue_growth is None

    def test_calculate_revenue_growth_with_missing_data(self):
        """Test Revenue Growth calculation with missing data."""
        revenue_growth = self.calculator.calculate_revenue_growth(
            current_revenue=10000,
            previous_revenue=None
        )
        assert revenue_growth is None

    def test_calculate_eps_success(self):
        """Test EPS calculation with valid data."""
        eps = self.calculator.calculate_eps(
            net_income=1000,  # 1000 million KRW
            shares_outstanding=100000  # 100,000 shares
        )
        # (1000 * 1,000,000) / 100,000 = 10,000 KRW per share
        assert eps == 10000.0

    def test_calculate_eps_with_zero_shares(self):
        """Test EPS calculation with zero shares."""
        eps = self.calculator.calculate_eps(
            net_income=1000,
            shares_outstanding=0
        )
        assert eps is None

    def test_calculate_eps_with_missing_data(self):
        """Test EPS calculation with missing data."""
        eps = self.calculator.calculate_eps(
            net_income=None,
            shares_outstanding=100000
        )
        assert eps is None

    def test_calculate_bps_success(self):
        """Test BPS calculation with valid data."""
        bps = self.calculator.calculate_bps(
            total_equity=5000,  # 5000 million KRW
            shares_outstanding=100000  # 100,000 shares
        )
        # (5000 * 1,000,000) / 100,000 = 50,000 KRW per share
        assert bps == 50000.0

    def test_calculate_bps_with_zero_shares(self):
        """Test BPS calculation with zero shares."""
        bps = self.calculator.calculate_bps(
            total_equity=5000,
            shares_outstanding=0
        )
        assert bps is None

    def test_calculate_bps_with_missing_data(self):
        """Test BPS calculation with missing data."""
        bps = self.calculator.calculate_bps(
            total_equity=5000,
            shares_outstanding=None
        )
        assert bps is None

    def test_calculate_all_indicators_without_previous_data(self):
        """Test calculating all indicators without previous period data."""
        current_data = {
            'current_price': 50000,
            'net_income': 1000,
            'total_equity': 10000,
            'total_debt': 3000,
            'total_assets': 15000,
            'operating_profit': 1500,
            'revenue': 10000,
            'shares_outstanding': 100000
        }

        indicators = self.calculator.calculate_all_indicators(current_data)

        # Check that basic indicators are calculated
        assert indicators.eps is not None
        assert indicators.bps is not None
        assert indicators.per is not None
        assert indicators.pbr is not None
        assert indicators.roe is not None
        assert indicators.debt_ratio is not None
        assert indicators.operating_margin is not None

        # Growth metrics should be None without previous data
        assert indicators.revenue_growth is None
        assert indicators.eps_growth is None

    def test_calculate_all_indicators_with_previous_data(self):
        """Test calculating all indicators with previous period data."""
        current_data = {
            'current_price': 50000,
            'net_income': 1000,
            'total_equity': 10000,
            'total_debt': 3000,
            'total_assets': 15000,
            'operating_profit': 1500,
            'revenue': 11000,
            'shares_outstanding': 100000
        }

        previous_data = {
            'revenue': 10000,
            'eps': 9000
        }

        indicators = self.calculator.calculate_all_indicators(
            current_data,
            previous_data
        )

        # Check that all indicators are calculated
        assert indicators.eps is not None
        assert indicators.bps is not None
        assert indicators.per is not None
        assert indicators.pbr is not None
        assert indicators.roe is not None
        assert indicators.debt_ratio is not None
        assert indicators.operating_margin is not None
        assert indicators.revenue_growth is not None
        assert indicators.eps_growth is not None

    def test_calculate_all_indicators_with_missing_data(self):
        """Test calculating all indicators with some missing data."""
        current_data = {
            'current_price': 50000,
            'net_income': None,  # Missing
            'total_equity': 10000,
            'total_debt': 3000,
            'total_assets': 15000,
            'operating_profit': 1500,
            'revenue': 10000,
            'shares_outstanding': 100000
        }

        indicators = self.calculator.calculate_all_indicators(current_data)

        # Some indicators should be None due to missing data
        assert indicators.eps is None  # Requires net_income
        assert indicators.roe is None  # Requires net_income
        assert indicators.per is None  # Requires EPS

        # Others should still be calculated
        assert indicators.bps is not None
        assert indicators.debt_ratio is not None
        assert indicators.operating_margin is not None

    def test_financial_indicator_to_dict(self):
        """Test FinancialIndicator to_dict conversion."""
        indicator = FinancialIndicator()
        indicator.per = 10.5
        indicator.pbr = 2.3
        indicator.roe = 15.2

        result = indicator.to_dict()

        assert result['per'] == 10.5
        assert result['pbr'] == 2.3
        assert result['roe'] == 15.2
        assert result['earnings_growth'] == indicator.eps_growth
        assert 'date' in result
