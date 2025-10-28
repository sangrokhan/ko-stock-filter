"""
Order Executor.

Generates and logs trade orders from trading signals.
Handles order creation, logging, and tracking.
"""
import logging
import uuid
from typing import Optional, Dict, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.database.models import Trade, Portfolio
from services.trading_engine.signal_generator import (
    TradingSignal, SignalType, OrderType
)

logger = logging.getLogger(__name__)


class OrderExecutor:
    """
    Executes trade orders from validated signals.

    Creates Trade records and updates Portfolio positions.
    In a production system, this would integrate with a broker API.
    """

    def __init__(
        self,
        db: Session,
        user_id: str,
        dry_run: bool = True
    ):
        """
        Initialize order executor.

        Args:
            db: Database session
            user_id: User identifier
            dry_run: If True, only log orders without execution
        """
        self.db = db
        self.user_id = user_id
        self.dry_run = dry_run

        logger.info(f"Order Executor initialized (dry_run={dry_run})")

    def execute_signal(self, signal: TradingSignal) -> Optional[Trade]:
        """
        Execute a trading signal.

        Args:
            signal: Validated trading signal

        Returns:
            Trade object if successful, None otherwise
        """
        if not signal.is_valid:
            logger.error(f"Cannot execute invalid signal: {signal.ticker}")
            return None

        try:
            if signal.signal_type == SignalType.ENTRY_BUY:
                return self._execute_buy_order(signal)
            elif signal.signal_type == SignalType.EXIT_SELL:
                return self._execute_sell_order(signal)
            else:
                logger.error(f"Unknown signal type: {signal.signal_type}")
                return None

        except Exception as e:
            logger.error(f"Error executing signal for {signal.ticker}: {e}", exc_info=True)
            return None

    def execute_signals_batch(self, signals: List[TradingSignal]) -> List[Trade]:
        """
        Execute a batch of signals.

        Args:
            signals: List of validated signals

        Returns:
            List of created Trade objects
        """
        trades = []

        for signal in signals:
            trade = self.execute_signal(signal)
            if trade:
                trades.append(trade)

        logger.info(f"Batch execution: {len(trades)}/{len(signals)} orders created")
        return trades

    def _execute_buy_order(self, signal: TradingSignal) -> Optional[Trade]:
        """Execute a buy order."""
        # Generate order ID
        order_id = f"BUY_{signal.ticker}_{uuid.uuid4().hex[:8].upper()}"

        # Calculate order details
        quantity = signal.recommended_shares
        price = signal.limit_price if signal.order_type == OrderType.LIMIT else signal.current_price
        total_amount = int(quantity * price)

        # Estimate commission and tax
        commission = int(total_amount * 0.00015)  # 0.015% commission
        tax = int(total_amount * 0.0023)  # 0.23% transaction tax

        # Create trade record
        trade = Trade(
            order_id=order_id,
            ticker=signal.ticker,
            action="BUY",
            order_type=signal.order_type.value.upper(),
            quantity=quantity,
            price=Decimal(str(price)),
            total_amount=total_amount,
            commission=commission,
            tax=tax,
            status="PENDING" if self.dry_run else "EXECUTED",
            reason="; ".join(signal.reasons),
            strategy="signal_generator",
            created_at=datetime.now()
        )

        if not self.dry_run:
            trade.executed_price = Decimal(str(signal.current_price))
            trade.executed_quantity = quantity
            trade.executed_at = datetime.now()
            trade.status = "EXECUTED"

            # Update or create portfolio position
            self._update_portfolio_on_buy(signal, trade)

        # Save to database
        self.db.add(trade)
        self.db.commit()

        logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}BUY order created: {signal.ticker} "
                   f"{quantity} shares @ {price:,.0f} = {total_amount:,.0f} KRW")

        return trade

    def _execute_sell_order(self, signal: TradingSignal) -> Optional[Trade]:
        """Execute a sell order."""
        # Generate order ID
        order_id = f"SELL_{signal.ticker}_{uuid.uuid4().hex[:8].upper()}"

        # Get existing position
        position = self.db.query(Portfolio).filter(
            Portfolio.user_id == self.user_id,
            Portfolio.ticker == signal.ticker
        ).first()

        if not position:
            logger.error(f"No position found for {signal.ticker}")
            return None

        # Calculate order details
        quantity = min(signal.recommended_shares, position.quantity)
        price = signal.limit_price if signal.order_type == OrderType.LIMIT else signal.current_price
        total_amount = int(quantity * price)

        # Estimate commission and tax
        commission = int(total_amount * 0.00015)  # 0.015% commission
        tax = int(total_amount * 0.0023)  # 0.23% transaction tax

        # Calculate P&L
        avg_price = float(position.avg_price)
        pnl = (price - avg_price) * quantity - commission - tax

        # Create trade record
        trade = Trade(
            order_id=order_id,
            ticker=signal.ticker,
            action="SELL",
            order_type=signal.order_type.value.upper(),
            quantity=quantity,
            price=Decimal(str(price)),
            total_amount=total_amount,
            commission=commission,
            tax=tax,
            status="PENDING" if self.dry_run else "EXECUTED",
            reason="; ".join(signal.reasons),
            strategy="signal_generator",
            created_at=datetime.now()
        )

        if not self.dry_run:
            trade.executed_price = Decimal(str(signal.current_price))
            trade.executed_quantity = quantity
            trade.executed_at = datetime.now()
            trade.status = "EXECUTED"

            # Update portfolio position
            self._update_portfolio_on_sell(signal, trade, position, pnl)

        # Save to database
        self.db.add(trade)
        self.db.commit()

        logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}SELL order created: {signal.ticker} "
                   f"{quantity} shares @ {price:,.0f} = {total_amount:,.0f} KRW (P&L: {pnl:,.0f})")

        return trade

    def _update_portfolio_on_buy(self, signal: TradingSignal, trade: Trade):
        """Update portfolio position after buy execution."""
        # Check if position exists
        position = self.db.query(Portfolio).filter(
            Portfolio.user_id == self.user_id,
            Portfolio.ticker == signal.ticker
        ).first()

        if position:
            # Update existing position (averaging)
            old_quantity = position.quantity
            old_avg_price = float(position.avg_price)
            new_quantity = trade.executed_quantity
            new_price = float(trade.executed_price)

            total_quantity = old_quantity + new_quantity
            new_avg_price = (old_quantity * old_avg_price + new_quantity * new_price) / total_quantity

            position.quantity = total_quantity
            position.avg_price = Decimal(str(new_avg_price))
            position.current_price = trade.executed_price
            position.invested_amount = int(total_quantity * new_avg_price)
            position.total_commission += trade.commission
            position.total_tax += trade.tax
            position.last_transaction_date = datetime.now()
            position.updated_at = datetime.now()

        else:
            # Create new position
            position = Portfolio(
                user_id=self.user_id,
                ticker=signal.ticker,
                quantity=trade.executed_quantity,
                avg_price=trade.executed_price,
                current_price=trade.executed_price,
                invested_amount=trade.total_amount,
                unrealized_pnl=0,
                unrealized_pnl_pct=0.0,
                realized_pnl=0,
                total_commission=trade.commission,
                total_tax=trade.tax,
                first_purchase_date=datetime.now(),
                last_transaction_date=datetime.now(),
                # Set stop-loss and take-profit
                stop_loss_price=Decimal(str(signal.stop_loss_price)) if signal.stop_loss_price else None,
                stop_loss_pct=10.0,
                take_profit_price=Decimal(str(signal.take_profit_price)) if signal.take_profit_price else None,
                take_profit_pct=20.0,
                trailing_stop_enabled=True,
                trailing_stop_distance_pct=10.0,
                highest_price_since_purchase=trade.executed_price,
                trailing_stop_price=Decimal(str(signal.stop_loss_price)) if signal.stop_loss_price else None
            )
            self.db.add(position)

        logger.info(f"Portfolio updated: {signal.ticker} position is now {position.quantity} shares @ {position.avg_price:,.0f}")

    def _update_portfolio_on_sell(
        self,
        signal: TradingSignal,
        trade: Trade,
        position: Portfolio,
        pnl: float
    ):
        """Update portfolio position after sell execution."""
        quantity_sold = trade.executed_quantity
        remaining_quantity = position.quantity - quantity_sold

        if remaining_quantity <= 0:
            # Full exit - remove position
            logger.info(f"Full exit: removing {signal.ticker} position")
            self.db.delete(position)
        else:
            # Partial exit - update position
            position.quantity = remaining_quantity
            position.current_price = trade.executed_price
            position.realized_pnl += int(pnl)
            position.total_commission += trade.commission
            position.total_tax += trade.tax
            position.last_transaction_date = datetime.now()
            position.updated_at = datetime.now()

            logger.info(f"Partial exit: {signal.ticker} position now {remaining_quantity} shares")

    def get_pending_orders(self) -> List[Trade]:
        """Get all pending orders."""
        return self.db.query(Trade).filter(
            Trade.status == "PENDING"
        ).order_by(Trade.created_at.desc()).all()

    def cancel_order(self, order_id: str, reason: str = "Manual cancellation") -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: Order ID to cancel
            reason: Cancellation reason

        Returns:
            True if successful
        """
        trade = self.db.query(Trade).filter(
            Trade.order_id == order_id,
            Trade.status == "PENDING"
        ).first()

        if not trade:
            logger.error(f"Pending order not found: {order_id}")
            return False

        trade.status = "CANCELLED"
        trade.reason = f"{trade.reason}; Cancelled: {reason}"
        trade.cancelled_at = datetime.now()
        trade.updated_at = datetime.now()

        self.db.commit()

        logger.info(f"Order cancelled: {order_id}")
        return True

    def get_execution_summary(self, trades: List[Trade]) -> Dict:
        """
        Get summary of trade executions.

        Args:
            trades: List of trades

        Returns:
            Dictionary with execution summary
        """
        if not trades:
            return {
                'total_trades': 0,
                'buy_orders': 0,
                'sell_orders': 0,
                'total_value': 0,
                'total_commission': 0,
                'total_tax': 0
            }

        buy_orders = [t for t in trades if t.action == "BUY"]
        sell_orders = [t for t in trades if t.action == "SELL"]

        return {
            'total_trades': len(trades),
            'buy_orders': len(buy_orders),
            'sell_orders': len(sell_orders),
            'total_value': sum(t.total_amount for t in trades),
            'total_commission': sum(t.commission for t in trades),
            'total_tax': sum(t.tax for t in trades),
            'tickers': list(set(t.ticker for t in trades))
        }
