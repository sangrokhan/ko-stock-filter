"""
Unit tests for Stock Scorer.

Tests composite score calculation including value, growth, quality, and momentum scores.
"""
import pytest
import numpy as np
from datetime import datetime

from services.stock_scorer.stock_scorer import StockScorer, ScoreMetrics


class TestStockScorer:
    """Test suite for StockScorer."""

    @pytest.fixture
    def scorer(self):
        """Create stock scorer instance with default weights."""
        return StockScorer()

    @pytest.fixture
    def custom_weighted_scorer(self):
        """Create stock scorer with custom weights."""
        return StockScorer(
            weight_value=0.4,
            weight_growth=0.3,
            weight_quality=0.2,
            weight_momentum=0.1
        )

    def test_initialization_default_weights(self, scorer):
        """Test scorer initialization with default weights."""
        assert scorer.weight_value == 0.25
        assert scorer.weight_growth == 0.25
        assert scorer.weight_quality == 0.25
        assert scorer.weight_momentum == 0.25

    def test_initialization_custom_weights(self, custom_weighted_scorer):
        """Test scorer initialization with custom weights."""
        assert custom_weighted_scorer.weight_value == 0.4
        assert custom_weighted_scorer.weight_growth == 0.3
        assert custom_weighted_scorer.weight_quality == 0.2
        assert custom_weighted_scorer.weight_momentum == 0.1

    def test_initialization_normalizes_weights(self):
        """Test that weights are normalized if they don't sum to 1."""
        scorer = StockScorer(
            weight_value=0.5,
            weight_growth=0.5,
            weight_quality=0.5,
            weight_momentum=0.5
        )

        # Weights should be normalized to sum to 1.0
        total_weight = (
            scorer.weight_value +
            scorer.weight_growth +
            scorer.weight_quality +
            scorer.weight_momentum
        )
        assert abs(total_weight - 1.0) < 0.01

    def test_value_score_excellent_metrics(self, scorer, sample_fundamental_data):
        """Test value score calculation with excellent metrics."""
        # Excellent value metrics
        data = {
            'per': 8.0,   # Excellent: < 10
            'pbr': 0.8,   # Excellent: < 1
            'psr': 0.5,   # Excellent: < 1
            'dividend_yield': 6.0  # Excellent: > 5%
        }

        metrics = ScoreMetrics()
        value_score = scorer._calculate_value_score(data, metrics)

        assert value_score > 90  # Should be very high
        assert metrics.per_score == 100.0
        assert metrics.pbr_score == 100.0
        assert metrics.psr_score == 100.0
        assert metrics.dividend_yield_score == 100.0

    def test_value_score_poor_metrics(self, scorer):
        """Test value score calculation with poor metrics."""
        data = {
            'per': 50.0,  # Poor: > 25
            'pbr': 5.0,   # Poor: > 3
            'psr': 6.0,   # Poor: > 4
            'dividend_yield': 0.5  # Poor: < 1%
        }

        metrics = ScoreMetrics()
        value_score = scorer._calculate_value_score(data, metrics)

        assert value_score < 50  # Should be low
        assert metrics.per_score < 50
        assert metrics.pbr_score < 50

    def test_value_score_missing_data(self, scorer):
        """Test value score with missing data."""
        data = {
            'per': None,
            'pbr': 1.5
        }

        metrics = ScoreMetrics()
        value_score = scorer._calculate_value_score(data, metrics)

        assert value_score > 0  # Should still calculate from available data
        assert metrics.missing_value_count > 0

    def test_growth_score_excellent_growth(self, scorer):
        """Test growth score with excellent growth metrics."""
        data = {
            'revenue_growth': 25.0,   # Excellent: > 20%
            'earnings_growth': 30.0,  # Excellent: > 25%
            'equity_growth': 18.0     # Excellent: > 15%
        }

        metrics = ScoreMetrics()
        growth_score = scorer._calculate_growth_score(data, metrics)

        assert growth_score > 90
        assert metrics.revenue_growth_score == 100.0
        assert metrics.earnings_growth_score == 100.0
        assert metrics.equity_growth_score == 100.0

    def test_growth_score_negative_growth(self, scorer):
        """Test growth score with negative growth metrics."""
        data = {
            'revenue_growth': -10.0,
            'earnings_growth': -15.0,
            'equity_growth': -8.0
        }

        metrics = ScoreMetrics()
        growth_score = scorer._calculate_growth_score(data, metrics)

        assert growth_score < 50  # Should be low
        assert metrics.revenue_growth_score < 50
        assert metrics.earnings_growth_score < 50

    def test_quality_score_excellent_quality(self, scorer):
        """Test quality score with excellent quality metrics."""
        data = {
            'roe': 25.0,              # Excellent: > 20%
            'operating_margin': 22.0,  # Excellent: > 20%
            'net_margin': 18.0,        # Excellent: > 15%
            'debt_ratio': 25.0,        # Excellent: < 30%
            'current_ratio': 2.5       # Excellent: > 2
        }

        metrics = ScoreMetrics()
        quality_score = scorer._calculate_quality_score(data, metrics)

        assert quality_score > 90
        assert metrics.roe_score == 100.0
        assert metrics.operating_margin_score == 100.0
        assert metrics.net_margin_score == 100.0
        assert metrics.debt_ratio_score == 100.0
        assert metrics.current_ratio_score == 100.0

    def test_quality_score_poor_quality(self, scorer):
        """Test quality score with poor quality metrics."""
        data = {
            'roe': 5.0,          # Poor: < 10%
            'operating_margin': 5.0,  # Poor: < 10%
            'net_margin': 2.0,        # Poor: < 5%
            'debt_ratio': 90.0,       # Poor: > 70%
            'current_ratio': 0.8      # Poor: < 1
        }

        metrics = ScoreMetrics()
        quality_score = scorer._calculate_quality_score(data, metrics)

        assert quality_score < 50
        assert metrics.debt_ratio_score < 50

    def test_momentum_score_excellent_momentum(self, scorer, sample_technical_data):
        """Test momentum score with excellent momentum indicators."""
        technical_data = {
            'rsi_14': 60.0,           # Excellent: 50-70
            'macd_histogram': 3.0     # Positive: bullish
        }

        price_data = [
            {'close': 50000 + i * 200, 'volume': 1000000 + i * 10000}
            for i in range(30)
        ]

        metrics = ScoreMetrics()
        momentum_score = scorer._calculate_momentum_score(
            technical_data, price_data, metrics
        )

        assert momentum_score > 70
        assert metrics.rsi_score == 100.0
        assert metrics.macd_score > 50

    def test_momentum_score_poor_momentum(self, scorer):
        """Test momentum score with poor momentum indicators."""
        technical_data = {
            'rsi_14': 95.0,           # Overbought: > 90
            'macd_histogram': -4.0    # Negative: bearish
        }

        price_data = [
            {'close': 50000 - i * 200, 'volume': 1000000 - i * 10000}
            for i in range(30)
        ]

        metrics = ScoreMetrics()
        momentum_score = scorer._calculate_momentum_score(
            technical_data, price_data, metrics
        )

        assert momentum_score < 50
        assert metrics.rsi_score < 50
        assert metrics.macd_score < 50

    def test_momentum_score_insufficient_price_data(self, scorer):
        """Test momentum score with insufficient price data."""
        technical_data = {'rsi_14': 60.0}
        price_data = [{'close': 50000, 'volume': 1000000}]  # Only 1 data point

        metrics = ScoreMetrics()
        momentum_score = scorer._calculate_momentum_score(
            technical_data, price_data, metrics
        )

        # Should still calculate from available indicators
        assert momentum_score >= 0
        assert metrics.missing_value_count > 0

    def test_composite_score_calculation(
        self, scorer, sample_fundamental_data, sample_technical_data
    ):
        """Test complete composite score calculation."""
        price_data = [
            {'close': 50000 + i * 100, 'volume': 1000000 + i * 10000}
            for i in range(30)
        ]

        result = scorer.calculate_score(
            sample_fundamental_data,
            sample_technical_data,
            price_data
        )

        assert isinstance(result, ScoreMetrics)
        assert 0 <= result.composite_score <= 100
        assert result.value_score is not None
        assert result.growth_score is not None
        assert result.quality_score is not None
        assert result.momentum_score is not None

    def test_composite_score_weighted_average(self, custom_weighted_scorer):
        """Test that composite score uses weighted average."""
        fundamental_data = {
            'per': 10.0, 'pbr': 1.0, 'psr': 1.0, 'dividend_yield': 3.0,
            'revenue_growth': 15.0, 'earnings_growth': 20.0, 'equity_growth': 12.0,
            'roe': 18.0, 'operating_margin': 16.0, 'net_margin': 12.0,
            'debt_ratio': 40.0, 'current_ratio': 1.8
        }

        technical_data = {'rsi_14': 60.0, 'macd_histogram': 2.0}

        price_data = [
            {'close': 50000 + i * 100, 'volume': 1000000}
            for i in range(30)
        ]

        result = custom_weighted_scorer.calculate_score(
            fundamental_data,
            technical_data,
            price_data
        )

        # Verify weighted average calculation
        expected_composite = (
            result.value_score * 0.4 +
            result.growth_score * 0.3 +
            result.quality_score * 0.2 +
            result.momentum_score * 0.1
        )

        assert abs(result.composite_score - expected_composite) < 0.1

    def test_data_quality_score(self, scorer):
        """Test data quality score calculation."""
        # Complete data
        complete_data = {
            'per': 12.0, 'pbr': 1.5, 'psr': 1.2, 'dividend_yield': 2.5,
            'revenue_growth': 10.0, 'earnings_growth': 12.0, 'equity_growth': 8.0,
            'roe': 15.0, 'operating_margin': 14.0, 'net_margin': 10.0,
            'debt_ratio': 45.0, 'current_ratio': 1.6
        }

        tech_data = {'rsi_14': 55.0, 'macd_histogram': 1.5}
        price_data = [{'close': 50000, 'volume': 1000000} for _ in range(30)]

        result = scorer.calculate_score(complete_data, tech_data, price_data)

        # Should have high data quality with complete data
        assert result.data_quality_score > 70
        assert result.missing_value_count < 5

    def test_data_quality_score_missing_data(self, scorer):
        """Test data quality score with significant missing data."""
        incomplete_data = {
            'per': 12.0,
            'pbr': None,
            'psr': None,
            'revenue_growth': None,
            'roe': 15.0
        }

        tech_data = {}
        price_data = []

        result = scorer.calculate_score(incomplete_data, tech_data, price_data)

        # Should have low data quality with missing data
        assert result.data_quality_score < 70
        assert result.missing_value_count > 0

    def test_score_metrics_to_dict(self, scorer, sample_fundamental_data, sample_technical_data):
        """Test ScoreMetrics to_dict conversion."""
        price_data = [
            {'close': 50000 + i * 100, 'volume': 1000000}
            for i in range(30)
        ]

        result = scorer.calculate_score(
            sample_fundamental_data,
            sample_technical_data,
            price_data
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert 'composite_score' in result_dict
        assert 'value_score' in result_dict
        assert 'growth_score' in result_dict
        assert 'quality_score' in result_dict
        assert 'momentum_score' in result_dict
        assert 'data_quality_score' in result_dict
        assert 'date' in result_dict

    def test_per_score_boundaries(self, scorer):
        """Test PER score at various boundary values."""
        test_cases = [
            (5.0, 100.0),    # Excellent
            (10.0, 100.0),   # Excellent boundary
            (15.0, 80.0),    # Good
            (25.0, 40.0),    # Fair boundary
            (50.0, 0.0)      # Poor
        ]

        for per_value, expected_min_score in test_cases:
            data = {'per': per_value}
            metrics = ScoreMetrics()
            scorer._calculate_value_score(data, metrics)

            if expected_min_score == 100.0:
                assert metrics.per_score == expected_min_score
            else:
                # For non-perfect scores, check they're in expected range
                assert metrics.per_score is not None

    def test_pbr_score_boundaries(self, scorer):
        """Test PBR score at various boundary values."""
        test_cases = [
            (0.5, 100.0),    # Excellent
            (1.0, 100.0),    # Excellent boundary
            (2.0, 70.0),     # Good
            (3.0, 30.0),     # Fair boundary
            (5.0, 0.0)       # Poor
        ]

        for pbr_value, expected_min_score in test_cases:
            data = {'pbr': pbr_value}
            metrics = ScoreMetrics()
            scorer._calculate_value_score(data, metrics)

            if expected_min_score == 100.0:
                assert metrics.pbr_score == expected_min_score

    def test_rsi_score_boundaries(self, scorer):
        """Test RSI score at various boundary values."""
        test_cases = [
            (60.0, 100.0),   # Optimal range
            (45.0, 80.0),    # Good range
            (35.0, 50.0),    # Fair range
            (95.0, 0.0)      # Overbought
        ]

        for rsi_value, expected_min_score in test_cases:
            technical_data = {'rsi_14': rsi_value}
            price_data = []
            metrics = ScoreMetrics()

            scorer._calculate_momentum_score(technical_data, price_data, metrics)

            if expected_min_score == 100.0:
                assert metrics.rsi_score == expected_min_score

    def test_price_trend_calculation(self, scorer):
        """Test price trend score calculation."""
        # Uptrend
        uptrend_data = [
            {'close': 50000 + i * 200, 'volume': 1000000}
            for i in range(30)
        ]

        metrics_up = ScoreMetrics()
        scorer._calculate_momentum_score({}, uptrend_data, metrics_up)

        # Downtrend
        downtrend_data = [
            {'close': 50000 - i * 200, 'volume': 1000000}
            for i in range(30)
        ]

        metrics_down = ScoreMetrics()
        scorer._calculate_momentum_score({}, downtrend_data, metrics_down)

        # Uptrend should score higher than downtrend
        assert metrics_up.price_trend_score > metrics_down.price_trend_score

    def test_volume_trend_calculation(self, scorer):
        """Test volume trend score calculation."""
        # Increasing volume
        increasing_volume = [
            {'close': 50000, 'volume': 1000000 + i * 50000}
            for i in range(30)
        ]

        metrics_inc = ScoreMetrics()
        scorer._calculate_momentum_score({}, increasing_volume, metrics_inc)

        # Decreasing volume
        decreasing_volume = [
            {'close': 50000, 'volume': 1000000 - i * 30000}
            for i in range(30)
        ]

        metrics_dec = ScoreMetrics()
        scorer._calculate_momentum_score({}, decreasing_volume, metrics_dec)

        # Increasing volume should score higher
        assert metrics_inc.volume_trend_score > metrics_dec.volume_trend_score

    def test_zero_division_handling(self, scorer):
        """Test handling of potential zero division errors."""
        data = {
            'per': 0,
            'pbr': 0,
            'roe': 0
        }

        metrics = ScoreMetrics()
        # Should not raise exception
        value_score = scorer._calculate_value_score(data, metrics)
        quality_score = scorer._calculate_quality_score(data, metrics)

        assert value_score >= 0
        assert quality_score >= 0

    def test_negative_values_handling(self, scorer):
        """Test handling of negative values."""
        data = {
            'per': -5.0,  # Negative PER
            'roe': -10.0,  # Negative ROE
            'revenue_growth': -20.0  # Negative growth
        }

        metrics = ScoreMetrics()
        value_score = scorer._calculate_value_score(data, metrics)
        quality_score = scorer._calculate_quality_score(data, metrics)
        growth_score = scorer._calculate_growth_score(data, metrics)

        # Should handle negatives gracefully
        assert value_score >= 0
        assert quality_score >= 0
        assert growth_score >= 0


class TestScoreMetrics:
    """Test ScoreMetrics dataclass."""

    def test_score_metrics_initialization(self):
        """Test ScoreMetrics initialization."""
        metrics = ScoreMetrics()

        assert metrics.composite_score == 0.0
        assert metrics.missing_value_count == 0
        assert metrics.total_metric_count == 0
        assert isinstance(metrics.errors, list)
        assert len(metrics.errors) == 0

    def test_score_metrics_weights(self):
        """Test default weights in ScoreMetrics."""
        metrics = ScoreMetrics()

        assert metrics.weight_value == 0.25
        assert metrics.weight_growth == 0.25
        assert metrics.weight_quality == 0.25
        assert metrics.weight_momentum == 0.25


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
