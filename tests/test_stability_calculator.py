"""
Tests for Stability Calculator.
"""
import pytest
import numpy as np
from datetime import datetime, timedelta

from services.stability_calculator.stability_calculator import (
    StabilityCalculator,
    StabilityMetrics
)


class TestStabilityCalculator:
    """Test cases for StabilityCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create a calculator instance."""
        return StabilityCalculator(
            lookback_days=252,
            min_price_points=30,
            min_earnings_points=4
        )

    def test_calculate_price_volatility_stable_stock(self, calculator):
        """Test price volatility calculation for a stable stock."""
        # Generate stable prices (low volatility)
        np.random.seed(42)
        base_price = 100
        prices = [base_price + np.random.normal(0, 0.5) for _ in range(100)]

        volatility, score = calculator.calculate_price_volatility(prices)

        assert volatility is not None
        assert score is not None
        assert 0 <= score <= 100
        assert score > 50  # Stable stock should have high score

    def test_calculate_price_volatility_volatile_stock(self, calculator):
        """Test price volatility calculation for a volatile stock."""
        # Generate volatile prices (high volatility)
        np.random.seed(42)
        base_price = 100
        prices = [base_price + np.random.normal(0, 10) for _ in range(100)]

        volatility, score = calculator.calculate_price_volatility(prices)

        assert volatility is not None
        assert score is not None
        assert 0 <= score <= 100
        assert score < 50  # Volatile stock should have low score

    def test_calculate_price_volatility_insufficient_data(self, calculator):
        """Test price volatility with insufficient data."""
        prices = [100.0]

        volatility, score = calculator.calculate_price_volatility(prices)

        assert volatility is None
        assert score is None

    def test_calculate_beta_market_like(self, calculator):
        """Test beta calculation for a market-like stock."""
        # Generate prices that move with the market (beta ~ 1.0)
        np.random.seed(42)
        market_prices = [100 + i * 0.1 + np.random.normal(0, 0.5) for i in range(100)]
        stock_prices = [100 + i * 0.1 + np.random.normal(0, 0.5) for i in range(100)]

        beta, score, correlation = calculator.calculate_beta(stock_prices, market_prices)

        assert beta is not None
        assert score is not None
        assert correlation is not None
        assert 0.5 < beta < 1.5  # Should be close to 1.0
        assert score > 50  # Market-like behavior is stable

    def test_calculate_beta_defensive_stock(self, calculator):
        """Test beta calculation for a defensive stock."""
        # Generate prices that move less than the market (beta < 1.0)
        np.random.seed(42)
        market_returns = [np.random.normal(0, 2) for _ in range(100)]
        stock_returns = [r * 0.5 for r in market_returns]  # Half the market movement

        market_prices = [100]
        stock_prices = [100]

        for mr, sr in zip(market_returns, stock_returns):
            market_prices.append(market_prices[-1] * (1 + mr / 100))
            stock_prices.append(stock_prices[-1] * (1 + sr / 100))

        beta, score, correlation = calculator.calculate_beta(stock_prices, market_prices)

        assert beta is not None
        assert beta < 1.0  # Defensive stock

    def test_calculate_beta_insufficient_data(self, calculator):
        """Test beta calculation with insufficient data."""
        stock_prices = [100.0, 101.0]
        market_prices = [1000.0, 1010.0]

        beta, score, correlation = calculator.calculate_beta(stock_prices, market_prices)

        assert beta is None
        assert score is None
        assert correlation is None

    def test_calculate_volume_stability_stable(self, calculator):
        """Test volume stability for consistent volume."""
        # Generate stable volumes
        np.random.seed(42)
        volumes = [int(1000000 + np.random.normal(0, 50000)) for _ in range(100)]

        cv, score = calculator.calculate_volume_stability(volumes)

        assert cv is not None
        assert score is not None
        assert 0 <= score <= 100
        assert cv < 0.5  # Low coefficient of variation

    def test_calculate_volume_stability_volatile(self, calculator):
        """Test volume stability for erratic volume."""
        # Generate volatile volumes
        volumes = [1000000, 5000000, 500000, 3000000, 100000, 4000000]

        cv, score = calculator.calculate_volume_stability(volumes)

        assert cv is not None
        assert score is not None
        assert cv > 0.5  # High coefficient of variation

    def test_calculate_earnings_consistency_consistent(self, calculator):
        """Test earnings consistency for stable earnings."""
        # Consistent earnings with slight growth
        earnings = [100, 105, 110, 115, 120, 125, 130, 135]

        cv, score, trend = calculator.calculate_earnings_consistency(earnings)

        assert cv is not None
        assert score is not None
        assert trend is not None
        assert score > 50  # Consistent earnings should score high
        assert trend > 0  # Positive trend

    def test_calculate_earnings_consistency_erratic(self, calculator):
        """Test earnings consistency for erratic earnings."""
        # Erratic earnings
        earnings = [100, 50, 150, 70, 130, 60, 140, 80]

        cv, score, trend = calculator.calculate_earnings_consistency(earnings)

        assert cv is not None
        assert score is not None
        assert trend is not None
        assert score < 70  # Erratic earnings should score lower

    def test_calculate_earnings_consistency_insufficient_data(self, calculator):
        """Test earnings consistency with insufficient data."""
        earnings = [100, 105]

        cv, score, trend = calculator.calculate_earnings_consistency(earnings)

        assert cv is None
        assert score is None
        assert trend is None

    def test_calculate_debt_stability_improving(self, calculator):
        """Test debt stability for improving debt ratio."""
        # Decreasing debt ratio (improving)
        debt_ratios = [70, 65, 60, 55, 50, 45, 40, 35]

        score, trend = calculator.calculate_debt_stability(debt_ratios)

        assert score is not None
        assert trend is not None
        assert score > 50  # Improving debt is stable
        assert trend < 0  # Negative trend (decreasing debt)

    def test_calculate_debt_stability_worsening(self, calculator):
        """Test debt stability for worsening debt ratio."""
        # Increasing debt ratio (worsening)
        debt_ratios = [30, 35, 40, 45, 50, 55, 60, 65]

        score, trend = calculator.calculate_debt_stability(debt_ratios)

        assert score is not None
        assert trend is not None
        assert score < 70  # Worsening debt is less stable
        assert trend > 0  # Positive trend (increasing debt)

    def test_calculate_stability_score_complete_data(self, calculator):
        """Test overall stability score with complete data."""
        # Generate sample data
        np.random.seed(42)

        # Stable price data
        price_data = [
            {'close': 100 + i * 0.1 + np.random.normal(0, 0.5), 'volume': 1000000 + int(np.random.normal(0, 50000))}
            for i in range(100)
        ]

        # Market data
        market_data = [
            {'close': 1000 + i * 1.0 + np.random.normal(0, 5)}
            for i in range(100)
        ]

        # Earnings data
        earnings_data = [100, 105, 110, 115, 120, 125, 130, 135]

        # Debt data
        debt_data = [50, 48, 46, 44, 42, 40, 38, 36]

        metrics = calculator.calculate_stability_score(
            price_data=price_data,
            market_data=market_data,
            earnings_data=earnings_data,
            debt_data=debt_data
        )

        assert isinstance(metrics, StabilityMetrics)
        assert 0 <= metrics.stability_score <= 100
        assert metrics.price_volatility_score is not None
        assert metrics.beta_score is not None
        assert metrics.volume_stability_score is not None
        assert metrics.earnings_consistency_score is not None
        assert metrics.debt_stability_score is not None

    def test_calculate_stability_score_partial_data(self, calculator):
        """Test overall stability score with partial data."""
        # Generate sample data with only price data
        np.random.seed(42)

        price_data = [
            {'close': 100 + i * 0.1, 'volume': 1000000}
            for i in range(100)
        ]

        metrics = calculator.calculate_stability_score(
            price_data=price_data,
            market_data=[],
            earnings_data=[],
            debt_data=[]
        )

        assert isinstance(metrics, StabilityMetrics)
        assert 0 <= metrics.stability_score <= 100
        # Only price and volume components should be calculated
        assert metrics.price_volatility_score is not None
        assert metrics.volume_stability_score is not None
        # Other components should be None
        assert metrics.beta_score is None
        assert metrics.earnings_consistency_score is None
        assert metrics.debt_stability_score is None

    def test_calculate_stability_score_custom_weights(self, calculator):
        """Test stability score with custom weights."""
        np.random.seed(42)

        price_data = [
            {'close': 100 + i * 0.1, 'volume': 1000000}
            for i in range(100)
        ]

        custom_weights = {
            'price': 0.5,  # Emphasize price volatility
            'beta': 0.1,
            'volume': 0.1,
            'earnings': 0.2,
            'debt': 0.1
        }

        metrics = calculator.calculate_stability_score(
            price_data=price_data,
            market_data=[],
            earnings_data=[],
            debt_data=[],
            weights=custom_weights
        )

        assert metrics.weight_price == 0.5
        assert 0 <= metrics.stability_score <= 100

    def test_stability_metrics_to_dict(self):
        """Test StabilityMetrics to_dict conversion."""
        metrics = StabilityMetrics()
        metrics.stability_score = 75.5
        metrics.price_volatility_score = 80.0
        metrics.beta = 1.1

        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result['stability_score'] == 75.5
        assert result['price_volatility_score'] == 80.0
        assert result['beta'] == 1.1
        assert 'date' in result

    def test_edge_case_zero_prices(self, calculator):
        """Test handling of zero prices."""
        prices = [100, 0, 100, 0]

        volatility, score = calculator.calculate_price_volatility(prices)

        # Should handle gracefully
        assert volatility is None or isinstance(volatility, float)

    def test_edge_case_negative_earnings(self, calculator):
        """Test handling of negative earnings."""
        earnings = [100, -50, 120, -30, 150]

        cv, score, trend = calculator.calculate_earnings_consistency(earnings)

        # Should handle negative values
        assert cv is None or isinstance(cv, float)

    def test_edge_case_all_same_values(self, calculator):
        """Test handling of constant values."""
        prices = [100.0] * 50

        volatility, score = calculator.calculate_price_volatility(prices)

        assert volatility is not None
        assert volatility == 0.0  # No volatility
        assert score == 100.0  # Perfect stability
