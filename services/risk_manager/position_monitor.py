"""
Position Monitor Service - Actively monitors positions for stop-loss and take-profit triggers.
Generates sell orders when price thresholds are breached.
Implements trailing stop-loss that moves up as profit increases.
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.database.models import Portfolio, Trade, TechnicalIndicator, PortfolioRiskMetrics
from shared.database.connection import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExitSignal:
    """Exit signal for a position."""
    user_id: str
    ticker: str
    signal_type: str  # "stop_loss", "trailing_stop", "take_profit", "emergency_liquidation"
    current_price: float
    trigger_price: float
    quantity: int
    reason: str
    urgency: str  # "critical", "high", "normal"
    technical_signals: Optional[Dict] = None


@dataclass
class PositionMonitorResult:
    """Result of position monitoring."""
    positions_checked: int
    exit_signals: List[ExitSignal]
    trailing_stops_updated: int
    warnings: List[str]
    emergency_liquidation_triggered: bool


class PositionMonitor:
    """
    Monitors positions for exit conditions:
    - Individual stock stop-loss at -10%
    - Trailing stop-loss (moves up as profit increases)
    - Take-profit at +20% or based on technical signals
    - Emergency liquidation if portfolio loss exceeds 28%
    """

    def __init__(
        self,
        check_stop_loss: bool = True,
        check_trailing_stop: bool = True,
        check_take_profit: bool = True,
        check_emergency_liquidation: bool = True,
        emergency_liquidation_threshold: float = 28.0
    ):
        """
        Initialize position monitor.

        Args:
            check_stop_loss: Enable stop-loss checking
            check_trailing_stop: Enable trailing stop-loss checking
            check_take_profit: Enable take-profit checking
            check_emergency_liquidation: Enable emergency liquidation checking
            emergency_liquidation_threshold: Portfolio loss % threshold for emergency liquidation
        """
        self.check_stop_loss = check_stop_loss
        self.check_trailing_stop = check_trailing_stop
        self.check_take_profit = check_take_profit
        self.check_emergency_liquidation = check_emergency_liquidation
        self.emergency_liquidation_threshold = emergency_liquidation_threshold
        logger.info(f"Position Monitor initialized with emergency threshold: {emergency_liquidation_threshold}%")

    def monitor_positions(self, user_id: str, db: Session) -> PositionMonitorResult:
        """
        Monitor all positions for a user and generate exit signals.

        Args:
            user_id: User identifier
            db: Database session

        Returns:
            PositionMonitorResult with exit signals and updates
        """
        positions = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

        if not positions:
            logger.info(f"No positions to monitor for user {user_id}")
            return PositionMonitorResult(
                positions_checked=0,
                exit_signals=[],
                trailing_stops_updated=0,
                warnings=[],
                emergency_liquidation_triggered=False
            )

        exit_signals = []
        trailing_stops_updated = 0
        warnings = []
        emergency_liquidation_triggered = False

        # Check for emergency liquidation first
        if self.check_emergency_liquidation:
            should_liquidate, liquidation_reason = self._check_emergency_liquidation(user_id, db)
            if should_liquidate:
                emergency_liquidation_triggered = True
                # Generate exit signals for all positions
                for position in positions:
                    signal = ExitSignal(
                        user_id=user_id,
                        ticker=position.ticker,
                        signal_type="emergency_liquidation",
                        current_price=float(position.current_price or 0),
                        trigger_price=0.0,  # Market order
                        quantity=position.quantity,
                        reason=liquidation_reason,
                        urgency="critical"
                    )
                    exit_signals.append(signal)

                logger.critical(f"EMERGENCY LIQUIDATION TRIGGERED for user {user_id}: {liquidation_reason}")
                return PositionMonitorResult(
                    positions_checked=len(positions),
                    exit_signals=exit_signals,
                    trailing_stops_updated=0,
                    warnings=[liquidation_reason],
                    emergency_liquidation_triggered=True
                )

        # Monitor individual positions
        for position in positions:
            # Update trailing stop if needed
            if self.check_trailing_stop and position.trailing_stop_enabled:
                updated = self._update_trailing_stop(position, db)
                if updated:
                    trailing_stops_updated += 1

            # Check stop-loss
            if self.check_stop_loss:
                signal = self._check_stop_loss(position)
                if signal:
                    exit_signals.append(signal)
                    continue  # Don't check other conditions if stop-loss triggered

            # Check trailing stop-loss
            if self.check_trailing_stop:
                signal = self._check_trailing_stop_loss(position)
                if signal:
                    exit_signals.append(signal)
                    continue

            # Check take-profit
            if self.check_take_profit:
                signal = self._check_take_profit(position, db)
                if signal:
                    exit_signals.append(signal)

        # Commit any trailing stop updates
        if trailing_stops_updated > 0:
            db.commit()

        logger.info(f"Position monitoring complete for user {user_id}: "
                   f"{len(positions)} positions checked, {len(exit_signals)} exit signals, "
                   f"{trailing_stops_updated} trailing stops updated")

        return PositionMonitorResult(
            positions_checked=len(positions),
            exit_signals=exit_signals,
            trailing_stops_updated=trailing_stops_updated,
            warnings=warnings,
            emergency_liquidation_triggered=emergency_liquidation_triggered
        )

    def _check_emergency_liquidation(self, user_id: str, db: Session) -> Tuple[bool, str]:
        """
        Check if portfolio has exceeded emergency liquidation threshold.

        Returns:
            Tuple of (should_liquidate, reason)
        """
        # Get latest risk metrics
        latest_metrics = db.query(PortfolioRiskMetrics).filter(
            PortfolioRiskMetrics.user_id == user_id
        ).order_by(desc(PortfolioRiskMetrics.date)).first()

        if not latest_metrics:
            return False, ""

        # Check if loss exceeds threshold
        if latest_metrics.total_loss_from_initial_pct >= self.emergency_liquidation_threshold:
            reason = (
                f"Emergency liquidation: Portfolio loss of {latest_metrics.total_loss_from_initial_pct:.2f}% "
                f"exceeds {self.emergency_liquidation_threshold}% threshold. "
                f"Liquidating all positions to prevent further losses."
            )
            return True, reason

        return False, ""

    def _update_trailing_stop(self, position: Portfolio, db: Session) -> bool:
        """
        Update trailing stop-loss price if current price is higher than recorded highest.

        Args:
            position: Portfolio position
            db: Database session

        Returns:
            True if trailing stop was updated
        """
        if not position.current_price:
            return False

        current_price = float(position.current_price)
        highest_price = float(position.highest_price_since_purchase or position.avg_price)

        # Update highest price if current is higher
        if current_price > highest_price:
            position.highest_price_since_purchase = Decimal(str(current_price))

            # Calculate new trailing stop price
            # Trailing stop is N% below the highest price
            trailing_distance_pct = position.trailing_stop_distance_pct or 10.0
            new_trailing_stop = current_price * (1 - trailing_distance_pct / 100)

            # Only move trailing stop up, never down
            old_trailing_stop = float(position.trailing_stop_price or 0)
            if new_trailing_stop > old_trailing_stop:
                position.trailing_stop_price = Decimal(str(new_trailing_stop))
                position.updated_at = datetime.utcnow()

                logger.info(f"Trailing stop updated for {position.ticker}: "
                           f"Highest: {current_price:,.0f}, "
                           f"New trailing stop: {new_trailing_stop:,.0f} "
                           f"(was {old_trailing_stop:,.0f})")
                return True

        return False

    def _check_stop_loss(self, position: Portfolio) -> Optional[ExitSignal]:
        """
        Check if position has hit stop-loss price.

        Args:
            position: Portfolio position

        Returns:
            ExitSignal if stop-loss triggered, None otherwise
        """
        if not position.current_price or not position.stop_loss_price:
            return None

        current_price = float(position.current_price)
        stop_loss_price = float(position.stop_loss_price)

        if current_price <= stop_loss_price:
            loss_pct = ((current_price - float(position.avg_price)) / float(position.avg_price)) * 100
            reason = (
                f"Stop-loss triggered: Price {current_price:,.0f} <= Stop {stop_loss_price:,.0f} "
                f"(Loss: {loss_pct:.2f}%)"
            )

            return ExitSignal(
                user_id=position.user_id,
                ticker=position.ticker,
                signal_type="stop_loss",
                current_price=current_price,
                trigger_price=stop_loss_price,
                quantity=position.quantity,
                reason=reason,
                urgency="high"
            )

        return None

    def _check_trailing_stop_loss(self, position: Portfolio) -> Optional[ExitSignal]:
        """
        Check if position has hit trailing stop-loss price.

        Args:
            position: Portfolio position

        Returns:
            ExitSignal if trailing stop triggered, None otherwise
        """
        if not position.trailing_stop_enabled or not position.current_price:
            return None

        if not position.trailing_stop_price:
            return None

        current_price = float(position.current_price)
        trailing_stop_price = float(position.trailing_stop_price)

        if current_price <= trailing_stop_price:
            highest_price = float(position.highest_price_since_purchase or position.avg_price)
            profit_from_highest = ((highest_price - float(position.avg_price)) / float(position.avg_price)) * 100
            current_pnl_pct = float(position.unrealized_pnl_pct or 0)

            reason = (
                f"Trailing stop triggered: Price {current_price:,.0f} <= Trailing stop {trailing_stop_price:,.0f} "
                f"(Peak profit: {profit_from_highest:.2f}%, Current: {current_pnl_pct:.2f}%)"
            )

            return ExitSignal(
                user_id=position.user_id,
                ticker=position.ticker,
                signal_type="trailing_stop",
                current_price=current_price,
                trigger_price=trailing_stop_price,
                quantity=position.quantity,
                reason=reason,
                urgency="high"
            )

        return None

    def _check_take_profit(self, position: Portfolio, db: Session) -> Optional[ExitSignal]:
        """
        Check if position has hit take-profit price or technical signals.

        Args:
            position: Portfolio position
            db: Database session

        Returns:
            ExitSignal if take-profit triggered, None otherwise
        """
        if not position.current_price:
            return None

        current_price = float(position.current_price)
        current_pnl_pct = float(position.unrealized_pnl_pct or 0)

        # Check absolute take-profit price
        if position.take_profit_price:
            take_profit_price = float(position.take_profit_price)
            if current_price >= take_profit_price:
                reason = (
                    f"Take-profit triggered: Price {current_price:,.0f} >= Target {take_profit_price:,.0f} "
                    f"(Profit: {current_pnl_pct:.2f}%)"
                )

                return ExitSignal(
                    user_id=position.user_id,
                    ticker=position.ticker,
                    signal_type="take_profit",
                    current_price=current_price,
                    trigger_price=take_profit_price,
                    quantity=position.quantity,
                    reason=reason,
                    urgency="normal"
                )

        # Check technical signals if enabled
        if position.take_profit_use_technical:
            technical_signal = self._check_technical_take_profit_signals(position, db)
            if technical_signal:
                return technical_signal

        return None

    def _check_technical_take_profit_signals(
        self,
        position: Portfolio,
        db: Session
    ) -> Optional[ExitSignal]:
        """
        Check technical indicators for take-profit signals.

        Signals:
        - RSI > 70 (overbought)
        - MACD bearish crossover
        - Price above upper Bollinger Band
        - Price significantly above key moving averages

        Args:
            position: Portfolio position
            db: Database session

        Returns:
            ExitSignal if technical take-profit triggered, None otherwise
        """
        # Get latest technical indicators
        from shared.database.models import Stock
        stock = db.query(Stock).filter(Stock.ticker == position.ticker).first()
        if not stock:
            return None

        latest_tech = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_id == stock.id
        ).order_by(desc(TechnicalIndicator.date)).first()

        if not latest_tech:
            return None

        signals = []
        current_price = float(position.current_price)

        # RSI overbought check
        if latest_tech.rsi_14 and latest_tech.rsi_14 > 70:
            signals.append(f"RSI overbought ({latest_tech.rsi_14:.1f})")

        # MACD bearish divergence
        if latest_tech.macd and latest_tech.macd_signal and latest_tech.macd_histogram:
            if latest_tech.macd < latest_tech.macd_signal and latest_tech.macd_histogram < 0:
                signals.append("MACD bearish crossover")

        # Bollinger Band check
        if latest_tech.bollinger_upper and current_price > latest_tech.bollinger_upper:
            signals.append("Price above upper Bollinger Band")

        # Price vs moving averages - check if significantly above
        if latest_tech.sma_20:
            pct_above_sma20 = ((current_price - latest_tech.sma_20) / latest_tech.sma_20) * 100
            if pct_above_sma20 > 15:  # More than 15% above SMA20
                signals.append(f"Price {pct_above_sma20:.1f}% above SMA20")

        # Need at least 2 signals to trigger take-profit
        if len(signals) >= 2:
            current_pnl_pct = float(position.unrealized_pnl_pct or 0)
            reason = (
                f"Technical take-profit triggered: {', '.join(signals)} "
                f"(Profit: {current_pnl_pct:.2f}%)"
            )

            return ExitSignal(
                user_id=position.user_id,
                ticker=position.ticker,
                signal_type="take_profit",
                current_price=current_price,
                trigger_price=current_price,
                quantity=position.quantity,
                reason=reason,
                urgency="normal",
                technical_signals={
                    'rsi_14': latest_tech.rsi_14,
                    'macd': latest_tech.macd,
                    'macd_signal': latest_tech.macd_signal,
                    'macd_histogram': latest_tech.macd_histogram,
                    'bollinger_upper': latest_tech.bollinger_upper,
                    'signals': signals
                }
            )

        return None

    def initialize_position_limits(
        self,
        position: Portfolio,
        entry_price: float,
        stop_loss_pct: float = 10.0,
        take_profit_pct: float = 20.0,
        trailing_stop_enabled: bool = True,
        trailing_stop_distance_pct: float = 10.0
    ) -> Portfolio:
        """
        Initialize stop-loss and take-profit levels for a new position.

        Args:
            position: Portfolio position to initialize
            entry_price: Entry price (avg_price)
            stop_loss_pct: Stop-loss percentage (default -10%)
            take_profit_pct: Take-profit percentage (default +20%)
            trailing_stop_enabled: Enable trailing stop
            trailing_stop_distance_pct: Trailing stop distance from highest price

        Returns:
            Updated position
        """
        # Set stop-loss price
        stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        position.stop_loss_price = Decimal(str(stop_loss_price))
        position.stop_loss_pct = stop_loss_pct

        # Set take-profit price
        take_profit_price = entry_price * (1 + take_profit_pct / 100)
        position.take_profit_price = Decimal(str(take_profit_price))
        position.take_profit_pct = take_profit_pct

        # Initialize trailing stop
        position.trailing_stop_enabled = trailing_stop_enabled
        position.trailing_stop_distance_pct = trailing_stop_distance_pct
        position.highest_price_since_purchase = Decimal(str(entry_price))
        position.trailing_stop_price = Decimal(str(stop_loss_price))  # Start at same level as stop-loss

        logger.info(f"Position limits initialized for {position.ticker}:")
        logger.info(f"  Entry: {entry_price:,.0f}")
        logger.info(f"  Stop-loss: {stop_loss_price:,.0f} (-{stop_loss_pct}%)")
        logger.info(f"  Take-profit: {take_profit_price:,.0f} (+{take_profit_pct}%)")
        logger.info(f"  Trailing stop: Enabled={trailing_stop_enabled}, Distance={trailing_stop_distance_pct}%")

        return position


# Example usage
if __name__ == "__main__":
    monitor = PositionMonitor(
        check_stop_loss=True,
        check_trailing_stop=True,
        check_take_profit=True,
        check_emergency_liquidation=True,
        emergency_liquidation_threshold=28.0
    )

    db = SessionLocal()
    try:
        user_id = "user123"
        result = monitor.monitor_positions(user_id, db)

        print(f"Monitoring Result:")
        print(f"  Positions checked: {result.positions_checked}")
        print(f"  Exit signals: {len(result.exit_signals)}")
        print(f"  Trailing stops updated: {result.trailing_stops_updated}")
        print(f"  Emergency liquidation: {result.emergency_liquidation_triggered}")

        for signal in result.exit_signals:
            print(f"\nExit Signal:")
            print(f"  Ticker: {signal.ticker}")
            print(f"  Type: {signal.signal_type}")
            print(f"  Reason: {signal.reason}")
            print(f"  Urgency: {signal.urgency}")

    finally:
        db.close()
