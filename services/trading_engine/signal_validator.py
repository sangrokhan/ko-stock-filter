"""
Signal Validator.

Validates trading signals before execution:
- Data quality checks
- Risk limit checks
- Market condition checks
- Signal strength validation
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.database.models import (
    Stock, StockPrice, Portfolio, PortfolioRiskMetrics
)
from services.trading_engine.signal_generator import TradingSignal, SignalType

logger = logging.getLogger(__name__)


class SignalValidator:
    """
    Validates trading signals before execution.

    Performs comprehensive checks including:
    - Data quality and recency
    - Portfolio risk limits
    - Position concentration
    - Market conditions
    - Signal strength thresholds
    """

    def __init__(
        self,
        db: Session,
        user_id: str,
        max_positions: int = 20,
        max_concentration_pct: float = 30.0,
        max_sector_concentration_pct: float = 40.0,
        require_recent_data_hours: int = 48,
        min_data_quality_score: float = 75.0
    ):
        """
        Initialize signal validator.

        Args:
            db: Database session
            user_id: User identifier
            max_positions: Maximum number of concurrent positions
            max_concentration_pct: Max % in any single sector
            max_sector_concentration_pct: Max % in any sector
            require_recent_data_hours: Max age of data in hours
            min_data_quality_score: Minimum data quality score
        """
        self.db = db
        self.user_id = user_id
        self.max_positions = max_positions
        self.max_concentration_pct = max_concentration_pct
        self.max_sector_concentration_pct = max_sector_concentration_pct
        self.require_recent_data_hours = require_recent_data_hours
        self.min_data_quality_score = min_data_quality_score

        logger.info(f"Signal Validator initialized for user {user_id}")

    def validate_signal(self, signal: TradingSignal) -> Tuple[bool, List[str]]:
        """
        Validate a trading signal.

        Args:
            signal: Trading signal to validate

        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []

        # Run all validation checks
        if not self._check_data_quality(signal):
            errors.append("Data quality check failed")

        if not self._check_data_recency(signal):
            errors.append("Data is not recent enough")

        if signal.signal_type == SignalType.ENTRY_BUY:
            if not self._check_position_limits(signal):
                errors.append("Position limit check failed")

            if not self._check_concentration_limits(signal):
                errors.append("Concentration limit check failed")

            if not self._check_portfolio_capacity(signal):
                errors.append("Portfolio capacity check failed")

        if not self._check_risk_limits(signal):
            errors.append("Risk limit check failed")

        if not self._check_signal_strength(signal):
            errors.append("Signal strength insufficient")

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning(f"Signal validation failed for {signal.ticker}: {errors}")
        else:
            logger.info(f"Signal validated successfully for {signal.ticker}")

        return is_valid, errors

    def validate_signals_batch(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """
        Validate a batch of signals and return only valid ones.

        Args:
            signals: List of trading signals

        Returns:
            List of valid signals
        """
        valid_signals = []

        for signal in signals:
            is_valid, errors = self.validate_signal(signal)

            if is_valid:
                valid_signals.append(signal)
            else:
                signal.is_valid = False
                signal.validation_warnings.extend(errors)

        logger.info(f"Batch validation: {len(valid_signals)}/{len(signals)} signals valid")
        return valid_signals

    def _check_data_quality(self, signal: TradingSignal) -> bool:
        """Check if signal has sufficient data quality."""
        stock = self.db.query(Stock).filter(Stock.ticker == signal.ticker).first()
        if not stock:
            logger.warning(f"Stock not found: {signal.ticker}")
            return False

        # Check if we have composite score
        if signal.conviction_score:
            data_quality_score = signal.conviction_score.metrics.get('data_quality_score', 100)
            if data_quality_score < self.min_data_quality_score:
                logger.warning(f"{signal.ticker}: Data quality score {data_quality_score:.1f} below threshold")
                return False

        # Check for fundamental data
        if not signal.fundamental_metrics:
            logger.warning(f"{signal.ticker}: Missing fundamental metrics")
            return False

        # Check for technical data
        if not signal.technical_indicators:
            logger.warning(f"{signal.ticker}: Missing technical indicators")
            return False

        return True

    def _check_data_recency(self, signal: TradingSignal) -> bool:
        """Check if data is recent enough."""
        stock = self.db.query(Stock).filter(Stock.ticker == signal.ticker).first()
        if not stock:
            return False

        # Check price data recency
        latest_price = self.db.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).order_by(StockPrice.date.desc()).first()

        if not latest_price:
            logger.warning(f"{signal.ticker}: No price data found")
            return False

        max_age = timedelta(hours=self.require_recent_data_hours)
        data_age = datetime.now() - latest_price.date

        if data_age > max_age:
            logger.warning(f"{signal.ticker}: Price data is {data_age.days} days old")
            return False

        return True

    def _check_position_limits(self, signal: TradingSignal) -> bool:
        """Check if adding position would exceed limits."""
        # Count current positions
        current_positions = self.db.query(func.count(Portfolio.id)).filter(
            Portfolio.user_id == self.user_id
        ).scalar()

        if current_positions >= self.max_positions:
            logger.warning(f"Maximum positions ({self.max_positions}) reached")
            return False

        return True

    def _check_concentration_limits(self, signal: TradingSignal) -> bool:
        """Check if position would create excessive concentration."""
        # Get stock sector
        stock = self.db.query(Stock).filter(Stock.ticker == signal.ticker).first()
        if not stock or not stock.sector:
            return True  # Can't check if no sector info

        # Get all positions in same sector
        sector_positions = self.db.query(Portfolio).join(
            Stock, Portfolio.ticker == Stock.ticker
        ).filter(
            Portfolio.user_id == self.user_id,
            Stock.sector == stock.sector
        ).all()

        # Calculate current sector allocation
        total_portfolio_value = sum(
            float(p.current_value or 0) for p in self.db.query(Portfolio).filter(
                Portfolio.user_id == self.user_id
            ).all()
        )

        if total_portfolio_value == 0:
            return True

        sector_value = sum(float(p.current_value or 0) for p in sector_positions)
        new_sector_value = sector_value + signal.position_value
        new_sector_pct = (new_sector_value / total_portfolio_value) * 100

        if new_sector_pct > self.max_sector_concentration_pct:
            logger.warning(f"Sector concentration would be {new_sector_pct:.1f}% (max {self.max_sector_concentration_pct}%)")
            return False

        # Check single position concentration
        if signal.position_pct > self.max_concentration_pct:
            logger.warning(f"Position would be {signal.position_pct:.1f}% (max {self.max_concentration_pct}%)")
            return False

        return True

    def _check_portfolio_capacity(self, signal: TradingSignal) -> bool:
        """Check if portfolio has capacity for new position."""
        # Get current portfolio value and cash
        risk_metrics = self.db.query(PortfolioRiskMetrics).filter(
            PortfolioRiskMetrics.user_id == self.user_id
        ).order_by(PortfolioRiskMetrics.date.desc()).first()

        if not risk_metrics:
            # No risk metrics, assume we have capacity
            return True

        # Check if trading is halted
        if risk_metrics.is_trading_halted:
            logger.warning(f"Trading is halted: {risk_metrics.trading_halt_reason}")
            return False

        # Check if we have enough cash
        available_cash = risk_metrics.cash_balance or 0
        if signal.position_value > available_cash:
            logger.warning(f"Insufficient cash: need {signal.position_value:,.0f}, have {available_cash:,.0f}")
            return False

        return True

    def _check_risk_limits(self, signal: TradingSignal) -> bool:
        """Check if signal respects risk limits."""
        # Get latest risk metrics
        risk_metrics = self.db.query(PortfolioRiskMetrics).filter(
            PortfolioRiskMetrics.user_id == self.user_id
        ).order_by(PortfolioRiskMetrics.date.desc()).first()

        if not risk_metrics:
            return True  # No risk metrics, allow

        # Check if already at max drawdown
        if risk_metrics.current_drawdown >= 25.0:  # 25% drawdown
            logger.warning(f"Portfolio drawdown at {risk_metrics.current_drawdown:.1f}%")
            if signal.signal_type == SignalType.ENTRY_BUY:
                return False  # Don't add new positions during high drawdown

        # Check if approaching max loss limit
        if risk_metrics.total_loss_from_initial_pct >= 25.0:  # Approaching 30% limit
            logger.warning(f"Portfolio loss at {risk_metrics.total_loss_from_initial_pct:.1f}%")
            if signal.signal_type == SignalType.ENTRY_BUY:
                return False

        return True

    def _check_signal_strength(self, signal: TradingSignal) -> bool:
        """Check if signal meets minimum strength requirements."""
        # For entry signals, require at least moderate strength
        if signal.signal_type == SignalType.ENTRY_BUY:
            if signal.conviction_score and signal.conviction_score.total_score < 60.0:
                logger.warning(f"Signal strength too weak: {signal.conviction_score.total_score:.1f}")
                return False

        # Check risk/reward ratio
        if signal.risk_reward_ratio and signal.risk_reward_ratio < 1.5:
            logger.warning(f"Risk/reward ratio too low: {signal.risk_reward_ratio:.2f}")
            return False

        return True

    def get_validation_summary(self, signals: List[TradingSignal]) -> Dict:
        """
        Get summary of validation results.

        Args:
            signals: List of signals

        Returns:
            Dictionary with validation summary
        """
        total = len(signals)
        valid = len([s for s in signals if s.is_valid])
        invalid = total - valid

        # Count reasons for invalidity
        error_counts = {}
        for signal in signals:
            if not signal.is_valid:
                for warning in signal.validation_warnings:
                    error_counts[warning] = error_counts.get(warning, 0) + 1

        return {
            'total_signals': total,
            'valid_signals': valid,
            'invalid_signals': invalid,
            'validation_rate': (valid / total * 100) if total > 0 else 0,
            'error_breakdown': error_counts
        }
