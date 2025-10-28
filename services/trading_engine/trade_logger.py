"""
Trade Logger.

Comprehensive logging system for trade execution with:
- Detailed trade information
- Performance metrics
- CSV export
- Trade journal functionality
"""
import logging
import csv
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import desc

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.database.models import Trade, Portfolio
from services.trading_engine.broker_interface import Order, OrderExecution


logger = logging.getLogger(__name__)


class TradeLogger:
    """
    Comprehensive trade logging system.

    Logs all trades with detailed information including:
    - Entry and exit details
    - P&L calculation
    - Commission and fees
    - Performance metrics
    """

    def __init__(
        self,
        db: Session,
        log_file_path: Optional[str] = None,
        enable_console_logging: bool = True
    ):
        """
        Initialize trade logger.

        Args:
            db: Database session
            log_file_path: Path to log file (optional)
            enable_console_logging: Enable console logging
        """
        self.db = db
        self.log_file_path = log_file_path
        self.enable_console_logging = enable_console_logging

        # Setup file logging if specified
        if self.log_file_path:
            self._setup_file_logging()

    def log_order_submitted(self, order: Order):
        """
        Log order submission.

        Args:
            order: Order object
        """
        log_msg = (
            f"ORDER SUBMITTED | {order.order_id} | "
            f"{order.ticker} | {order.side.value.upper()} | "
            f"{order.quantity} shares | {order.order_type.value.upper()} | "
            f"Price: {order.limit_price or 'MARKET'}"
        )

        self._log(log_msg, level="INFO")

        # Log to database
        self._save_log_to_db(
            order_id=order.order_id,
            ticker=order.ticker,
            action="ORDER_SUBMITTED",
            details=log_msg
        )

    def log_order_executed(self, order: Order, execution: OrderExecution):
        """
        Log order execution.

        Args:
            order: Order object
            execution: Execution details
        """
        log_msg = (
            f"ORDER EXECUTED | {order.order_id} | "
            f"{order.ticker} | {order.side.value.upper()} | "
            f"{execution.quantity} shares @ {execution.price:,.0f} KRW | "
            f"Commission: {execution.commission:,.0f} | "
            f"Tax: {execution.tax:,.0f} | "
            f"Net: {execution.net_amount:,.0f} KRW"
        )

        self._log(log_msg, level="INFO")

        # Log detailed execution info
        detailed_log = self._format_execution_details(order, execution)
        self._log(detailed_log, level="DEBUG")

        # Log to database
        self._save_log_to_db(
            order_id=order.order_id,
            ticker=order.ticker,
            action="ORDER_EXECUTED",
            details=detailed_log
        )

    def log_order_cancelled(self, order: Order, reason: str = ""):
        """
        Log order cancellation.

        Args:
            order: Order object
            reason: Cancellation reason
        """
        log_msg = (
            f"ORDER CANCELLED | {order.order_id} | "
            f"{order.ticker} | {order.side.value.upper()} | "
            f"Reason: {reason or 'User request'}"
        )

        self._log(log_msg, level="WARNING")

        self._save_log_to_db(
            order_id=order.order_id,
            ticker=order.ticker,
            action="ORDER_CANCELLED",
            details=log_msg
        )

    def log_order_rejected(self, order: Order, reason: str):
        """
        Log order rejection.

        Args:
            order: Order object
            reason: Rejection reason
        """
        log_msg = (
            f"ORDER REJECTED | {order.order_id} | "
            f"{order.ticker} | {order.side.value.upper()} | "
            f"Reason: {reason}"
        )

        self._log(log_msg, level="ERROR")

        self._save_log_to_db(
            order_id=order.order_id,
            ticker=order.ticker,
            action="ORDER_REJECTED",
            details=log_msg
        )

    def log_position_opened(self, ticker: str, quantity: int, avg_price: float):
        """
        Log position opening.

        Args:
            ticker: Stock ticker
            quantity: Quantity
            avg_price: Average price
        """
        log_msg = (
            f"POSITION OPENED | {ticker} | "
            f"{quantity} shares @ {avg_price:,.0f} KRW | "
            f"Total: {quantity * avg_price:,.0f} KRW"
        )

        self._log(log_msg, level="INFO")

        self._save_log_to_db(
            order_id=None,
            ticker=ticker,
            action="POSITION_OPENED",
            details=log_msg
        )

    def log_position_closed(
        self,
        ticker: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_pct: float
    ):
        """
        Log position closing with P&L.

        Args:
            ticker: Stock ticker
            quantity: Quantity
            entry_price: Entry price
            exit_price: Exit price
            pnl: Profit/loss in currency
            pnl_pct: Profit/loss percentage
        """
        pnl_sign = "+" if pnl >= 0 else ""
        log_msg = (
            f"POSITION CLOSED | {ticker} | "
            f"{quantity} shares | "
            f"Entry: {entry_price:,.0f} | Exit: {exit_price:,.0f} | "
            f"P&L: {pnl_sign}{pnl:,.0f} KRW ({pnl_sign}{pnl_pct:.2f}%)"
        )

        self._log(log_msg, level="INFO")

        self._save_log_to_db(
            order_id=None,
            ticker=ticker,
            action="POSITION_CLOSED",
            details=log_msg
        )

    def log_daily_summary(self, user_id: str):
        """
        Log daily trading summary.

        Args:
            user_id: User identifier
        """
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())

        # Get today's trades
        trades = self.db.query(Trade).filter(
            Trade.executed_at >= today_start
        ).all()

        if not trades:
            self._log("DAILY SUMMARY | No trades executed today", level="INFO")
            return

        # Calculate summary
        buy_trades = [t for t in trades if t.action == "BUY"]
        sell_trades = [t for t in trades if t.action == "SELL"]

        total_value = sum(t.total_amount for t in trades)
        total_commission = sum(t.commission for t in trades)
        total_tax = sum(t.tax for t in trades)

        # Calculate P&L from closed positions
        total_pnl = 0
        for sell_trade in sell_trades:
            # Find corresponding buy trade (simplified)
            buy_trade = next(
                (t for t in buy_trades if t.ticker == sell_trade.ticker),
                None
            )
            if buy_trade:
                pnl = (
                    (float(sell_trade.executed_price) - float(buy_trade.executed_price)) *
                    sell_trade.executed_quantity -
                    sell_trade.commission - sell_trade.tax -
                    buy_trade.commission - buy_trade.tax
                )
                total_pnl += pnl

        log_msg = (
            f"DAILY SUMMARY | {today} | "
            f"Trades: {len(trades)} ({len(buy_trades)} BUY, {len(sell_trades)} SELL) | "
            f"Total Value: {total_value:,.0f} KRW | "
            f"Commission: {total_commission:,.0f} | Tax: {total_tax:,.0f} | "
            f"P&L: {total_pnl:,.0f} KRW"
        )

        self._log(log_msg, level="INFO")

    def export_trades_to_csv(
        self,
        output_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ticker: Optional[str] = None
    ):
        """
        Export trades to CSV file.

        Args:
            output_path: Output file path
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            ticker: Ticker filter (optional)
        """
        # Query trades
        query = self.db.query(Trade)

        if start_date:
            query = query.filter(Trade.executed_at >= start_date)
        if end_date:
            query = query.filter(Trade.executed_at <= end_date)
        if ticker:
            query = query.filter(Trade.ticker == ticker)

        trades = query.order_by(Trade.executed_at).all()

        # Write to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Order ID', 'Ticker', 'Action', 'Order Type',
                'Quantity', 'Price', 'Executed Price', 'Executed Quantity',
                'Total Amount', 'Commission', 'Tax',
                'Status', 'Strategy', 'Reason',
                'Created At', 'Executed At'
            ])

            # Data
            for trade in trades:
                writer.writerow([
                    trade.order_id,
                    trade.ticker,
                    trade.action,
                    trade.order_type,
                    trade.quantity,
                    float(trade.price) if trade.price else '',
                    float(trade.executed_price) if trade.executed_price else '',
                    trade.executed_quantity,
                    trade.total_amount,
                    trade.commission,
                    trade.tax,
                    trade.status,
                    trade.strategy,
                    trade.reason,
                    trade.created_at.isoformat() if trade.created_at else '',
                    trade.executed_at.isoformat() if trade.executed_at else ''
                ])

        logger.info(f"Exported {len(trades)} trades to {output_path}")

    def get_trade_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get trade statistics.

        Args:
            start_date: Start date filter (optional)
            end_date: End date filter (optional)

        Returns:
            Dictionary with statistics
        """
        # Query trades
        query = self.db.query(Trade).filter(Trade.status == "EXECUTED")

        if start_date:
            query = query.filter(Trade.executed_at >= start_date)
        if end_date:
            query = query.filter(Trade.executed_at <= end_date)

        trades = query.all()

        if not trades:
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'total_volume': 0,
                'total_commission': 0,
                'total_tax': 0
            }

        buy_trades = [t for t in trades if t.action == "BUY"]
        sell_trades = [t for t in trades if t.action == "SELL"]

        return {
            'total_trades': len(trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'unique_tickers': len(set(t.ticker for t in trades)),
            'total_volume': sum(t.executed_quantity for t in trades if t.executed_quantity),
            'total_value': sum(t.total_amount for t in trades if t.total_amount),
            'total_commission': sum(t.commission for t in trades if t.commission),
            'total_tax': sum(t.tax for t in trades if t.tax),
            'avg_trade_size': sum(t.total_amount for t in trades if t.total_amount) / len(trades),
            'tickers': list(set(t.ticker for t in trades))
        }

    def _format_execution_details(self, order: Order, execution: OrderExecution) -> str:
        """Format detailed execution information."""
        details = [
            "=" * 80,
            f"Order Execution Details - {order.order_id}",
            "=" * 80,
            f"Ticker:           {order.ticker}",
            f"Side:             {order.side.value.upper()}",
            f"Order Type:       {order.order_type.value.upper()}",
            f"Quantity:         {execution.quantity:,} shares",
            f"Execution Price:  {execution.price:,.2f} KRW",
            f"Gross Amount:     {execution.total_amount:,.2f} KRW",
            f"Commission:       {execution.commission:,.2f} KRW",
            f"Tax:              {execution.tax:,.2f} KRW",
            f"Net Amount:       {execution.net_amount:,.2f} KRW",
            f"Execution Time:   {execution.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Execution ID:     {execution.execution_id}",
            "=" * 80
        ]
        return "\n".join(details)

    def _log(self, message: str, level: str = "INFO"):
        """Internal logging method."""
        if self.enable_console_logging:
            if level == "DEBUG":
                logger.debug(message)
            elif level == "INFO":
                logger.info(message)
            elif level == "WARNING":
                logger.warning(message)
            elif level == "ERROR":
                logger.error(message)

        if self.log_file_path:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] [{level}] {message}\n")

    def _save_log_to_db(
        self,
        order_id: Optional[str],
        ticker: str,
        action: str,
        details: str
    ):
        """Save log entry to database (optional, for audit trail)."""
        # This could save to a separate audit_log table if needed
        # For now, we just use the regular logging system
        pass

    def _setup_file_logging(self):
        """Setup file logging."""
        log_dir = Path(self.log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Write header if file doesn't exist
        if not Path(self.log_file_path).exists():
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                f.write(f"Trade Log - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
