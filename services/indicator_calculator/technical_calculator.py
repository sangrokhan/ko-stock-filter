"""
Technical Indicator Calculator.

Calculates technical indicators including:
- Moving Averages (MA20, MA60, MA120, MA200)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Volume analysis (OBV, Volume MA)
- Price momentum indicators
- ATR (Average True Range)
- Stochastic Oscillator
- ADX (Average Directional Index)
"""
from datetime import datetime
from typing import Optional, Dict, Any
import logging
import pandas as pd
import numpy as np

try:
    import pandas_ta as ta
except ImportError:
    ta = None
    logging.warning("pandas-ta not installed. Technical indicators may not work.")

logger = logging.getLogger(__name__)


class TechnicalIndicatorData:
    """Container for calculated technical indicators."""

    def __init__(self):
        # Moving Averages
        self.sma_5: Optional[float] = None
        self.sma_20: Optional[float] = None
        self.sma_50: Optional[float] = None
        self.sma_120: Optional[float] = None
        self.sma_200: Optional[float] = None
        self.ema_12: Optional[float] = None
        self.ema_26: Optional[float] = None

        # Momentum Indicators
        self.rsi_14: Optional[float] = None
        self.rsi_9: Optional[float] = None
        self.stochastic_k: Optional[float] = None
        self.stochastic_d: Optional[float] = None

        # Trend Indicators
        self.macd: Optional[float] = None
        self.macd_signal: Optional[float] = None
        self.macd_histogram: Optional[float] = None
        self.adx: Optional[float] = None

        # Volatility Indicators
        self.bollinger_upper: Optional[float] = None
        self.bollinger_middle: Optional[float] = None
        self.bollinger_lower: Optional[float] = None
        self.atr: Optional[float] = None

        # Volume Indicators
        self.obv: Optional[int] = None
        self.volume_ma_20: Optional[int] = None

        self.calculation_date: datetime = datetime.utcnow()
        self.errors: list = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            # Moving Averages
            'sma_5': self.sma_5,
            'sma_20': self.sma_20,
            'sma_50': self.sma_50,
            'sma_120': self.sma_120,
            'sma_200': self.sma_200,
            'ema_12': self.ema_12,
            'ema_26': self.ema_26,
            # Momentum
            'rsi_14': self.rsi_14,
            'rsi_9': self.rsi_9,
            'stochastic_k': self.stochastic_k,
            'stochastic_d': self.stochastic_d,
            # Trend
            'macd': self.macd,
            'macd_signal': self.macd_signal,
            'macd_histogram': self.macd_histogram,
            'adx': self.adx,
            # Volatility
            'bollinger_upper': self.bollinger_upper,
            'bollinger_middle': self.bollinger_middle,
            'bollinger_lower': self.bollinger_lower,
            'atr': self.atr,
            # Volume
            'obv': self.obv,
            'volume_ma_20': self.volume_ma_20,
            'date': self.calculation_date,
        }


class TechnicalIndicatorCalculator:
    """Calculator for technical indicators using pandas-ta."""

    def __init__(self):
        """Initialize the technical calculator."""
        self.logger = logging.getLogger(__name__)
        if ta is None:
            self.logger.warning("pandas-ta is not available. Install it with: pip install pandas-ta")

    def calculate_moving_averages(
        self,
        df: pd.DataFrame,
        price_column: str = 'close'
    ) -> Dict[str, Optional[float]]:
        """
        Calculate Simple and Exponential Moving Averages.

        Args:
            df: DataFrame with OHLCV data
            price_column: Column to use for calculations (default: 'close')

        Returns:
            Dictionary with MA values
        """
        result = {
            'sma_5': None,
            'sma_20': None,
            'sma_50': None,
            'sma_120': None,
            'sma_200': None,
            'ema_12': None,
            'ema_26': None,
        }

        try:
            if df.empty or price_column not in df.columns:
                self.logger.warning("Empty DataFrame or missing price column")
                return result

            prices = df[price_column]

            # Simple Moving Averages
            if len(df) >= 5:
                result['sma_5'] = self._safe_round(prices.rolling(window=5).mean().iloc[-1])
            if len(df) >= 20:
                result['sma_20'] = self._safe_round(prices.rolling(window=20).mean().iloc[-1])
            if len(df) >= 50:
                result['sma_50'] = self._safe_round(prices.rolling(window=50).mean().iloc[-1])
            if len(df) >= 120:
                result['sma_120'] = self._safe_round(prices.rolling(window=120).mean().iloc[-1])
            if len(df) >= 200:
                result['sma_200'] = self._safe_round(prices.rolling(window=200).mean().iloc[-1])

            # Exponential Moving Averages
            if len(df) >= 12:
                result['ema_12'] = self._safe_round(prices.ewm(span=12, adjust=False).mean().iloc[-1])
            if len(df) >= 26:
                result['ema_26'] = self._safe_round(prices.ewm(span=26, adjust=False).mean().iloc[-1])

            return result

        except Exception as e:
            self.logger.error(f"Error calculating moving averages: {e}")
            return result

    def calculate_rsi(
        self,
        df: pd.DataFrame,
        price_column: str = 'close'
    ) -> Dict[str, Optional[float]]:
        """
        Calculate Relative Strength Index (RSI).

        Args:
            df: DataFrame with OHLCV data
            price_column: Column to use for calculations (default: 'close')

        Returns:
            Dictionary with RSI values
        """
        result = {
            'rsi_14': None,
            'rsi_9': None,
        }

        try:
            if df.empty or price_column not in df.columns:
                return result

            prices = df[price_column]

            # RSI 14-period
            if len(df) >= 14:
                if ta is not None:
                    rsi_14 = ta.rsi(prices, length=14)
                    if rsi_14 is not None and not rsi_14.empty:
                        result['rsi_14'] = self._safe_round(rsi_14.iloc[-1])
                else:
                    result['rsi_14'] = self._calculate_rsi_manual(prices, period=14)

            # RSI 9-period
            if len(df) >= 9:
                if ta is not None:
                    rsi_9 = ta.rsi(prices, length=9)
                    if rsi_9 is not None and not rsi_9.empty:
                        result['rsi_9'] = self._safe_round(rsi_9.iloc[-1])
                else:
                    result['rsi_9'] = self._calculate_rsi_manual(prices, period=9)

            return result

        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return result

    def _calculate_rsi_manual(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """
        Manually calculate RSI when pandas-ta is not available.

        Args:
            prices: Price series
            period: RSI period

        Returns:
            RSI value or None
        """
        try:
            if len(prices) < period + 1:
                return None

            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            return self._safe_round(rsi.iloc[-1])

        except Exception as e:
            self.logger.error(f"Error in manual RSI calculation: {e}")
            return None

    def calculate_macd(
        self,
        df: pd.DataFrame,
        price_column: str = 'close'
    ) -> Dict[str, Optional[float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            df: DataFrame with OHLCV data
            price_column: Column to use for calculations (default: 'close')

        Returns:
            Dictionary with MACD values
        """
        result = {
            'macd': None,
            'macd_signal': None,
            'macd_histogram': None,
        }

        try:
            if df.empty or price_column not in df.columns or len(df) < 26:
                return result

            prices = df[price_column]

            if ta is not None:
                macd_df = ta.macd(prices, fast=12, slow=26, signal=9)
                if macd_df is not None and not macd_df.empty:
                    # pandas-ta returns columns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
                    if f'MACD_12_26_9' in macd_df.columns:
                        result['macd'] = self._safe_round(macd_df[f'MACD_12_26_9'].iloc[-1])
                    if f'MACDs_12_26_9' in macd_df.columns:
                        result['macd_signal'] = self._safe_round(macd_df[f'MACDs_12_26_9'].iloc[-1])
                    if f'MACDh_12_26_9' in macd_df.columns:
                        result['macd_histogram'] = self._safe_round(macd_df[f'MACDh_12_26_9'].iloc[-1])
            else:
                # Manual MACD calculation
                ema_12 = prices.ewm(span=12, adjust=False).mean()
                ema_26 = prices.ewm(span=26, adjust=False).mean()
                macd_line = ema_12 - ema_26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                histogram = macd_line - signal_line

                result['macd'] = self._safe_round(macd_line.iloc[-1])
                result['macd_signal'] = self._safe_round(signal_line.iloc[-1])
                result['macd_histogram'] = self._safe_round(histogram.iloc[-1])

            return result

        except Exception as e:
            self.logger.error(f"Error calculating MACD: {e}")
            return result

    def calculate_bollinger_bands(
        self,
        df: pd.DataFrame,
        price_column: str = 'close',
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, Optional[float]]:
        """
        Calculate Bollinger Bands.

        Args:
            df: DataFrame with OHLCV data
            price_column: Column to use for calculations (default: 'close')
            period: Period for moving average (default: 20)
            std_dev: Number of standard deviations (default: 2.0)

        Returns:
            Dictionary with Bollinger Band values
        """
        result = {
            'bollinger_upper': None,
            'bollinger_middle': None,
            'bollinger_lower': None,
        }

        try:
            if df.empty or price_column not in df.columns or len(df) < period:
                return result

            prices = df[price_column]

            if ta is not None:
                bbands = ta.bbands(prices, length=period, std=std_dev)
                if bbands is not None and not bbands.empty:
                    if f'BBU_{period}_{std_dev}' in bbands.columns:
                        result['bollinger_upper'] = self._safe_round(bbands[f'BBU_{period}_{std_dev}'].iloc[-1])
                    if f'BBM_{period}_{std_dev}' in bbands.columns:
                        result['bollinger_middle'] = self._safe_round(bbands[f'BBM_{period}_{std_dev}'].iloc[-1])
                    if f'BBL_{period}_{std_dev}' in bbands.columns:
                        result['bollinger_lower'] = self._safe_round(bbands[f'BBL_{period}_{std_dev}'].iloc[-1])
            else:
                # Manual Bollinger Bands calculation
                middle = prices.rolling(window=period).mean()
                std = prices.rolling(window=period).std()
                upper = middle + (std * std_dev)
                lower = middle - (std * std_dev)

                result['bollinger_upper'] = self._safe_round(upper.iloc[-1])
                result['bollinger_middle'] = self._safe_round(middle.iloc[-1])
                result['bollinger_lower'] = self._safe_round(lower.iloc[-1])

            return result

        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {e}")
            return result

    def calculate_volume_indicators(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Optional[int]]:
        """
        Calculate volume-based indicators.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary with volume indicator values
        """
        result = {
            'obv': None,
            'volume_ma_20': None,
        }

        try:
            if df.empty or 'volume' not in df.columns or 'close' not in df.columns:
                return result

            # On Balance Volume (OBV)
            if ta is not None:
                obv = ta.obv(df['close'], df['volume'])
                if obv is not None and not obv.empty:
                    result['obv'] = self._safe_int(obv.iloc[-1])
            else:
                # Manual OBV calculation
                obv = pd.Series(0, index=df.index)
                for i in range(1, len(df)):
                    if df['close'].iloc[i] > df['close'].iloc[i-1]:
                        obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
                    elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                        obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
                    else:
                        obv.iloc[i] = obv.iloc[i-1]
                result['obv'] = self._safe_int(obv.iloc[-1])

            # Volume Moving Average (20-day)
            if len(df) >= 20:
                volume_ma = df['volume'].rolling(window=20).mean()
                result['volume_ma_20'] = self._safe_int(volume_ma.iloc[-1])

            return result

        except Exception as e:
            self.logger.error(f"Error calculating volume indicators: {e}")
            return result

    def calculate_atr(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> Optional[float]:
        """
        Calculate Average True Range (ATR).

        Args:
            df: DataFrame with OHLCV data
            period: ATR period (default: 14)

        Returns:
            ATR value or None
        """
        try:
            if df.empty or len(df) < period:
                return None

            required_cols = ['high', 'low', 'close']
            if not all(col in df.columns for col in required_cols):
                return None

            if ta is not None:
                atr = ta.atr(df['high'], df['low'], df['close'], length=period)
                if atr is not None and not atr.empty:
                    return self._safe_round(atr.iloc[-1])
            else:
                # Manual ATR calculation
                high_low = df['high'] - df['low']
                high_close = np.abs(df['high'] - df['close'].shift())
                low_close = np.abs(df['low'] - df['close'].shift())

                true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = true_range.rolling(window=period).mean()

                return self._safe_round(atr.iloc[-1])

        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return None

    def calculate_stochastic(
        self,
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3
    ) -> Dict[str, Optional[float]]:
        """
        Calculate Stochastic Oscillator.

        Args:
            df: DataFrame with OHLCV data
            k_period: Period for %K (default: 14)
            d_period: Period for %D (default: 3)

        Returns:
            Dictionary with Stochastic values
        """
        result = {
            'stochastic_k': None,
            'stochastic_d': None,
        }

        try:
            if df.empty or len(df) < k_period:
                return result

            required_cols = ['high', 'low', 'close']
            if not all(col in df.columns for col in required_cols):
                return result

            if ta is not None:
                stoch = ta.stoch(df['high'], df['low'], df['close'], k=k_period, d=d_period)
                if stoch is not None and not stoch.empty:
                    if f'STOCHk_{k_period}_{d_period}_3' in stoch.columns:
                        result['stochastic_k'] = self._safe_round(stoch[f'STOCHk_{k_period}_{d_period}_3'].iloc[-1])
                    if f'STOCHd_{k_period}_{d_period}_3' in stoch.columns:
                        result['stochastic_d'] = self._safe_round(stoch[f'STOCHd_{k_period}_{d_period}_3'].iloc[-1])
            else:
                # Manual Stochastic calculation
                low_min = df['low'].rolling(window=k_period).min()
                high_max = df['high'].rolling(window=k_period).max()

                k_percent = 100 * ((df['close'] - low_min) / (high_max - low_min))
                d_percent = k_percent.rolling(window=d_period).mean()

                result['stochastic_k'] = self._safe_round(k_percent.iloc[-1])
                result['stochastic_d'] = self._safe_round(d_percent.iloc[-1])

            return result

        except Exception as e:
            self.logger.error(f"Error calculating Stochastic: {e}")
            return result

    def calculate_adx(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> Optional[float]:
        """
        Calculate Average Directional Index (ADX).

        Args:
            df: DataFrame with OHLCV data
            period: ADX period (default: 14)

        Returns:
            ADX value or None
        """
        try:
            if df.empty or len(df) < period * 2:
                return None

            required_cols = ['high', 'low', 'close']
            if not all(col in df.columns for col in required_cols):
                return None

            if ta is not None:
                adx = ta.adx(df['high'], df['low'], df['close'], length=period)
                if adx is not None and not adx.empty:
                    if f'ADX_{period}' in adx.columns:
                        return self._safe_round(adx[f'ADX_{period}'].iloc[-1])

            # Manual ADX calculation is complex, return None if pandas-ta not available
            return None

        except Exception as e:
            self.logger.error(f"Error calculating ADX: {e}")
            return None

    def calculate_all_indicators(
        self,
        df: pd.DataFrame,
        calculation_date: Optional[datetime] = None
    ) -> TechnicalIndicatorData:
        """
        Calculate all technical indicators for a stock.

        Args:
            df: DataFrame with OHLCV data (indexed by date)
            calculation_date: Date of calculation (default: last date in df)

        Returns:
            TechnicalIndicatorData object with all calculated indicators
        """
        indicator = TechnicalIndicatorData()

        try:
            if df.empty:
                self.logger.warning("Empty DataFrame provided")
                return indicator

            # Set calculation date
            if calculation_date:
                indicator.calculation_date = calculation_date
            elif not df.empty:
                indicator.calculation_date = df.index[-1]

            # Calculate Moving Averages
            ma_results = self.calculate_moving_averages(df)
            indicator.sma_5 = ma_results['sma_5']
            indicator.sma_20 = ma_results['sma_20']
            indicator.sma_50 = ma_results['sma_50']
            indicator.sma_120 = ma_results['sma_120']
            indicator.sma_200 = ma_results['sma_200']
            indicator.ema_12 = ma_results['ema_12']
            indicator.ema_26 = ma_results['ema_26']

            # Calculate RSI
            rsi_results = self.calculate_rsi(df)
            indicator.rsi_14 = rsi_results['rsi_14']
            indicator.rsi_9 = rsi_results['rsi_9']

            # Calculate MACD
            macd_results = self.calculate_macd(df)
            indicator.macd = macd_results['macd']
            indicator.macd_signal = macd_results['macd_signal']
            indicator.macd_histogram = macd_results['macd_histogram']

            # Calculate Bollinger Bands
            bb_results = self.calculate_bollinger_bands(df)
            indicator.bollinger_upper = bb_results['bollinger_upper']
            indicator.bollinger_middle = bb_results['bollinger_middle']
            indicator.bollinger_lower = bb_results['bollinger_lower']

            # Calculate Volume Indicators
            volume_results = self.calculate_volume_indicators(df)
            indicator.obv = volume_results['obv']
            indicator.volume_ma_20 = volume_results['volume_ma_20']

            # Calculate ATR
            indicator.atr = self.calculate_atr(df)

            # Calculate Stochastic
            stoch_results = self.calculate_stochastic(df)
            indicator.stochastic_k = stoch_results['stochastic_k']
            indicator.stochastic_d = stoch_results['stochastic_d']

            # Calculate ADX
            indicator.adx = self.calculate_adx(df)

            return indicator

        except Exception as e:
            self.logger.error(f"Error calculating all indicators: {e}", exc_info=True)
            indicator.errors.append(str(e))
            return indicator

    def _safe_round(self, value: Any, decimals: int = 2) -> Optional[float]:
        """
        Safely round a value to specified decimals.

        Args:
            value: Value to round
            decimals: Number of decimal places

        Returns:
            Rounded float or None
        """
        try:
            if pd.isna(value) or value is None:
                return None
            if np.isinf(value):
                return None
            return round(float(value), decimals)
        except (TypeError, ValueError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        """
        Safely convert value to int.

        Args:
            value: Value to convert

        Returns:
            Int value or None
        """
        try:
            if pd.isna(value) or value is None:
                return None
            if np.isinf(value):
                return None
            return int(value)
        except (TypeError, ValueError):
            return None
