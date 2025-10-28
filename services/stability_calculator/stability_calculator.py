"""
Stability Score Calculator.

Calculates comprehensive stability metrics including:
- Price volatility (standard deviation of returns)
- Beta coefficient (systematic risk vs market)
- Volume stability
- Earnings consistency
- Debt stability trend

Produces an overall stability score (0-100) where higher values indicate more stable stocks.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import logging
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class StabilityMetrics:
    """Container for calculated stability metrics."""

    def __init__(self):
        # Price Volatility
        self.price_volatility: Optional[float] = None
        self.price_volatility_score: Optional[float] = None
        self.returns_mean: Optional[float] = None
        self.returns_std: Optional[float] = None

        # Beta Coefficient
        self.beta: Optional[float] = None
        self.beta_score: Optional[float] = None
        self.market_correlation: Optional[float] = None

        # Volume Stability
        self.volume_stability: Optional[float] = None
        self.volume_stability_score: Optional[float] = None
        self.volume_mean: Optional[int] = None
        self.volume_std: Optional[int] = None

        # Earnings Consistency
        self.earnings_consistency: Optional[float] = None
        self.earnings_consistency_score: Optional[float] = None
        self.earnings_trend: Optional[float] = None

        # Debt Stability
        self.debt_stability: Optional[float] = None
        self.debt_stability_score: Optional[float] = None
        self.debt_trend: Optional[float] = None
        self.debt_ratio_current: Optional[float] = None

        # Overall Score
        self.stability_score: float = 0.0

        # Weights
        self.weight_price: float = 0.25
        self.weight_beta: float = 0.20
        self.weight_volume: float = 0.15
        self.weight_earnings: float = 0.25
        self.weight_debt: float = 0.15

        # Data quality
        self.data_points_price: int = 0
        self.data_points_earnings: int = 0
        self.data_points_debt: int = 0
        self.calculation_period_days: int = 0
        self.calculation_date: datetime = datetime.utcnow()
        self.errors: list = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'date': self.calculation_date,
            'price_volatility': self.price_volatility,
            'price_volatility_score': self.price_volatility_score,
            'returns_mean': self.returns_mean,
            'returns_std': self.returns_std,
            'beta': self.beta,
            'beta_score': self.beta_score,
            'market_correlation': self.market_correlation,
            'volume_stability': self.volume_stability,
            'volume_stability_score': self.volume_stability_score,
            'volume_mean': self.volume_mean,
            'volume_std': self.volume_std,
            'earnings_consistency': self.earnings_consistency,
            'earnings_consistency_score': self.earnings_consistency_score,
            'earnings_trend': self.earnings_trend,
            'debt_stability': self.debt_stability,
            'debt_stability_score': self.debt_stability_score,
            'debt_trend': self.debt_trend,
            'debt_ratio_current': self.debt_ratio_current,
            'stability_score': self.stability_score,
            'weight_price': self.weight_price,
            'weight_beta': self.weight_beta,
            'weight_volume': self.weight_volume,
            'weight_earnings': self.weight_earnings,
            'weight_debt': self.weight_debt,
            'data_points_price': self.data_points_price,
            'data_points_earnings': self.data_points_earnings,
            'data_points_debt': self.data_points_debt,
            'calculation_period_days': self.calculation_period_days,
        }


class StabilityCalculator:
    """Calculator for stock stability metrics."""

    def __init__(self,
                 lookback_days: int = 252,  # ~1 year of trading days
                 min_price_points: int = 30,
                 min_earnings_points: int = 4):
        """
        Initialize the stability calculator.

        Args:
            lookback_days: Number of days to look back for price data
            min_price_points: Minimum number of price points required
            min_earnings_points: Minimum number of earnings points required
        """
        self.logger = logging.getLogger(__name__)
        self.lookback_days = lookback_days
        self.min_price_points = min_price_points
        self.min_earnings_points = min_earnings_points

    def calculate_price_volatility(
        self,
        prices: List[float]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate price volatility using standard deviation of returns.

        Args:
            prices: List of closing prices (chronologically ordered)

        Returns:
            Tuple of (volatility, score) or (None, None) if insufficient data
        """
        try:
            if not prices or len(prices) < 2:
                self.logger.debug("Insufficient price data for volatility calculation")
                return None, None

            # Calculate daily returns
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    ret = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(ret)

            if len(returns) < self.min_price_points:
                self.logger.debug(f"Insufficient returns data: {len(returns)} < {self.min_price_points}")
                return None, None

            # Calculate volatility (standard deviation of returns)
            returns_array = np.array(returns)
            volatility = float(np.std(returns_array))

            # Convert to annualized volatility
            annualized_volatility = volatility * np.sqrt(252)

            # Score: Lower volatility = higher stability score
            # Typical stock volatility ranges from 15% to 50%+ annually
            # We'll normalize this to 0-100 where:
            # - 15% volatility = 100 points
            # - 50% volatility = 0 points
            score = max(0, min(100, 100 - (annualized_volatility - 0.15) * 285.7))

            return round(float(annualized_volatility), 4), round(float(score), 2)

        except Exception as e:
            self.logger.warning(f"Error calculating price volatility: {e}")
            return None, None

    def calculate_beta(
        self,
        stock_prices: List[float],
        market_prices: List[float]
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate beta coefficient (systematic risk relative to market).

        Args:
            stock_prices: List of stock closing prices
            market_prices: List of market index closing prices (same dates)

        Returns:
            Tuple of (beta, score, correlation) or (None, None, None)
        """
        try:
            if not stock_prices or not market_prices:
                self.logger.debug("Missing price data for beta calculation")
                return None, None, None

            if len(stock_prices) != len(market_prices):
                self.logger.warning("Stock and market price arrays have different lengths")
                return None, None, None

            if len(stock_prices) < self.min_price_points:
                self.logger.debug(f"Insufficient data for beta: {len(stock_prices)} < {self.min_price_points}")
                return None, None, None

            # Calculate returns
            stock_returns = []
            market_returns = []

            for i in range(1, len(stock_prices)):
                if stock_prices[i-1] > 0 and market_prices[i-1] > 0:
                    stock_ret = (stock_prices[i] - stock_prices[i-1]) / stock_prices[i-1]
                    market_ret = (market_prices[i] - market_prices[i-1]) / market_prices[i-1]
                    stock_returns.append(stock_ret)
                    market_returns.append(market_ret)

            if len(stock_returns) < self.min_price_points:
                return None, None, None

            stock_returns_array = np.array(stock_returns)
            market_returns_array = np.array(market_returns)

            # Calculate covariance and variance
            covariance = np.cov(stock_returns_array, market_returns_array)[0, 1]
            market_variance = np.var(market_returns_array)

            if market_variance == 0:
                self.logger.debug("Market variance is zero")
                return None, None, None

            # Calculate beta
            beta = covariance / market_variance

            # Calculate correlation
            correlation = np.corrcoef(stock_returns_array, market_returns_array)[0, 1]

            # Score: Beta closer to 1.0 = more stable (market-like behavior)
            # Beta < 0.5 or > 1.5 = less stable
            # Score formula: penalize deviation from 1.0
            beta_deviation = abs(beta - 1.0)
            score = max(0, min(100, 100 - (beta_deviation * 100)))

            return round(float(beta), 3), round(float(score), 2), round(float(correlation), 3)

        except Exception as e:
            self.logger.warning(f"Error calculating beta: {e}")
            return None, None, None

    def calculate_volume_stability(
        self,
        volumes: List[int]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate volume stability using coefficient of variation.

        Args:
            volumes: List of daily trading volumes

        Returns:
            Tuple of (coefficient_of_variation, score) or (None, None)
        """
        try:
            if not volumes or len(volumes) < self.min_price_points:
                self.logger.debug("Insufficient volume data")
                return None, None

            volumes_array = np.array(volumes)
            mean_volume = float(np.mean(volumes_array))
            std_volume = float(np.std(volumes_array))

            if mean_volume == 0:
                self.logger.debug("Mean volume is zero")
                return None, None

            # Coefficient of variation
            cv = std_volume / mean_volume

            # Score: Lower CV = higher stability
            # Typical CV for volume ranges from 0.3 to 2.0+
            # Normalize: CV of 0.3 = 100 points, CV of 2.0 = 0 points
            score = max(0, min(100, 100 - ((cv - 0.3) / 1.7) * 100))

            return round(float(cv), 4), round(float(score), 2)

        except Exception as e:
            self.logger.warning(f"Error calculating volume stability: {e}")
            return None, None

    def calculate_earnings_consistency(
        self,
        earnings: List[float]
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate earnings consistency using coefficient of variation and trend.

        Args:
            earnings: List of quarterly or annual earnings (chronologically ordered)

        Returns:
            Tuple of (coefficient_of_variation, score, trend) or (None, None, None)
        """
        try:
            if not earnings or len(earnings) < self.min_earnings_points:
                self.logger.debug(f"Insufficient earnings data: {len(earnings) if earnings else 0}")
                return None, None, None

            earnings_array = np.array(earnings)

            # Remove zero and negative earnings for CV calculation
            positive_earnings = earnings_array[earnings_array > 0]

            if len(positive_earnings) < self.min_earnings_points:
                self.logger.debug("Insufficient positive earnings data")
                return None, None, None

            mean_earnings = float(np.mean(positive_earnings))
            std_earnings = float(np.std(positive_earnings))

            if mean_earnings == 0:
                return None, None, None

            # Coefficient of variation
            cv = std_earnings / mean_earnings

            # Calculate trend using linear regression
            x = np.arange(len(earnings))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, earnings_array)
            trend = float(slope)

            # Score: Lower CV and positive trend = higher consistency
            # CV component (70% weight)
            cv_score = max(0, min(100, 100 - (cv * 50)))  # Typical earnings CV: 0-2

            # Trend component (30% weight) - positive trend is good
            if mean_earnings != 0:
                trend_normalized = trend / mean_earnings  # Normalize by mean
                trend_score = 50 + min(50, max(-50, trend_normalized * 500))  # -10% to +10% trend
            else:
                trend_score = 50

            # Combined score
            score = cv_score * 0.7 + trend_score * 0.3

            return round(float(cv), 4), round(float(score), 2), round(trend, 2)

        except Exception as e:
            self.logger.warning(f"Error calculating earnings consistency: {e}")
            return None, None, None

    def calculate_debt_stability(
        self,
        debt_ratios: List[float]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate debt stability by analyzing debt ratio trend.

        Args:
            debt_ratios: List of debt ratios over time (chronologically ordered)

        Returns:
            Tuple of (stability_score, trend) or (None, None)
        """
        try:
            if not debt_ratios or len(debt_ratios) < 2:
                self.logger.debug("Insufficient debt ratio data")
                return None, None

            debt_array = np.array(debt_ratios)

            # Calculate trend using linear regression
            x = np.arange(len(debt_ratios))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, debt_array)
            trend = float(slope)

            # Current debt ratio
            current_debt = float(debt_ratios[-1])

            # Score components:
            # 1. Low debt ratio is good (50% weight)
            # 2. Stable or decreasing trend is good (50% weight)

            # Debt ratio component: < 30% = 100, > 70% = 0
            debt_score = max(0, min(100, 100 - ((current_debt - 30) / 40) * 100))

            # Trend component: decreasing = 100, stable = 75, increasing = 0
            if trend < -1.0:  # Decreasing significantly
                trend_score = 100
            elif trend < 0:  # Decreasing slightly
                trend_score = 90 + (trend * 10)
            elif trend < 1.0:  # Increasing slightly
                trend_score = 75 - (trend * 75)
            else:  # Increasing significantly
                trend_score = max(0, 75 - (trend * 75))

            # Combined score
            score = debt_score * 0.5 + trend_score * 0.5

            return round(float(score), 2), round(trend, 4)

        except Exception as e:
            self.logger.warning(f"Error calculating debt stability: {e}")
            return None, None

    def calculate_stability_score(
        self,
        price_data: List[Dict[str, Any]],
        market_data: List[Dict[str, Any]],
        earnings_data: List[float],
        debt_data: List[float],
        weights: Optional[Dict[str, float]] = None
    ) -> StabilityMetrics:
        """
        Calculate overall stability score combining all metrics.

        Args:
            price_data: List of price dictionaries with 'close' and 'volume'
            market_data: List of market index price dictionaries with 'close'
            earnings_data: List of earnings values
            debt_data: List of debt ratio values
            weights: Optional custom weights for components

        Returns:
            StabilityMetrics object with all calculated metrics
        """
        metrics = StabilityMetrics()

        # Set custom weights if provided
        if weights:
            metrics.weight_price = weights.get('price', 0.25)
            metrics.weight_beta = weights.get('beta', 0.20)
            metrics.weight_volume = weights.get('volume', 0.15)
            metrics.weight_earnings = weights.get('earnings', 0.25)
            metrics.weight_debt = weights.get('debt', 0.15)

        # Normalize weights to sum to 1.0
        total_weight = (metrics.weight_price + metrics.weight_beta +
                       metrics.weight_volume + metrics.weight_earnings +
                       metrics.weight_debt)
        if total_weight > 0:
            metrics.weight_price /= total_weight
            metrics.weight_beta /= total_weight
            metrics.weight_volume /= total_weight
            metrics.weight_earnings /= total_weight
            metrics.weight_debt /= total_weight

        # Extract price and volume data
        prices = [p['close'] for p in price_data if p.get('close')]
        volumes = [p['volume'] for p in price_data if p.get('volume')]
        market_prices = [m['close'] for m in market_data if m.get('close')]

        metrics.data_points_price = len(prices)
        metrics.data_points_earnings = len(earnings_data) if earnings_data else 0
        metrics.data_points_debt = len(debt_data) if debt_data else 0
        metrics.calculation_period_days = self.lookback_days

        # Calculate each component
        component_scores = []
        component_weights = []

        # 1. Price Volatility
        if prices:
            volatility, vol_score = self.calculate_price_volatility(prices)
            metrics.price_volatility = volatility
            metrics.price_volatility_score = vol_score

            if vol_score is not None:
                returns = [(prices[i] - prices[i-1]) / prices[i-1]
                          for i in range(1, len(prices)) if prices[i-1] > 0]
                if returns:
                    metrics.returns_mean = round(float(np.mean(returns)), 6)
                    metrics.returns_std = round(float(np.std(returns)), 6)

                component_scores.append(vol_score)
                component_weights.append(metrics.weight_price)

        # 2. Beta Coefficient
        if prices and market_prices and len(prices) == len(market_prices):
            beta, beta_score, correlation = self.calculate_beta(prices, market_prices)
            metrics.beta = beta
            metrics.beta_score = beta_score
            metrics.market_correlation = correlation

            if beta_score is not None:
                component_scores.append(beta_score)
                component_weights.append(metrics.weight_beta)

        # 3. Volume Stability
        if volumes:
            cv, vol_score = self.calculate_volume_stability(volumes)
            metrics.volume_stability = cv
            metrics.volume_stability_score = vol_score

            if vol_score is not None:
                metrics.volume_mean = int(np.mean(volumes))
                metrics.volume_std = int(np.std(volumes))

                component_scores.append(vol_score)
                component_weights.append(metrics.weight_volume)

        # 4. Earnings Consistency
        if earnings_data:
            cv, earn_score, trend = self.calculate_earnings_consistency(earnings_data)
            metrics.earnings_consistency = cv
            metrics.earnings_consistency_score = earn_score
            metrics.earnings_trend = trend

            if earn_score is not None:
                component_scores.append(earn_score)
                component_weights.append(metrics.weight_earnings)

        # 5. Debt Stability
        if debt_data:
            debt_score, trend = self.calculate_debt_stability(debt_data)
            metrics.debt_stability_score = debt_score
            metrics.debt_trend = trend
            metrics.debt_ratio_current = float(debt_data[-1]) if debt_data else None

            if debt_score is not None:
                component_scores.append(debt_score)
                component_weights.append(metrics.weight_debt)

        # Calculate overall stability score (weighted average)
        if component_scores and component_weights:
            # Normalize weights for available components
            weight_sum = sum(component_weights)
            if weight_sum > 0:
                normalized_weights = [w / weight_sum for w in component_weights]
                overall_score = sum(score * weight
                                  for score, weight in zip(component_scores, normalized_weights))
                metrics.stability_score = round(float(overall_score), 2)
            else:
                metrics.stability_score = 0.0
        else:
            self.logger.warning("No components available for stability score calculation")
            metrics.stability_score = 0.0

        return metrics
