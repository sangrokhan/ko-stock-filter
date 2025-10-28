"""
Unit tests for Technical Indicator Calculator.

Tests all technical indicator calculation methods including:
- Moving Averages (SMA, EMA)
- RSI (Relative Strength Index)
- MACD
- Bollinger Bands
- Volume indicators
- Volatility indicators (ATR)
- Momentum indicators (Stochastic)
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from services.indicator_calculator.technical_calculator import (
    TechnicalIndicatorCalculator,
    TechnicalIndicatorData
)


@pytest.fixture
def calculator():
    """Fixture providing a calculator instance."""
    return TechnicalIndicatorCalculator()


@pytest.fixture
def sample_price_data():
    """Fixture providing sample OHLCV price data."""
    # Generate 250 days of sample data
    dates = pd.date_range(end=datetime.now(), periods=250, freq='D')

    # Create realistic price data with trend
    base_price = 50000
    prices = []
    volume = []

    for i in range(250):
        # Add trend and random walk
        trend = i * 100
        noise = np.random.normal(0, 1000)
        price = base_price + trend + noise
        prices.append(price)
        volume.append(np.random.randint(1000000, 5000000))

    df = pd.DataFrame({
        'date': dates,
        'open': [p * 0.99 for p in prices],
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': volume,
    })

    df.set_index('date', inplace=True)
    return df


@pytest.fixture
def minimal_price_data():
    """Fixture providing minimal price data (20 days)."""
    dates = pd.date_range(end=datetime.now(), periods=20, freq='D')

    prices = [50000 + i * 100 + np.random.normal(0, 500) for i in range(20)]

    df = pd.DataFrame({
        'date': dates,
        'open': [p * 0.99 for p in prices],
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000000, 2000000) for _ in range(20)],
    })

    df.set_index('date', inplace=True)
    return df


class TestMovingAverages:
    """Tests for moving average calculations."""

    def test_calculate_sma_with_sufficient_data(self, calculator, sample_price_data):
        """Test SMA calculation with sufficient data."""
        result = calculator.calculate_moving_averages(sample_price_data)

        assert result is not None
        assert result['sma_5'] is not None
        assert result['sma_20'] is not None
        assert result['sma_50'] is not None
        assert result['sma_120'] is not None
        assert result['sma_200'] is not None

        # SMAs should be positive
        assert result['sma_5'] > 0
        assert result['sma_20'] > 0
        assert result['sma_200'] > 0

        # Longer period SMAs should smooth out more
        # (This is a general trend, not always true)
        assert isinstance(result['sma_5'], float)
        assert isinstance(result['sma_200'], float)

    def test_calculate_ema_with_sufficient_data(self, calculator, sample_price_data):
        """Test EMA calculation with sufficient data."""
        result = calculator.calculate_moving_averages(sample_price_data)

        assert result['ema_12'] is not None
        assert result['ema_26'] is not None
        assert result['ema_12'] > 0
        assert result['ema_26'] > 0

    def test_calculate_sma_with_minimal_data(self, calculator, minimal_price_data):
        """Test SMA calculation with minimal data."""
        result = calculator.calculate_moving_averages(minimal_price_data)

        # Should have short-term MAs
        assert result['sma_5'] is not None
        assert result['sma_20'] is not None

        # Should not have long-term MAs
        assert result['sma_50'] is None
        assert result['sma_120'] is None
        assert result['sma_200'] is None

    def test_calculate_ma_with_empty_dataframe(self, calculator):
        """Test MA calculation with empty DataFrame."""
        df = pd.DataFrame()
        result = calculator.calculate_moving_averages(df)

        assert result['sma_5'] is None
        assert result['sma_20'] is None
        assert result['ema_12'] is None

    def test_calculate_ma_with_missing_column(self, calculator, sample_price_data):
        """Test MA calculation with missing price column."""
        df = sample_price_data.drop('close', axis=1)
        result = calculator.calculate_moving_averages(df)

        assert result['sma_5'] is None
        assert result['sma_20'] is None


class TestRSI:
    """Tests for RSI calculations."""

    def test_calculate_rsi_with_sufficient_data(self, calculator, sample_price_data):
        """Test RSI calculation with sufficient data."""
        result = calculator.calculate_rsi(sample_price_data)

        assert result is not None
        assert result['rsi_14'] is not None
        assert result['rsi_9'] is not None

        # RSI should be between 0 and 100
        assert 0 <= result['rsi_14'] <= 100
        assert 0 <= result['rsi_9'] <= 100

    def test_calculate_rsi_with_minimal_data(self, calculator, minimal_price_data):
        """Test RSI calculation with minimal data."""
        result = calculator.calculate_rsi(minimal_price_data)

        assert result['rsi_14'] is not None
        assert result['rsi_9'] is not None
        assert 0 <= result['rsi_14'] <= 100

    def test_calculate_rsi_with_insufficient_data(self, calculator):
        """Test RSI calculation with insufficient data."""
        dates = pd.date_range(end=datetime.now(), periods=5, freq='D')
        df = pd.DataFrame({
            'close': [50000, 50100, 50200, 50300, 50400]
        }, index=dates)

        result = calculator.calculate_rsi(df)

        # RSI-14 should be None (not enough data)
        assert result['rsi_14'] is None
        # RSI-9 could be None too (barely enough data)

    def test_calculate_rsi_with_empty_dataframe(self, calculator):
        """Test RSI calculation with empty DataFrame."""
        df = pd.DataFrame()
        result = calculator.calculate_rsi(df)

        assert result['rsi_14'] is None
        assert result['rsi_9'] is None


class TestMACD:
    """Tests for MACD calculations."""

    def test_calculate_macd_with_sufficient_data(self, calculator, sample_price_data):
        """Test MACD calculation with sufficient data."""
        result = calculator.calculate_macd(sample_price_data)

        assert result is not None
        assert result['macd'] is not None
        assert result['macd_signal'] is not None
        assert result['macd_histogram'] is not None

        # MACD histogram should equal MACD - Signal
        expected_histogram = result['macd'] - result['macd_signal']
        assert abs(result['macd_histogram'] - expected_histogram) < 0.01

    def test_calculate_macd_with_insufficient_data(self, calculator):
        """Test MACD calculation with insufficient data."""
        dates = pd.date_range(end=datetime.now(), periods=20, freq='D')
        df = pd.DataFrame({
            'close': [50000 + i * 100 for i in range(20)]
        }, index=dates)

        result = calculator.calculate_macd(df)

        # MACD needs at least 26 periods
        assert result['macd'] is None
        assert result['macd_signal'] is None
        assert result['macd_histogram'] is None

    def test_calculate_macd_with_empty_dataframe(self, calculator):
        """Test MACD calculation with empty DataFrame."""
        df = pd.DataFrame()
        result = calculator.calculate_macd(df)

        assert result['macd'] is None
        assert result['macd_signal'] is None
        assert result['macd_histogram'] is None


class TestBollingerBands:
    """Tests for Bollinger Bands calculations."""

    def test_calculate_bollinger_bands_with_sufficient_data(self, calculator, sample_price_data):
        """Test Bollinger Bands calculation with sufficient data."""
        result = calculator.calculate_bollinger_bands(sample_price_data)

        assert result is not None
        assert result['bollinger_upper'] is not None
        assert result['bollinger_middle'] is not None
        assert result['bollinger_lower'] is not None

        # Upper > Middle > Lower
        assert result['bollinger_upper'] > result['bollinger_middle']
        assert result['bollinger_middle'] > result['bollinger_lower']

    def test_calculate_bollinger_bands_with_minimal_data(self, calculator, minimal_price_data):
        """Test Bollinger Bands calculation with minimal data."""
        result = calculator.calculate_bollinger_bands(minimal_price_data)

        assert result['bollinger_upper'] is not None
        assert result['bollinger_middle'] is not None
        assert result['bollinger_lower'] is not None

    def test_calculate_bollinger_bands_with_insufficient_data(self, calculator):
        """Test Bollinger Bands calculation with insufficient data."""
        dates = pd.date_range(end=datetime.now(), periods=10, freq='D')
        df = pd.DataFrame({
            'close': [50000 + i * 100 for i in range(10)]
        }, index=dates)

        result = calculator.calculate_bollinger_bands(df)

        # Needs at least 20 periods by default
        assert result['bollinger_upper'] is None
        assert result['bollinger_middle'] is None
        assert result['bollinger_lower'] is None

    def test_calculate_bollinger_bands_custom_parameters(self, calculator, sample_price_data):
        """Test Bollinger Bands with custom parameters."""
        result = calculator.calculate_bollinger_bands(
            sample_price_data,
            period=10,
            std_dev=3.0
        )

        assert result['bollinger_upper'] is not None
        assert result['bollinger_middle'] is not None
        assert result['bollinger_lower'] is not None


class TestVolumeIndicators:
    """Tests for volume indicator calculations."""

    def test_calculate_volume_indicators_with_sufficient_data(self, calculator, sample_price_data):
        """Test volume indicators calculation with sufficient data."""
        result = calculator.calculate_volume_indicators(sample_price_data)

        assert result is not None
        assert result['obv'] is not None
        assert result['volume_ma_20'] is not None

        # OBV can be positive or negative
        assert isinstance(result['obv'], int)
        # Volume MA should be positive
        assert result['volume_ma_20'] > 0

    def test_calculate_volume_indicators_with_minimal_data(self, calculator, minimal_price_data):
        """Test volume indicators with minimal data."""
        result = calculator.calculate_volume_indicators(minimal_price_data)

        assert result['obv'] is not None
        assert result['volume_ma_20'] is not None

    def test_calculate_volume_indicators_with_missing_columns(self, calculator):
        """Test volume indicators with missing columns."""
        df = pd.DataFrame({
            'close': [50000, 50100, 50200]
        })

        result = calculator.calculate_volume_indicators(df)

        assert result['obv'] is None
        assert result['volume_ma_20'] is None


class TestATR:
    """Tests for ATR calculations."""

    def test_calculate_atr_with_sufficient_data(self, calculator, sample_price_data):
        """Test ATR calculation with sufficient data."""
        result = calculator.calculate_atr(sample_price_data)

        assert result is not None
        assert result > 0
        assert isinstance(result, float)

    def test_calculate_atr_with_insufficient_data(self, calculator):
        """Test ATR calculation with insufficient data."""
        dates = pd.date_range(end=datetime.now(), periods=10, freq='D')
        df = pd.DataFrame({
            'high': [50000 + i * 100 for i in range(10)],
            'low': [49000 + i * 100 for i in range(10)],
            'close': [49500 + i * 100 for i in range(10)]
        }, index=dates)

        result = calculator.calculate_atr(df)

        # Needs at least 14 periods
        assert result is None

    def test_calculate_atr_with_missing_columns(self, calculator, sample_price_data):
        """Test ATR with missing columns."""
        df = sample_price_data.drop('high', axis=1)
        result = calculator.calculate_atr(df)

        assert result is None


class TestStochastic:
    """Tests for Stochastic Oscillator calculations."""

    def test_calculate_stochastic_with_sufficient_data(self, calculator, sample_price_data):
        """Test Stochastic calculation with sufficient data."""
        result = calculator.calculate_stochastic(sample_price_data)

        assert result is not None
        assert result['stochastic_k'] is not None
        assert result['stochastic_d'] is not None

        # Stochastic should be between 0 and 100
        assert 0 <= result['stochastic_k'] <= 100
        assert 0 <= result['stochastic_d'] <= 100

    def test_calculate_stochastic_with_insufficient_data(self, calculator):
        """Test Stochastic with insufficient data."""
        dates = pd.date_range(end=datetime.now(), periods=10, freq='D')
        df = pd.DataFrame({
            'high': [50000 + i * 100 for i in range(10)],
            'low': [49000 + i * 100 for i in range(10)],
            'close': [49500 + i * 100 for i in range(10)]
        }, index=dates)

        result = calculator.calculate_stochastic(df)

        # Needs at least 14 periods
        assert result['stochastic_k'] is None
        assert result['stochastic_d'] is None


class TestAllIndicators:
    """Tests for calculating all indicators at once."""

    def test_calculate_all_indicators_with_sufficient_data(self, calculator, sample_price_data):
        """Test calculating all indicators with sufficient data."""
        result = calculator.calculate_all_indicators(sample_price_data)

        assert isinstance(result, TechnicalIndicatorData)

        # Check that most indicators are calculated
        assert result.sma_20 is not None
        assert result.sma_50 is not None
        assert result.sma_120 is not None
        assert result.sma_200 is not None
        assert result.ema_12 is not None
        assert result.ema_26 is not None

        assert result.rsi_14 is not None
        assert result.rsi_9 is not None

        assert result.macd is not None
        assert result.macd_signal is not None
        assert result.macd_histogram is not None

        assert result.bollinger_upper is not None
        assert result.bollinger_middle is not None
        assert result.bollinger_lower is not None

        assert result.obv is not None
        assert result.volume_ma_20 is not None

        assert result.atr is not None
        assert result.stochastic_k is not None
        assert result.stochastic_d is not None

    def test_calculate_all_indicators_with_minimal_data(self, calculator, minimal_price_data):
        """Test calculating all indicators with minimal data."""
        result = calculator.calculate_all_indicators(minimal_price_data)

        assert isinstance(result, TechnicalIndicatorData)

        # Short-term indicators should be available
        assert result.sma_5 is not None
        assert result.sma_20 is not None
        assert result.rsi_14 is not None

        # Long-term indicators should be None
        assert result.sma_200 is None

    def test_calculate_all_indicators_with_empty_dataframe(self, calculator):
        """Test calculating all indicators with empty DataFrame."""
        df = pd.DataFrame()
        result = calculator.calculate_all_indicators(df)

        assert isinstance(result, TechnicalIndicatorData)

        # All indicators should be None
        assert result.sma_20 is None
        assert result.rsi_14 is None
        assert result.macd is None

    def test_to_dict_conversion(self, calculator, sample_price_data):
        """Test converting TechnicalIndicatorData to dictionary."""
        result = calculator.calculate_all_indicators(sample_price_data)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert 'sma_20' in result_dict
        assert 'rsi_14' in result_dict
        assert 'macd' in result_dict
        assert 'bollinger_upper' in result_dict
        assert 'obv' in result_dict
        assert 'date' in result_dict

    def test_calculation_date_setting(self, calculator, sample_price_data):
        """Test that calculation date is properly set."""
        custom_date = datetime(2024, 1, 15)
        result = calculator.calculate_all_indicators(
            sample_price_data,
            calculation_date=custom_date
        )

        assert result.calculation_date == custom_date


class TestHelperMethods:
    """Tests for helper methods."""

    def test_safe_round_with_valid_value(self, calculator):
        """Test safe rounding with valid value."""
        result = calculator._safe_round(123.456789, decimals=2)
        assert result == 123.46

    def test_safe_round_with_none(self, calculator):
        """Test safe rounding with None."""
        result = calculator._safe_round(None)
        assert result is None

    def test_safe_round_with_nan(self, calculator):
        """Test safe rounding with NaN."""
        result = calculator._safe_round(np.nan)
        assert result is None

    def test_safe_round_with_inf(self, calculator):
        """Test safe rounding with infinity."""
        result = calculator._safe_round(np.inf)
        assert result is None

    def test_safe_int_with_valid_value(self, calculator):
        """Test safe int conversion with valid value."""
        result = calculator._safe_int(123.456)
        assert result == 123

    def test_safe_int_with_none(self, calculator):
        """Test safe int conversion with None."""
        result = calculator._safe_int(None)
        assert result is None

    def test_safe_int_with_nan(self, calculator):
        """Test safe int conversion with NaN."""
        result = calculator._safe_int(np.nan)
        assert result is None
