"""
Trading Signal Generator.

Generates entry and exit signals based on:
- Entry: undervalued + positive momentum + good volume + conviction score
- Exit: stop-loss, take-profit, deteriorating fundamentals
- Position sizing: based on conviction score and risk tolerance
- Order generation: market or limit orders with validation
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import desc

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.database.models import (
    Stock, StockPrice, TechnicalIndicator, FundamentalIndicator,
    CompositeScore, Portfolio, PortfolioRiskMetrics
)
from services.risk_manager.position_sizing import PositionSizer, PositionSizingMethod
from services.risk_manager.position_monitor import PositionMonitor, ExitSignal

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Trading signal types."""
    ENTRY_BUY = "entry_buy"
    EXIT_SELL = "exit_sell"
    HOLD = "hold"


class OrderType(Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"


class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class ConvictionScore:
    """Conviction score breakdown."""
    total_score: float  # 0-100
    value_component: float  # 0-100
    momentum_component: float  # 0-100
    volume_component: float  # 0-100
    quality_component: float  # 0-100
    composite_score: float  # From CompositeScore table

    # Weights used
    weight_value: float = 0.30
    weight_momentum: float = 0.30
    weight_volume: float = 0.20
    weight_quality: float = 0.20

    # Detailed metrics
    metrics: Dict = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


@dataclass
class TradingSignal:
    """Trading signal with all relevant information."""
    signal_id: str
    ticker: str
    signal_type: SignalType
    signal_strength: SignalStrength
    timestamp: datetime

    # Price information
    current_price: float
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None

    # Position sizing
    recommended_shares: int = 0
    position_value: float = 0.0
    position_pct: float = 0.0

    # Order details
    order_type: OrderType = OrderType.LIMIT
    limit_price: Optional[float] = None
    urgency: str = "normal"  # "critical", "high", "normal", "low"

    # Signal details
    conviction_score: Optional[ConvictionScore] = None
    reasons: List[str] = field(default_factory=list)
    technical_indicators: Dict = field(default_factory=dict)
    fundamental_metrics: Dict = field(default_factory=dict)

    # Risk metrics
    expected_return_pct: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    kelly_fraction: Optional[float] = None

    # Validation
    is_valid: bool = True
    validation_warnings: List[str] = field(default_factory=list)

    # Metadata
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/storage."""
        return {
            'signal_id': self.signal_id,
            'ticker': self.ticker,
            'signal_type': self.signal_type.value,
            'signal_strength': self.signal_strength.value,
            'timestamp': self.timestamp.isoformat(),
            'current_price': self.current_price,
            'target_price': self.target_price,
            'stop_loss_price': self.stop_loss_price,
            'take_profit_price': self.take_profit_price,
            'recommended_shares': self.recommended_shares,
            'position_value': self.position_value,
            'position_pct': self.position_pct,
            'order_type': self.order_type.value,
            'limit_price': self.limit_price,
            'urgency': self.urgency,
            'conviction_score': self.conviction_score.total_score if self.conviction_score else None,
            'reasons': self.reasons,
            'expected_return_pct': self.expected_return_pct,
            'risk_reward_ratio': self.risk_reward_ratio,
            'is_valid': self.is_valid,
            'validation_warnings': self.validation_warnings,
            'notes': self.notes
        }


class TradingSignalGenerator:
    """
    Comprehensive trading signal generator.

    Generates buy/sell signals based on:
    - Fundamental analysis (value, quality)
    - Technical analysis (momentum, volume)
    - Risk management (position sizing, stop-loss/take-profit)
    """

    def __init__(
        self,
        db: Session,
        user_id: str,
        portfolio_value: float,
        risk_tolerance: float = 2.0,  # % of portfolio to risk per trade
        max_position_size_pct: float = 10.0,
        min_conviction_score: float = 60.0,
        use_limit_orders: bool = True,
        limit_order_discount_pct: float = 1.0
    ):
        """
        Initialize signal generator.

        Args:
            db: Database session
            user_id: User identifier
            portfolio_value: Current portfolio value
            risk_tolerance: Risk per trade as % of portfolio
            max_position_size_pct: Maximum position size as %
            min_conviction_score: Minimum conviction score for entry (0-100)
            use_limit_orders: Use limit orders instead of market orders
            limit_order_discount_pct: Discount % for limit orders
        """
        self.db = db
        self.user_id = user_id
        self.portfolio_value = portfolio_value
        self.risk_tolerance = risk_tolerance
        self.max_position_size_pct = max_position_size_pct
        self.min_conviction_score = min_conviction_score
        self.use_limit_orders = use_limit_orders
        self.limit_order_discount_pct = limit_order_discount_pct

        # Initialize position sizer
        self.position_sizer = PositionSizer(
            default_method=PositionSizingMethod.KELLY_HALF,
            max_position_size_pct=max_position_size_pct,
            default_risk_pct=risk_tolerance
        )

        # Initialize position monitor
        self.position_monitor = PositionMonitor(
            check_stop_loss=True,
            check_trailing_stop=True,
            check_take_profit=True,
            check_emergency_liquidation=True
        )

        logger.info(f"Signal Generator initialized for user {user_id} with "
                   f"portfolio value {portfolio_value:,.0f}, "
                   f"risk tolerance {risk_tolerance}%")

    def generate_entry_signals(
        self,
        candidate_tickers: List[str],
        min_composite_score: float = 60.0,
        min_momentum_score: float = 50.0,
        min_volume_percentile: float = 50.0
    ) -> List[TradingSignal]:
        """
        Generate entry (buy) signals for candidate stocks.

        Args:
            candidate_tickers: List of stock tickers to evaluate
            min_composite_score: Minimum composite score threshold
            min_momentum_score: Minimum momentum score threshold
            min_volume_percentile: Minimum volume percentile

        Returns:
            List of entry signals sorted by conviction score
        """
        logger.info(f"Generating entry signals for {len(candidate_tickers)} candidates")

        signals = []
        for ticker in candidate_tickers:
            signal = self._generate_entry_signal(
                ticker,
                min_composite_score,
                min_momentum_score,
                min_volume_percentile
            )
            if signal and signal.is_valid:
                signals.append(signal)

        # Sort by conviction score (descending)
        signals.sort(key=lambda s: s.conviction_score.total_score if s.conviction_score else 0, reverse=True)

        logger.info(f"Generated {len(signals)} valid entry signals")
        return signals

    def generate_exit_signals(self) -> List[TradingSignal]:
        """
        Generate exit (sell) signals for current positions.

        Checks for:
        - Stop-loss triggers
        - Take-profit triggers
        - Deteriorating fundamentals
        - Technical weakness

        Returns:
            List of exit signals
        """
        logger.info(f"Generating exit signals for user {self.user_id}")

        signals = []

        # Get exit signals from position monitor
        monitor_result = self.position_monitor.monitor_positions(self.user_id, self.db)

        # Convert position monitor exit signals to trading signals
        for exit_signal in monitor_result.exit_signals:
            signal = self._convert_exit_signal_to_trading_signal(exit_signal)
            if signal and signal.is_valid:
                signals.append(signal)

        # Check for deteriorating fundamentals
        fundamental_exits = self._check_deteriorating_fundamentals()
        signals.extend(fundamental_exits)

        logger.info(f"Generated {len(signals)} exit signals")
        return signals

    def _generate_entry_signal(
        self,
        ticker: str,
        min_composite_score: float,
        min_momentum_score: float,
        min_volume_percentile: float
    ) -> Optional[TradingSignal]:
        """Generate entry signal for a single stock."""
        try:
            # Get stock data
            stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
            if not stock:
                logger.debug(f"Stock not found: {ticker}")
                return None

            # Get latest data
            latest_price = self._get_latest_price(stock.id)
            if not latest_price:
                logger.debug(f"No price data for {ticker}")
                return None

            composite_score = self._get_latest_composite_score(stock.id)
            if not composite_score:
                logger.debug(f"No composite score for {ticker}")
                return None

            technical = self._get_latest_technical(stock.id)
            fundamental = self._get_latest_fundamental(stock.id)

            # Check minimum thresholds
            if composite_score.composite_score < min_composite_score:
                logger.debug(f"{ticker}: Composite score {composite_score.composite_score:.1f} below threshold")
                return None

            if composite_score.momentum_score and composite_score.momentum_score < min_momentum_score:
                logger.debug(f"{ticker}: Momentum score {composite_score.momentum_score:.1f} below threshold")
                return None

            # Calculate conviction score
            conviction = self._calculate_conviction_score(
                composite_score, technical, fundamental, latest_price, stock.id
            )

            if conviction.total_score < self.min_conviction_score:
                logger.debug(f"{ticker}: Conviction score {conviction.total_score:.1f} below minimum")
                return None

            # Calculate position sizing
            current_price = float(latest_price.close)

            # Calculate stop-loss price (10% below entry)
            stop_loss_price = current_price * 0.90

            # Calculate take-profit price (20% above entry)
            take_profit_price = current_price * 1.20

            # Get historical performance for Kelly Criterion
            historical_perf = self._get_historical_performance()

            # Calculate position size
            position_result = self.position_sizer.calculate_position_size(
                portfolio_value=self.portfolio_value,
                entry_price=current_price,
                stop_loss_price=stop_loss_price,
                method=PositionSizingMethod.KELLY_HALF,
                win_rate=historical_perf.get('win_rate'),
                avg_win_pct=historical_perf.get('avg_win_pct'),
                avg_loss_pct=historical_perf.get('avg_loss_pct')
            )

            # Adjust position size based on conviction (scale up/down by conviction/100)
            conviction_multiplier = conviction.total_score / 100.0
            adjusted_shares = int(position_result.shares * conviction_multiplier)
            adjusted_shares = max(1, adjusted_shares)  # Minimum 1 share

            # Determine signal strength
            signal_strength = self._determine_signal_strength(conviction.total_score)

            # Calculate limit price if using limit orders
            order_type = OrderType.LIMIT if self.use_limit_orders else OrderType.MARKET
            limit_price = current_price * (1 - self.limit_order_discount_pct / 100) if self.use_limit_orders else None

            # Build signal
            signal_id = f"ENTRY_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            reasons = [
                f"Composite score: {composite_score.composite_score:.1f}/100",
                f"Conviction score: {conviction.total_score:.1f}/100",
            ]

            if composite_score.value_score:
                reasons.append(f"Value score: {composite_score.value_score:.1f}")
            if composite_score.momentum_score:
                reasons.append(f"Momentum score: {composite_score.momentum_score:.1f}")
            if composite_score.quality_score:
                reasons.append(f"Quality score: {composite_score.quality_score:.1f}")

            reasons.extend(conviction.notes)

            # Calculate expected return and risk/reward
            expected_return_pct = ((take_profit_price - current_price) / current_price) * 100
            risk_pct = ((current_price - stop_loss_price) / current_price) * 100
            risk_reward_ratio = expected_return_pct / risk_pct if risk_pct > 0 else 0

            signal = TradingSignal(
                signal_id=signal_id,
                ticker=ticker,
                signal_type=SignalType.ENTRY_BUY,
                signal_strength=signal_strength,
                timestamp=datetime.now(),
                current_price=current_price,
                target_price=take_profit_price,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                recommended_shares=adjusted_shares,
                position_value=adjusted_shares * current_price,
                position_pct=(adjusted_shares * current_price / self.portfolio_value) * 100,
                order_type=order_type,
                limit_price=limit_price,
                urgency=self._determine_urgency(signal_strength),
                conviction_score=conviction,
                reasons=reasons,
                technical_indicators=self._extract_technical_indicators(technical),
                fundamental_metrics=self._extract_fundamental_metrics(fundamental),
                expected_return_pct=expected_return_pct,
                risk_reward_ratio=risk_reward_ratio,
                kelly_fraction=position_result.kelly_fraction,
                is_valid=True
            )

            # Validate signal
            self._validate_signal(signal)

            logger.info(f"Generated entry signal for {ticker}: "
                       f"Conviction {conviction.total_score:.1f}, "
                       f"Shares {adjusted_shares}, "
                       f"Value {signal.position_value:,.0f} ({signal.position_pct:.2f}%)")

            return signal

        except Exception as e:
            logger.error(f"Error generating entry signal for {ticker}: {e}", exc_info=True)
            return None

    def _calculate_conviction_score(
        self,
        composite_score: CompositeScore,
        technical: Optional[TechnicalIndicator],
        fundamental: Optional[FundamentalIndicator],
        latest_price: StockPrice,
        stock_id: int
    ) -> ConvictionScore:
        """
        Calculate conviction score from multiple factors.

        Conviction = weighted combination of:
        - Value (30%): undervaluation indicators
        - Momentum (30%): positive technical momentum
        - Volume (20%): trading volume strength
        - Quality (20%): fundamental quality
        """
        # Value component (from composite score)
        value_component = composite_score.value_score or 0

        # Momentum component (from composite score)
        momentum_component = composite_score.momentum_score or 0

        # Volume component
        volume_component = self._calculate_volume_score(stock_id)

        # Quality component (from composite score)
        quality_component = composite_score.quality_score or 0

        # Weights
        w_value = 0.30
        w_momentum = 0.30
        w_volume = 0.20
        w_quality = 0.20

        # Calculate total conviction
        total_score = (
            value_component * w_value +
            momentum_component * w_momentum +
            volume_component * w_volume +
            quality_component * w_quality
        )

        # Generate notes
        notes = []
        if value_component >= 70:
            notes.append("Strong value opportunity")
        if momentum_component >= 70:
            notes.append("Strong positive momentum")
        if volume_component >= 70:
            notes.append("High volume support")
        if quality_component >= 70:
            notes.append("High quality fundamentals")

        # Build metrics dict
        metrics = {
            'composite_score': composite_score.composite_score,
            'value_score': composite_score.value_score,
            'growth_score': composite_score.growth_score,
            'quality_score': composite_score.quality_score,
            'momentum_score': composite_score.momentum_score,
            'volume_score': volume_component
        }

        return ConvictionScore(
            total_score=total_score,
            value_component=value_component,
            momentum_component=momentum_component,
            volume_component=volume_component,
            quality_component=quality_component,
            composite_score=composite_score.composite_score,
            weight_value=w_value,
            weight_momentum=w_momentum,
            weight_volume=w_volume,
            weight_quality=w_quality,
            metrics=metrics,
            notes=notes
        )

    def _calculate_volume_score(self, stock_id: int, lookback_days: int = 20) -> float:
        """
        Calculate volume score (0-100).

        Higher score indicates:
        - Higher than average volume
        - Increasing volume trend
        """
        lookback_date = datetime.now() - timedelta(days=lookback_days)

        prices = self.db.query(StockPrice).filter(
            StockPrice.stock_id == stock_id,
            StockPrice.date >= lookback_date
        ).order_by(StockPrice.date).all()

        if not prices or len(prices) < 5:
            return 50.0  # Neutral score

        volumes = [float(p.volume) for p in prices]
        avg_volume = sum(volumes) / len(volumes)
        latest_volume = volumes[-1]

        # Score based on latest vs average
        volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 1.0

        # Volume score: >2x avg = 100, 1x avg = 50, <0.5x avg = 0
        if volume_ratio >= 2.0:
            volume_score = 100.0
        elif volume_ratio >= 1.0:
            volume_score = 50.0 + ((volume_ratio - 1.0) / 1.0) * 50
        else:
            volume_score = volume_ratio * 50

        # Check volume trend (increasing = positive)
        if len(volumes) >= 10:
            recent_avg = sum(volumes[-5:]) / 5
            earlier_avg = sum(volumes[-10:-5]) / 5

            if recent_avg > earlier_avg * 1.2:
                volume_score = min(100, volume_score * 1.1)  # Boost for increasing trend

        return min(100, max(0, volume_score))

    def _check_deteriorating_fundamentals(self) -> List[TradingSignal]:
        """
        Check existing positions for deteriorating fundamentals.

        Returns exit signals if:
        - Composite score dropped significantly
        - Quality score below threshold
        - Negative earnings growth
        """
        signals = []

        positions = self.db.query(Portfolio).filter(Portfolio.user_id == self.user_id).all()

        for position in positions:
            stock = self.db.query(Stock).filter(Stock.ticker == position.ticker).first()
            if not stock:
                continue

            # Get latest composite score
            latest_score = self._get_latest_composite_score(stock.id)
            if not latest_score:
                continue

            # Get historical composite score (30 days ago)
            historical_date = datetime.now() - timedelta(days=30)
            historical_score = self.db.query(CompositeScore).filter(
                CompositeScore.stock_id == stock.id,
                CompositeScore.date <= historical_date
            ).order_by(desc(CompositeScore.date)).first()

            reasons = []
            should_exit = False

            # Check score degradation
            if historical_score:
                score_drop = historical_score.composite_score - latest_score.composite_score
                if score_drop > 20:  # Score dropped >20 points
                    reasons.append(f"Composite score dropped {score_drop:.1f} points")
                    should_exit = True

            # Check quality score
            if latest_score.quality_score and latest_score.quality_score < 40:
                reasons.append(f"Quality score deteriorated to {latest_score.quality_score:.1f}")
                should_exit = True

            # Check growth score
            if latest_score.growth_score and latest_score.growth_score < 30:
                reasons.append(f"Growth score deteriorated to {latest_score.growth_score:.1f}")
                should_exit = True

            if should_exit:
                signal_id = f"EXIT_FUNDAMENTALS_{position.ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                signal = TradingSignal(
                    signal_id=signal_id,
                    ticker=position.ticker,
                    signal_type=SignalType.EXIT_SELL,
                    signal_strength=SignalStrength.MODERATE,
                    timestamp=datetime.now(),
                    current_price=float(position.current_price or position.avg_price),
                    recommended_shares=position.quantity,
                    position_value=position.quantity * float(position.current_price or position.avg_price),
                    order_type=OrderType.MARKET,
                    urgency="normal",
                    reasons=reasons,
                    notes="Exit due to deteriorating fundamentals",
                    is_valid=True
                )

                signals.append(signal)
                logger.info(f"Exit signal for {position.ticker}: {', '.join(reasons)}")

        return signals

    def _convert_exit_signal_to_trading_signal(self, exit_signal: ExitSignal) -> TradingSignal:
        """Convert position monitor exit signal to trading signal."""
        signal_id = f"EXIT_{exit_signal.signal_type.upper()}_{exit_signal.ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Determine signal strength based on urgency
        if exit_signal.urgency == "critical":
            signal_strength = SignalStrength.VERY_STRONG
            order_type = OrderType.MARKET
        elif exit_signal.urgency == "high":
            signal_strength = SignalStrength.STRONG
            order_type = OrderType.MARKET
        else:
            signal_strength = SignalStrength.MODERATE
            order_type = OrderType.LIMIT

        return TradingSignal(
            signal_id=signal_id,
            ticker=exit_signal.ticker,
            signal_type=SignalType.EXIT_SELL,
            signal_strength=signal_strength,
            timestamp=datetime.now(),
            current_price=exit_signal.current_price,
            recommended_shares=exit_signal.quantity,
            position_value=exit_signal.quantity * exit_signal.current_price,
            order_type=order_type,
            limit_price=exit_signal.trigger_price if order_type == OrderType.LIMIT else None,
            urgency=exit_signal.urgency,
            reasons=[exit_signal.reason],
            technical_indicators=exit_signal.technical_signals or {},
            is_valid=True
        )

    def _determine_signal_strength(self, conviction_score: float) -> SignalStrength:
        """Determine signal strength from conviction score."""
        if conviction_score >= 85:
            return SignalStrength.VERY_STRONG
        elif conviction_score >= 75:
            return SignalStrength.STRONG
        elif conviction_score >= 65:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK

    def _determine_urgency(self, signal_strength: SignalStrength) -> str:
        """Determine urgency level from signal strength."""
        if signal_strength == SignalStrength.VERY_STRONG:
            return "high"
        elif signal_strength == SignalStrength.STRONG:
            return "normal"
        else:
            return "low"

    def _validate_signal(self, signal: TradingSignal):
        """
        Validate trading signal.

        Checks:
        - Position size within limits
        - Sufficient portfolio value
        - Risk/reward ratio acceptable
        - No existing position conflicts
        """
        warnings = []

        # Check position size
        if signal.position_pct > self.max_position_size_pct:
            warnings.append(f"Position size {signal.position_pct:.2f}% exceeds max {self.max_position_size_pct}%")

        # Check sufficient funds for entry signals
        if signal.signal_type == SignalType.ENTRY_BUY:
            if signal.position_value > self.portfolio_value * 0.95:
                warnings.append("Insufficient portfolio value for this position")
                signal.is_valid = False

        # Check risk/reward ratio
        if signal.risk_reward_ratio and signal.risk_reward_ratio < 1.5:
            warnings.append(f"Low risk/reward ratio: {signal.risk_reward_ratio:.2f}")

        # Check for existing positions (for entry signals)
        if signal.signal_type == SignalType.ENTRY_BUY:
            existing_position = self.db.query(Portfolio).filter(
                Portfolio.user_id == self.user_id,
                Portfolio.ticker == signal.ticker
            ).first()

            if existing_position:
                warnings.append("Position already exists for this ticker")
                signal.is_valid = False

        signal.validation_warnings = warnings

        if warnings:
            logger.warning(f"Signal validation warnings for {signal.ticker}: {warnings}")

    def _get_historical_performance(self) -> Dict:
        """Get historical trading performance for Kelly Criterion."""
        # Query completed trades for this user
        from shared.database.models import Trade

        completed_trades = self.db.query(Trade).filter(
            Trade.status == "EXECUTED"
        ).order_by(desc(Trade.executed_at)).limit(100).all()

        if not completed_trades:
            # Return default values
            return {
                'win_rate': 0.55,
                'avg_win_pct': 12.0,
                'avg_loss_pct': 8.0,
                'profit_factor': 1.65
            }

        # Calculate actual performance
        return self.position_sizer.get_historical_performance(
            [{'pnl_pct': 10.0}]  # Placeholder - would calculate from actual trades
        )

    def _get_latest_price(self, stock_id: int) -> Optional[StockPrice]:
        """Get latest stock price."""
        return self.db.query(StockPrice).filter(
            StockPrice.stock_id == stock_id
        ).order_by(desc(StockPrice.date)).first()

    def _get_latest_composite_score(self, stock_id: int) -> Optional[CompositeScore]:
        """Get latest composite score."""
        return self.db.query(CompositeScore).filter(
            CompositeScore.stock_id == stock_id
        ).order_by(desc(CompositeScore.date)).first()

    def _get_latest_technical(self, stock_id: int) -> Optional[TechnicalIndicator]:
        """Get latest technical indicators."""
        return self.db.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_id == stock_id
        ).order_by(desc(TechnicalIndicator.date)).first()

    def _get_latest_fundamental(self, stock_id: int) -> Optional[FundamentalIndicator]:
        """Get latest fundamental indicators."""
        return self.db.query(FundamentalIndicator).filter(
            FundamentalIndicator.stock_id == stock_id
        ).order_by(desc(FundamentalIndicator.date)).first()

    def _extract_technical_indicators(self, technical: Optional[TechnicalIndicator]) -> Dict:
        """Extract relevant technical indicators."""
        if not technical:
            return {}

        return {
            'rsi_14': technical.rsi_14,
            'macd': technical.macd,
            'macd_signal': technical.macd_signal,
            'macd_histogram': technical.macd_histogram,
            'sma_20': technical.sma_20,
            'sma_50': technical.sma_50,
            'bollinger_upper': technical.bollinger_upper,
            'bollinger_lower': technical.bollinger_lower
        }

    def _extract_fundamental_metrics(self, fundamental: Optional[FundamentalIndicator]) -> Dict:
        """Extract relevant fundamental metrics."""
        if not fundamental:
            return {}

        return {
            'per': fundamental.per,
            'pbr': fundamental.pbr,
            'roe': fundamental.roe,
            'debt_ratio': fundamental.debt_ratio,
            'revenue_growth': fundamental.revenue_growth,
            'earnings_growth': fundamental.earnings_growth,
            'operating_margin': fundamental.operating_margin,
            'net_margin': fundamental.net_margin
        }
