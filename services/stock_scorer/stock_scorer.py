"""
Stock Composite Scorer.

Calculates comprehensive investment scores including:
- Value score (PER, PBR, dividend yield, PSR)
- Growth score (revenue growth, earnings growth, equity growth)
- Quality score (ROE, margins, debt ratios)
- Momentum score (RSI, price trend, MACD, volume trend)

Produces an overall composite score (0-100) where higher values indicate better investment opportunities.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import logging
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class ScoreMetrics:
    """Container for calculated score metrics."""

    def __init__(self):
        # Component Scores (0-100)
        self.value_score: Optional[float] = None
        self.growth_score: Optional[float] = None
        self.quality_score: Optional[float] = None
        self.momentum_score: Optional[float] = None
        self.composite_score: float = 0.0
        self.percentile_rank: Optional[float] = None

        # Weights
        self.weight_value: float = 0.25
        self.weight_growth: float = 0.25
        self.weight_quality: float = 0.25
        self.weight_momentum: float = 0.25

        # Value Score Components
        self.per_score: Optional[float] = None
        self.pbr_score: Optional[float] = None
        self.dividend_yield_score: Optional[float] = None
        self.psr_score: Optional[float] = None

        # Growth Score Components
        self.revenue_growth_score: Optional[float] = None
        self.earnings_growth_score: Optional[float] = None
        self.equity_growth_score: Optional[float] = None

        # Quality Score Components
        self.roe_score: Optional[float] = None
        self.operating_margin_score: Optional[float] = None
        self.net_margin_score: Optional[float] = None
        self.debt_ratio_score: Optional[float] = None
        self.current_ratio_score: Optional[float] = None

        # Momentum Score Components
        self.rsi_score: Optional[float] = None
        self.price_trend_score: Optional[float] = None
        self.macd_score: Optional[float] = None
        self.volume_trend_score: Optional[float] = None

        # Data quality
        self.data_quality_score: Optional[float] = None
        self.missing_value_count: int = 0
        self.total_metric_count: int = 0
        self.calculation_date: datetime = datetime.utcnow()
        self.errors: list = []
        self.notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'date': self.calculation_date,
            'value_score': self.value_score,
            'growth_score': self.growth_score,
            'quality_score': self.quality_score,
            'momentum_score': self.momentum_score,
            'composite_score': self.composite_score,
            'percentile_rank': self.percentile_rank,
            'weight_value': self.weight_value,
            'weight_growth': self.weight_growth,
            'weight_quality': self.weight_quality,
            'weight_momentum': self.weight_momentum,
            'per_score': self.per_score,
            'pbr_score': self.pbr_score,
            'dividend_yield_score': self.dividend_yield_score,
            'psr_score': self.psr_score,
            'revenue_growth_score': self.revenue_growth_score,
            'earnings_growth_score': self.earnings_growth_score,
            'equity_growth_score': self.equity_growth_score,
            'roe_score': self.roe_score,
            'operating_margin_score': self.operating_margin_score,
            'net_margin_score': self.net_margin_score,
            'debt_ratio_score': self.debt_ratio_score,
            'current_ratio_score': self.current_ratio_score,
            'rsi_score': self.rsi_score,
            'price_trend_score': self.price_trend_score,
            'macd_score': self.macd_score,
            'volume_trend_score': self.volume_trend_score,
            'data_quality_score': self.data_quality_score,
            'missing_value_count': self.missing_value_count,
            'total_metric_count': self.total_metric_count,
            'calculation_method': 'standard',
            'notes': self.notes,
        }


class StockScorer:
    """
    Calculates composite investment scores for stocks.

    Each component score is normalized to 0-100 scale where:
    - Higher scores indicate better investment characteristics
    - Scores account for industry/market benchmarks where applicable
    """

    def __init__(self,
                 weight_value: float = 0.25,
                 weight_growth: float = 0.25,
                 weight_quality: float = 0.25,
                 weight_momentum: float = 0.25):
        """
        Initialize the scorer with custom weights.

        Args:
            weight_value: Weight for value score (default: 0.25)
            weight_growth: Weight for growth score (default: 0.25)
            weight_quality: Weight for quality score (default: 0.25)
            weight_momentum: Weight for momentum score (default: 0.25)
        """
        self.weight_value = weight_value
        self.weight_growth = weight_growth
        self.weight_quality = weight_quality
        self.weight_momentum = weight_momentum

        # Validate weights sum to 1.0
        total_weight = sum([weight_value, weight_growth, weight_quality, weight_momentum])
        if not np.isclose(total_weight, 1.0, atol=0.01):
            logger.warning(f"Weights sum to {total_weight}, normalizing to 1.0")
            norm_factor = 1.0 / total_weight
            self.weight_value *= norm_factor
            self.weight_growth *= norm_factor
            self.weight_quality *= norm_factor
            self.weight_momentum *= norm_factor

    def calculate_score(self,
                       fundamental_data: Dict[str, Any],
                       technical_data: Dict[str, Any],
                       price_data: List[Dict[str, Any]]) -> ScoreMetrics:
        """
        Calculate comprehensive composite score.

        Args:
            fundamental_data: Dict with fundamental metrics (PER, PBR, ROE, etc.)
            technical_data: Dict with technical indicators (RSI, MACD, etc.)
            price_data: List of price data dicts (for trend calculation)

        Returns:
            ScoreMetrics object with all calculated scores
        """
        metrics = ScoreMetrics()
        metrics.weight_value = self.weight_value
        metrics.weight_growth = self.weight_growth
        metrics.weight_quality = self.weight_quality
        metrics.weight_momentum = self.weight_momentum

        # Calculate component scores
        metrics.value_score = self._calculate_value_score(fundamental_data, metrics)
        metrics.growth_score = self._calculate_growth_score(fundamental_data, metrics)
        metrics.quality_score = self._calculate_quality_score(fundamental_data, metrics)
        metrics.momentum_score = self._calculate_momentum_score(technical_data, price_data, metrics)

        # Calculate composite score
        metrics.composite_score = self._calculate_composite_score(metrics)

        # Calculate data quality
        metrics.data_quality_score = self._calculate_data_quality(metrics)

        return metrics

    def _calculate_value_score(self, data: Dict[str, Any], metrics: ScoreMetrics) -> float:
        """
        Calculate value score based on valuation ratios.

        Lower PER/PBR/PSR and higher dividend yield indicate better value.

        Returns:
            Value score (0-100)
        """
        scores = []

        # PER Score: Lower is better (inverse scoring)
        # Excellent: < 10, Good: 10-15, Fair: 15-25, Poor: > 25
        per = data.get('per')
        if per is not None and per > 0:
            if per <= 10:
                metrics.per_score = 100.0
            elif per <= 15:
                metrics.per_score = 100.0 - ((per - 10) / 5) * 20  # 100-80
            elif per <= 25:
                metrics.per_score = 80.0 - ((per - 15) / 10) * 40  # 80-40
            else:
                metrics.per_score = max(0, 40.0 - ((per - 25) / 25) * 40)  # 40-0
            scores.append(metrics.per_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # PBR Score: Lower is better
        # Excellent: < 1, Good: 1-2, Fair: 2-3, Poor: > 3
        pbr = data.get('pbr')
        if pbr is not None and pbr > 0:
            if pbr <= 1.0:
                metrics.pbr_score = 100.0
            elif pbr <= 2.0:
                metrics.pbr_score = 100.0 - ((pbr - 1.0) / 1.0) * 30  # 100-70
            elif pbr <= 3.0:
                metrics.pbr_score = 70.0 - ((pbr - 2.0) / 1.0) * 40  # 70-30
            else:
                metrics.pbr_score = max(0, 30.0 - ((pbr - 3.0) / 2.0) * 30)  # 30-0
            scores.append(metrics.pbr_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # PSR Score: Lower is better
        # Excellent: < 1, Good: 1-2, Fair: 2-4, Poor: > 4
        psr = data.get('psr')
        if psr is not None and psr > 0:
            if psr <= 1.0:
                metrics.psr_score = 100.0
            elif psr <= 2.0:
                metrics.psr_score = 100.0 - ((psr - 1.0) / 1.0) * 30  # 100-70
            elif psr <= 4.0:
                metrics.psr_score = 70.0 - ((psr - 2.0) / 2.0) * 40  # 70-30
            else:
                metrics.psr_score = max(0, 30.0 - ((psr - 4.0) / 4.0) * 30)  # 30-0
            scores.append(metrics.psr_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # Dividend Yield Score: Higher is better
        # Excellent: > 5%, Good: 3-5%, Fair: 1-3%, Poor: < 1%
        div_yield = data.get('dividend_yield')
        if div_yield is not None and div_yield >= 0:
            if div_yield >= 5.0:
                metrics.dividend_yield_score = 100.0
            elif div_yield >= 3.0:
                metrics.dividend_yield_score = 80.0 + ((div_yield - 3.0) / 2.0) * 20  # 80-100
            elif div_yield >= 1.0:
                metrics.dividend_yield_score = 50.0 + ((div_yield - 1.0) / 2.0) * 30  # 50-80
            else:
                metrics.dividend_yield_score = div_yield * 50.0  # 0-50
            scores.append(metrics.dividend_yield_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # Return average of available scores
        return np.mean(scores) if scores else 0.0

    def _calculate_growth_score(self, data: Dict[str, Any], metrics: ScoreMetrics) -> float:
        """
        Calculate growth score based on growth rates.

        Higher growth rates indicate better performance.

        Returns:
            Growth score (0-100)
        """
        scores = []

        # Revenue Growth Score
        # Excellent: > 20%, Good: 10-20%, Fair: 0-10%, Poor: < 0%
        revenue_growth = data.get('revenue_growth')
        if revenue_growth is not None:
            if revenue_growth >= 20.0:
                metrics.revenue_growth_score = 100.0
            elif revenue_growth >= 10.0:
                metrics.revenue_growth_score = 80.0 + ((revenue_growth - 10.0) / 10.0) * 20  # 80-100
            elif revenue_growth >= 0.0:
                metrics.revenue_growth_score = 50.0 + ((revenue_growth) / 10.0) * 30  # 50-80
            else:
                # Negative growth
                metrics.revenue_growth_score = max(0, 50.0 + (revenue_growth / 20.0) * 50)  # 0-50
            scores.append(metrics.revenue_growth_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # Earnings Growth Score
        # Excellent: > 25%, Good: 15-25%, Fair: 5-15%, Poor: < 5%
        earnings_growth = data.get('earnings_growth')
        if earnings_growth is not None:
            if earnings_growth >= 25.0:
                metrics.earnings_growth_score = 100.0
            elif earnings_growth >= 15.0:
                metrics.earnings_growth_score = 80.0 + ((earnings_growth - 15.0) / 10.0) * 20  # 80-100
            elif earnings_growth >= 5.0:
                metrics.earnings_growth_score = 50.0 + ((earnings_growth - 5.0) / 10.0) * 30  # 50-80
            elif earnings_growth >= 0.0:
                metrics.earnings_growth_score = 30.0 + ((earnings_growth) / 5.0) * 20  # 30-50
            else:
                # Negative growth
                metrics.earnings_growth_score = max(0, 30.0 + (earnings_growth / 30.0) * 30)  # 0-30
            scores.append(metrics.earnings_growth_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # Equity Growth Score
        # Excellent: > 15%, Good: 10-15%, Fair: 5-10%, Poor: < 5%
        equity_growth = data.get('equity_growth')
        if equity_growth is not None:
            if equity_growth >= 15.0:
                metrics.equity_growth_score = 100.0
            elif equity_growth >= 10.0:
                metrics.equity_growth_score = 80.0 + ((equity_growth - 10.0) / 5.0) * 20  # 80-100
            elif equity_growth >= 5.0:
                metrics.equity_growth_score = 50.0 + ((equity_growth - 5.0) / 5.0) * 30  # 50-80
            elif equity_growth >= 0.0:
                metrics.equity_growth_score = 30.0 + ((equity_growth) / 5.0) * 20  # 30-50
            else:
                # Negative growth
                metrics.equity_growth_score = max(0, 30.0 + (equity_growth / 15.0) * 30)  # 0-30
            scores.append(metrics.equity_growth_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        return np.mean(scores) if scores else 0.0

    def _calculate_quality_score(self, data: Dict[str, Any], metrics: ScoreMetrics) -> float:
        """
        Calculate quality score based on profitability and financial health.

        Higher ROE, margins, and lower debt indicate better quality.

        Returns:
            Quality score (0-100)
        """
        scores = []

        # ROE Score
        # Excellent: > 20%, Good: 15-20%, Fair: 10-15%, Poor: < 10%
        roe = data.get('roe')
        if roe is not None:
            if roe >= 20.0:
                metrics.roe_score = 100.0
            elif roe >= 15.0:
                metrics.roe_score = 80.0 + ((roe - 15.0) / 5.0) * 20  # 80-100
            elif roe >= 10.0:
                metrics.roe_score = 50.0 + ((roe - 10.0) / 5.0) * 30  # 50-80
            elif roe >= 0.0:
                metrics.roe_score = (roe / 10.0) * 50  # 0-50
            else:
                metrics.roe_score = 0.0
            scores.append(metrics.roe_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # Operating Margin Score
        # Excellent: > 20%, Good: 15-20%, Fair: 10-15%, Poor: < 10%
        op_margin = data.get('operating_margin')
        if op_margin is not None:
            if op_margin >= 20.0:
                metrics.operating_margin_score = 100.0
            elif op_margin >= 15.0:
                metrics.operating_margin_score = 80.0 + ((op_margin - 15.0) / 5.0) * 20  # 80-100
            elif op_margin >= 10.0:
                metrics.operating_margin_score = 50.0 + ((op_margin - 10.0) / 5.0) * 30  # 50-80
            elif op_margin >= 0.0:
                metrics.operating_margin_score = (op_margin / 10.0) * 50  # 0-50
            else:
                metrics.operating_margin_score = 0.0
            scores.append(metrics.operating_margin_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # Net Margin Score
        # Excellent: > 15%, Good: 10-15%, Fair: 5-10%, Poor: < 5%
        net_margin = data.get('net_margin')
        if net_margin is not None:
            if net_margin >= 15.0:
                metrics.net_margin_score = 100.0
            elif net_margin >= 10.0:
                metrics.net_margin_score = 80.0 + ((net_margin - 10.0) / 5.0) * 20  # 80-100
            elif net_margin >= 5.0:
                metrics.net_margin_score = 50.0 + ((net_margin - 5.0) / 5.0) * 30  # 50-80
            elif net_margin >= 0.0:
                metrics.net_margin_score = (net_margin / 5.0) * 50  # 0-50
            else:
                metrics.net_margin_score = 0.0
            scores.append(metrics.net_margin_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # Debt Ratio Score (inverse - lower is better)
        # Excellent: < 30%, Good: 30-50%, Fair: 50-70%, Poor: > 70%
        debt_ratio = data.get('debt_ratio')
        if debt_ratio is not None:
            if debt_ratio <= 30.0:
                metrics.debt_ratio_score = 100.0
            elif debt_ratio <= 50.0:
                metrics.debt_ratio_score = 100.0 - ((debt_ratio - 30.0) / 20.0) * 20  # 100-80
            elif debt_ratio <= 70.0:
                metrics.debt_ratio_score = 80.0 - ((debt_ratio - 50.0) / 20.0) * 40  # 80-40
            else:
                metrics.debt_ratio_score = max(0, 40.0 - ((debt_ratio - 70.0) / 30.0) * 40)  # 40-0
            scores.append(metrics.debt_ratio_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # Current Ratio Score
        # Excellent: > 2, Good: 1.5-2, Fair: 1-1.5, Poor: < 1
        current_ratio = data.get('current_ratio')
        if current_ratio is not None and current_ratio > 0:
            if current_ratio >= 2.0:
                metrics.current_ratio_score = 100.0
            elif current_ratio >= 1.5:
                metrics.current_ratio_score = 80.0 + ((current_ratio - 1.5) / 0.5) * 20  # 80-100
            elif current_ratio >= 1.0:
                metrics.current_ratio_score = 50.0 + ((current_ratio - 1.0) / 0.5) * 30  # 50-80
            else:
                metrics.current_ratio_score = current_ratio * 50.0  # 0-50
            scores.append(metrics.current_ratio_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        return np.mean(scores) if scores else 0.0

    def _calculate_momentum_score(self,
                                  technical_data: Dict[str, Any],
                                  price_data: List[Dict[str, Any]],
                                  metrics: ScoreMetrics) -> float:
        """
        Calculate momentum score based on technical indicators.

        Returns:
            Momentum score (0-100)
        """
        scores = []

        # RSI Score
        # Excellent: 50-70 (bullish but not overbought), Good: 40-80, Fair: 30-90, Poor: otherwise
        rsi = technical_data.get('rsi_14')
        if rsi is not None:
            if 50 <= rsi <= 70:
                metrics.rsi_score = 100.0
            elif 40 <= rsi <= 80:
                # Distance from optimal range
                if rsi < 50:
                    metrics.rsi_score = 80.0 + ((rsi - 40) / 10) * 20  # 80-100
                else:
                    metrics.rsi_score = 100.0 - ((rsi - 70) / 10) * 20  # 100-80
            elif 30 <= rsi <= 90:
                if rsi < 40:
                    metrics.rsi_score = 50.0 + ((rsi - 30) / 10) * 30  # 50-80
                else:
                    metrics.rsi_score = 80.0 - ((rsi - 80) / 10) * 30  # 80-50
            else:
                # Oversold or overbought
                if rsi < 30:
                    metrics.rsi_score = (rsi / 30) * 50  # 0-50
                else:
                    metrics.rsi_score = max(0, 50 - ((rsi - 90) / 10) * 50)  # 50-0
            scores.append(metrics.rsi_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # MACD Score
        # Positive MACD histogram = bullish, Negative = bearish
        macd_histogram = technical_data.get('macd_histogram')
        if macd_histogram is not None:
            # Normalize based on magnitude (assuming typical range of -5 to +5)
            if macd_histogram > 0:
                metrics.macd_score = min(100, 50 + (macd_histogram / 5.0) * 50)
            else:
                metrics.macd_score = max(0, 50 + (macd_histogram / 5.0) * 50)
            scores.append(metrics.macd_score)
            metrics.total_metric_count += 1
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # Price Trend Score (based on recent price data)
        if price_data and len(price_data) >= 20:
            try:
                # Calculate trend using linear regression on last 20 days
                recent_prices = price_data[-20:]
                closes = [p['close'] for p in recent_prices if 'close' in p]

                if len(closes) >= 10:
                    x = np.arange(len(closes))
                    slope, intercept, r_value, p_value, std_err = stats.linregress(x, closes)

                    # Normalize slope to percentage change per day
                    avg_price = np.mean(closes)
                    pct_change_per_day = (slope / avg_price) * 100

                    # Score based on trend strength
                    # Excellent: > +0.5% per day, Good: +0.2-0.5%, Fair: -0.2-0.2%, Poor: < -0.2%
                    if pct_change_per_day >= 0.5:
                        metrics.price_trend_score = 100.0
                    elif pct_change_per_day >= 0.2:
                        metrics.price_trend_score = 80.0 + ((pct_change_per_day - 0.2) / 0.3) * 20
                    elif pct_change_per_day >= -0.2:
                        metrics.price_trend_score = 50.0 + ((pct_change_per_day + 0.2) / 0.4) * 30
                    else:
                        metrics.price_trend_score = max(0, 50.0 + (pct_change_per_day / 0.5) * 50)

                    scores.append(metrics.price_trend_score)
                    metrics.total_metric_count += 1
                else:
                    metrics.missing_value_count += 1
                    metrics.total_metric_count += 1
            except Exception as e:
                logger.warning(f"Error calculating price trend: {e}")
                metrics.missing_value_count += 1
                metrics.total_metric_count += 1
                metrics.errors.append(f"Price trend calculation error: {str(e)}")
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        # Volume Trend Score
        if price_data and len(price_data) >= 20:
            try:
                recent_data = price_data[-20:]
                volumes = [p['volume'] for p in recent_data if 'volume' in p]

                if len(volumes) >= 10:
                    # Calculate volume trend
                    x = np.arange(len(volumes))
                    slope, intercept, r_value, p_value, std_err = stats.linregress(x, volumes)

                    # Positive volume trend with positive price trend is bullish
                    avg_volume = np.mean(volumes)
                    pct_change_per_day = (slope / avg_volume) * 100

                    # Score: Increasing volume is generally positive
                    if pct_change_per_day >= 1.0:
                        metrics.volume_trend_score = 100.0
                    elif pct_change_per_day >= 0.0:
                        metrics.volume_trend_score = 50.0 + (pct_change_per_day / 1.0) * 50
                    else:
                        metrics.volume_trend_score = max(0, 50.0 + (pct_change_per_day / 2.0) * 50)

                    scores.append(metrics.volume_trend_score)
                    metrics.total_metric_count += 1
                else:
                    metrics.missing_value_count += 1
                    metrics.total_metric_count += 1
            except Exception as e:
                logger.warning(f"Error calculating volume trend: {e}")
                metrics.missing_value_count += 1
                metrics.total_metric_count += 1
                metrics.errors.append(f"Volume trend calculation error: {str(e)}")
        else:
            metrics.missing_value_count += 1
            metrics.total_metric_count += 1

        return np.mean(scores) if scores else 0.0

    def _calculate_composite_score(self, metrics: ScoreMetrics) -> float:
        """
        Calculate overall composite score as weighted average.

        Args:
            metrics: ScoreMetrics object with component scores

        Returns:
            Composite score (0-100)
        """
        scores = []
        weights = []

        if metrics.value_score is not None:
            scores.append(metrics.value_score)
            weights.append(self.weight_value)

        if metrics.growth_score is not None:
            scores.append(metrics.growth_score)
            weights.append(self.weight_growth)

        if metrics.quality_score is not None:
            scores.append(metrics.quality_score)
            weights.append(self.weight_quality)

        if metrics.momentum_score is not None:
            scores.append(metrics.momentum_score)
            weights.append(self.weight_momentum)

        if not scores:
            return 0.0

        # Weighted average
        total_weight = sum(weights)
        if total_weight > 0:
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            return weighted_sum / total_weight
        else:
            return 0.0

    def _calculate_data_quality(self, metrics: ScoreMetrics) -> float:
        """
        Calculate data quality score based on completeness.

        Args:
            metrics: ScoreMetrics object

        Returns:
            Data quality score (0-100)
        """
        if metrics.total_metric_count == 0:
            return 0.0

        available_count = metrics.total_metric_count - metrics.missing_value_count
        quality_pct = (available_count / metrics.total_metric_count) * 100

        # Add warnings for low data quality
        if quality_pct < 50:
            metrics.notes = "Warning: Low data quality - many metrics missing"
        elif quality_pct < 75:
            metrics.notes = "Caution: Some metrics missing"

        return quality_pct
