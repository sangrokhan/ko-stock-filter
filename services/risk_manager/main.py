"""
Main entry point for Risk Manager Service.
Monitors and manages trading risk, position sizing, and exposure.
Enforces portfolio-level risk limits including maximum loss thresholds.
"""
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.database.connection import get_db, SessionLocal
from shared.database.models import Portfolio, Trade, PortfolioRiskMetrics

try:
    from services.risk_manager.position_sizing import PositionSizer, PositionSizingMethod
    from services.risk_manager.position_monitor import PositionMonitor
except ImportError:
    from position_sizing import PositionSizer, PositionSizingMethod
    from position_monitor import PositionMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RiskParameters:
    """Risk management parameters."""
    max_position_size: float  # Maximum position size as % of portfolio
    max_portfolio_risk: float  # Maximum portfolio risk as %
    max_drawdown: float  # Maximum allowable drawdown as %
    stop_loss_pct: float  # Stop loss percentage
    max_leverage: float  # Maximum leverage allowed
    max_total_loss: float  # Maximum total loss from initial capital as %


@dataclass
class PortfolioMetrics:
    """Portfolio metrics data class."""
    user_id: str
    total_value: int
    cash_balance: int
    invested_amount: int
    total_pnl: int
    total_pnl_pct: float
    realized_pnl: int
    unrealized_pnl: int
    current_drawdown: float
    peak_value: int
    initial_capital: int
    total_loss_from_initial_pct: float
    is_trading_halted: bool
    position_count: int
    largest_position_pct: float
    largest_position_ticker: Optional[str]
    positions: List[Dict]


@dataclass
class OrderValidationResult:
    """Result of order validation."""
    is_valid: bool
    reason: str
    warnings: List[str]
    suggested_quantity: Optional[int] = None


class RiskManagerService:
    """Service for managing trading risk with comprehensive portfolio monitoring."""

    def __init__(self, risk_params: Optional[RiskParameters] = None):
        """
        Initialize the risk manager service.

        Args:
            risk_params: Risk management parameters
        """
        self.running = False
        self.risk_params = risk_params or RiskParameters(
            max_position_size=10.0,
            max_portfolio_risk=2.0,
            max_drawdown=20.0,
            stop_loss_pct=5.0,
            max_leverage=1.0,
            max_total_loss=28.0  # 28% maximum loss limit (emergency liquidation threshold)
        )

        # Initialize position sizer with Kelly Criterion
        self.position_sizer = PositionSizer(
            default_method=PositionSizingMethod.KELLY_HALF,  # Conservative half-Kelly by default
            max_position_size_pct=self.risk_params.max_position_size,
            default_fixed_pct=5.0,
            default_risk_pct=self.risk_params.max_portfolio_risk
        )

        # Initialize position monitor
        self.position_monitor = PositionMonitor(
            check_stop_loss=True,
            check_trailing_stop=True,
            check_take_profit=True,
            check_emergency_liquidation=True,
            emergency_liquidation_threshold=self.risk_params.max_total_loss
        )

        logger.info("Risk Manager Service initialized with parameters:")
        logger.info(f"  Max Position Size: {self.risk_params.max_position_size}%")
        logger.info(f"  Max Portfolio Risk: {self.risk_params.max_portfolio_risk}%")
        logger.info(f"  Max Drawdown: {self.risk_params.max_drawdown}%")
        logger.info(f"  Max Total Loss: {self.risk_params.max_total_loss}%")
        logger.info(f"  Position Sizing: {self.position_sizer.default_method.value}")
        logger.info(f"  Stop-Loss: Individual -10%, Emergency {self.risk_params.max_total_loss}%")

    def start(self):
        """Start the risk manager service."""
        self.running = True
        logger.info("Risk Manager Service started")

    def stop(self):
        """Stop the risk manager service."""
        self.running = False
        logger.info("Risk Manager Service stopped")

    def calculate_portfolio_metrics(self, user_id: str, db: Session) -> PortfolioMetrics:
        """
        Calculate comprehensive portfolio metrics including P&L, drawdown, and position sizes.

        Args:
            user_id: User identifier
            db: Database session

        Returns:
            PortfolioMetrics with all calculated values
        """
        # Get all positions for the user
        positions = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

        if not positions:
            # Empty portfolio
            return PortfolioMetrics(
                user_id=user_id,
                total_value=0,
                cash_balance=0,
                invested_amount=0,
                total_pnl=0,
                total_pnl_pct=0.0,
                realized_pnl=0,
                unrealized_pnl=0,
                current_drawdown=0.0,
                peak_value=0,
                initial_capital=0,
                total_loss_from_initial_pct=0.0,
                is_trading_halted=False,
                position_count=0,
                largest_position_pct=0.0,
                largest_position_ticker=None,
                positions=[]
            )

        # Calculate portfolio totals
        total_current_value = sum(int(p.current_value or 0) for p in positions)
        total_invested = sum(int(p.invested_amount or 0) for p in positions)
        total_unrealized_pnl = sum(int(p.unrealized_pnl or 0) for p in positions)
        total_realized_pnl = sum(int(p.realized_pnl or 0) for p in positions)

        # Get latest risk metrics from database
        latest_risk_metrics = db.query(PortfolioRiskMetrics).filter(
            PortfolioRiskMetrics.user_id == user_id
        ).order_by(desc(PortfolioRiskMetrics.date)).first()

        # Determine cash balance, peak value, and initial capital
        if latest_risk_metrics:
            cash_balance = latest_risk_metrics.cash_balance or 0
            peak_value = latest_risk_metrics.peak_value or total_current_value
            initial_capital = latest_risk_metrics.initial_capital or total_invested
        else:
            cash_balance = 0
            peak_value = total_current_value
            initial_capital = total_invested

        # Update peak value if current is higher
        if total_current_value > peak_value:
            peak_value = total_current_value

        # Calculate total portfolio value (positions + cash)
        total_value = total_current_value + cash_balance

        # Calculate total P&L
        total_pnl = total_unrealized_pnl + total_realized_pnl
        total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0.0

        # Calculate current drawdown from peak
        current_drawdown = 0.0
        if peak_value > 0:
            current_drawdown = ((peak_value - total_value) / peak_value) * 100

        # Calculate total loss from initial capital
        total_loss_from_initial_pct = 0.0
        if initial_capital > 0 and total_value < initial_capital:
            total_loss_from_initial_pct = ((initial_capital - total_value) / initial_capital) * 100

        # Check if trading is halted
        is_trading_halted = (
            total_loss_from_initial_pct >= self.risk_params.max_total_loss or
            (latest_risk_metrics and latest_risk_metrics.is_trading_halted)
        )

        # Find largest position
        largest_position = None
        largest_position_value = 0
        for p in positions:
            if p.current_value and p.current_value > largest_position_value:
                largest_position_value = int(p.current_value)
                largest_position = p

        largest_position_pct = (largest_position_value / total_value * 100) if total_value > 0 else 0.0
        largest_position_ticker = largest_position.ticker if largest_position else None

        # Build position details
        position_details = []
        for p in positions:
            position_details.append({
                'ticker': p.ticker,
                'quantity': p.quantity,
                'avg_price': float(p.avg_price) if p.avg_price else 0.0,
                'current_price': float(p.current_price) if p.current_price else 0.0,
                'current_value': int(p.current_value or 0),
                'invested_amount': int(p.invested_amount or 0),
                'unrealized_pnl': int(p.unrealized_pnl or 0),
                'unrealized_pnl_pct': float(p.unrealized_pnl_pct or 0.0),
                'position_pct': (int(p.current_value or 0) / total_value * 100) if total_value > 0 else 0.0
            })

        return PortfolioMetrics(
            user_id=user_id,
            total_value=total_value,
            cash_balance=cash_balance,
            invested_amount=total_invested,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            realized_pnl=total_realized_pnl,
            unrealized_pnl=total_unrealized_pnl,
            current_drawdown=current_drawdown,
            peak_value=peak_value,
            initial_capital=initial_capital,
            total_loss_from_initial_pct=total_loss_from_initial_pct,
            is_trading_halted=is_trading_halted,
            position_count=len(positions),
            largest_position_pct=largest_position_pct,
            largest_position_ticker=largest_position_ticker,
            positions=position_details
        )

    def update_risk_metrics(self, metrics: PortfolioMetrics, db: Session) -> PortfolioRiskMetrics:
        """
        Update portfolio risk metrics in database.

        Args:
            metrics: Calculated portfolio metrics
            db: Database session

        Returns:
            Created or updated PortfolioRiskMetrics record
        """
        # Get latest metrics
        latest = db.query(PortfolioRiskMetrics).filter(
            PortfolioRiskMetrics.user_id == metrics.user_id
        ).order_by(desc(PortfolioRiskMetrics.date)).first()

        # Calculate daily P&L
        daily_pnl = 0
        daily_pnl_pct = 0.0
        if latest:
            previous_value = latest.total_value or 0
            daily_pnl = metrics.total_value - previous_value
            if previous_value > 0:
                daily_pnl_pct = (daily_pnl / previous_value) * 100

        # Calculate max drawdown
        max_drawdown = latest.max_drawdown if latest else 0.0
        if metrics.current_drawdown > max_drawdown:
            max_drawdown = metrics.current_drawdown

        # Calculate drawdown duration
        drawdown_duration_days = 0
        is_at_peak = metrics.total_value >= metrics.peak_value
        if not is_at_peak and latest:
            if latest.is_at_peak:
                drawdown_duration_days = 1
            else:
                drawdown_duration_days = (latest.drawdown_duration_days or 0) + 1

        # Check for trading halt
        is_trading_halted = metrics.is_trading_halted
        trading_halt_reason = None
        trading_halt_timestamp = None

        if is_trading_halted:
            if not (latest and latest.is_trading_halted):
                # New halt
                trading_halt_timestamp = datetime.utcnow()
                if metrics.total_loss_from_initial_pct >= self.risk_params.max_total_loss:
                    trading_halt_reason = (
                        f"Portfolio loss of {metrics.total_loss_from_initial_pct:.2f}% "
                        f"exceeds maximum loss limit of {self.risk_params.max_total_loss}%"
                    )
                    logger.critical(f"TRADING HALTED for user {metrics.user_id}: {trading_halt_reason}")
            else:
                # Preserve existing halt info
                trading_halt_reason = latest.trading_halt_reason
                trading_halt_timestamp = latest.trading_halt_timestamp

        # Calculate win rate and profit factor from trade history
        win_rate = None
        profit_factor = None
        trades = db.query(Trade).filter(
            Trade.status == "EXECUTED"
        ).all()

        if trades:
            winning_trades = sum(1 for t in trades if (t.action == "SELL" and
                                                       t.total_amount and t.quantity and
                                                       t.executed_price))
            total_trades = len(trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        # Generate risk warnings
        risk_warnings = []
        if metrics.current_drawdown > self.risk_params.max_drawdown:
            risk_warnings.append(f"Current drawdown {metrics.current_drawdown:.2f}% exceeds limit {self.risk_params.max_drawdown}%")
        if metrics.largest_position_pct > self.risk_params.max_position_size:
            risk_warnings.append(
                f"Position {metrics.largest_position_ticker} ({metrics.largest_position_pct:.2f}%) "
                f"exceeds max position size {self.risk_params.max_position_size}%"
            )
        if metrics.total_loss_from_initial_pct > self.risk_params.max_total_loss * 0.8:
            risk_warnings.append(
                f"Total loss {metrics.total_loss_from_initial_pct:.2f}% approaching "
                f"maximum limit {self.risk_params.max_total_loss}%"
            )

        # Create new risk metrics record
        risk_metrics = PortfolioRiskMetrics(
            user_id=metrics.user_id,
            date=datetime.utcnow(),
            total_value=metrics.total_value,
            cash_balance=metrics.cash_balance,
            invested_amount=metrics.invested_amount,
            peak_value=metrics.peak_value,
            initial_capital=metrics.initial_capital,
            total_pnl=metrics.total_pnl,
            total_pnl_pct=metrics.total_pnl_pct,
            realized_pnl=metrics.realized_pnl,
            unrealized_pnl=metrics.unrealized_pnl,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            current_drawdown=metrics.current_drawdown,
            max_drawdown=max_drawdown,
            drawdown_duration_days=drawdown_duration_days,
            is_at_peak=is_at_peak,
            position_count=metrics.position_count,
            largest_position_pct=metrics.largest_position_pct,
            largest_position_ticker=metrics.largest_position_ticker,
            total_exposure_pct=(metrics.invested_amount / metrics.total_value * 100) if metrics.total_value > 0 else 0.0,
            total_loss_from_initial=metrics.initial_capital - metrics.total_value if metrics.total_value < metrics.initial_capital else 0,
            total_loss_from_initial_pct=metrics.total_loss_from_initial_pct,
            total_loss_from_peak=metrics.peak_value - metrics.total_value if metrics.total_value < metrics.peak_value else 0,
            total_loss_from_peak_pct=metrics.current_drawdown,
            max_position_size_limit=self.risk_params.max_position_size,
            max_loss_limit=self.risk_params.max_total_loss,
            is_trading_halted=is_trading_halted,
            trading_halt_reason=trading_halt_reason,
            trading_halt_timestamp=trading_halt_timestamp,
            risk_warnings="; ".join(risk_warnings) if risk_warnings else None,
            win_rate=win_rate,
            profit_factor=profit_factor
        )

        db.add(risk_metrics)
        db.commit()
        db.refresh(risk_metrics)

        logger.info(f"Risk metrics updated for user {metrics.user_id}")
        logger.info(f"  Total Value: {metrics.total_value:,} KRW")
        logger.info(f"  Total P&L: {metrics.total_pnl:,} KRW ({metrics.total_pnl_pct:.2f}%)")
        logger.info(f"  Current Drawdown: {metrics.current_drawdown:.2f}%")
        logger.info(f"  Loss from Initial: {metrics.total_loss_from_initial_pct:.2f}%")
        logger.info(f"  Trading Halted: {is_trading_halted}")

        return risk_metrics

    def validate_order(self, order: Dict, user_id: str, db: Session) -> OrderValidationResult:
        """
        Validate if an order meets risk criteria.

        Args:
            order: Order details with keys: ticker, side, quantity, price
            user_id: User identifier
            db: Database session

        Returns:
            OrderValidationResult with validation status and details
        """
        warnings = []

        # Calculate current portfolio metrics
        metrics = self.calculate_portfolio_metrics(user_id, db)

        # Check if trading is halted
        if metrics.is_trading_halted:
            return OrderValidationResult(
                is_valid=False,
                reason=f"Trading is halted due to {self.risk_params.max_total_loss}% loss limit reached. "
                       f"Current loss: {metrics.total_loss_from_initial_pct:.2f}%",
                warnings=warnings
            )

        # For sell orders, always allow (risk reduction)
        if order.get('side') == 'SELL':
            return OrderValidationResult(
                is_valid=True,
                reason="Sell order approved (risk reduction)",
                warnings=warnings
            )

        # For buy orders, check position size limits
        ticker = order.get('ticker')
        quantity = order.get('quantity', 0)
        price = order.get('price', 0)
        order_value = quantity * price

        # Check if portfolio has enough value
        if metrics.total_value == 0:
            return OrderValidationResult(
                is_valid=False,
                reason="Portfolio has no value",
                warnings=warnings
            )

        # Calculate position size as % of portfolio
        new_position_pct = (order_value / metrics.total_value) * 100

        # Check if adding to existing position
        existing_position = db.query(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.ticker == ticker
        ).first()

        if existing_position:
            existing_value = int(existing_position.current_value or 0)
            total_position_value = existing_value + order_value
            new_position_pct = (total_position_value / metrics.total_value) * 100

        # Check against max position size
        if new_position_pct > self.risk_params.max_position_size:
            # Calculate suggested quantity
            max_position_value = metrics.total_value * (self.risk_params.max_position_size / 100)
            existing_value = int(existing_position.current_value) if existing_position else 0
            available_for_order = max(0, max_position_value - existing_value)
            suggested_quantity = int(available_for_order / price) if price > 0 else 0

            return OrderValidationResult(
                is_valid=False,
                reason=(
                    f"Position size {new_position_pct:.2f}% exceeds maximum "
                    f"{self.risk_params.max_position_size}% limit"
                ),
                warnings=warnings,
                suggested_quantity=suggested_quantity
            )

        # Check cash availability (if tracked)
        if metrics.cash_balance > 0 and order_value > metrics.cash_balance:
            warnings.append(f"Order value {order_value:,} KRW exceeds cash balance {metrics.cash_balance:,} KRW")

        # Check drawdown
        if metrics.current_drawdown > self.risk_params.max_drawdown * 0.9:
            warnings.append(
                f"Current drawdown {metrics.current_drawdown:.2f}% is near limit "
                f"{self.risk_params.max_drawdown}%"
            )

        # Check loss approaching limit
        if metrics.total_loss_from_initial_pct > self.risk_params.max_total_loss * 0.85:
            warnings.append(
                f"Total loss {metrics.total_loss_from_initial_pct:.2f}% approaching "
                f"maximum limit {self.risk_params.max_total_loss}%"
            )

        return OrderValidationResult(
            is_valid=True,
            reason="Order validated successfully",
            warnings=warnings
        )

    def calculate_position_size(
        self,
        ticker: str,
        entry_price: float,
        stop_loss_price: float,
        portfolio_value: float,
        method: Optional[PositionSizingMethod] = None,
        user_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict:
        """
        Calculate appropriate position size based on risk parameters and historical performance.
        Supports multiple methods including Kelly Criterion, fixed percent, and fixed risk.

        Args:
            ticker: Stock ticker
            entry_price: Entry price per share
            stop_loss_price: Stop loss price
            portfolio_value: Total portfolio value
            method: Position sizing method (defaults to Kelly Half)
            user_id: User identifier (for historical performance calculation)
            db: Database session (for historical performance calculation)

        Returns:
            Dictionary with shares, position_value, position_pct, method, and notes
        """
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share == 0:
            raise ValueError("Risk per share cannot be zero")

        # Get historical performance for Kelly Criterion
        win_rate = None
        avg_win_pct = None
        avg_loss_pct = None

        if user_id and db:
            # Get executed trades for the user
            trades = db.query(Trade).filter(
                Trade.status == "EXECUTED"
            ).all()

            if trades:
                # Convert to format needed by position sizer
                trade_data = []
                for trade in trades:
                    if trade.executed_price and trade.quantity:
                        # Simple P&L calculation (this is approximate)
                        # In a real system, you'd track entry/exit pairs
                        if trade.action == "SELL":
                            # Estimate P&L based on price movement
                            pnl_pct = ((float(trade.executed_price) - float(trade.price or trade.executed_price)) /
                                     float(trade.price or trade.executed_price) * 100)
                            trade_data.append({'pnl_pct': pnl_pct})

                if trade_data:
                    perf = self.position_sizer.get_historical_performance(trade_data)
                    win_rate = perf['win_rate']
                    avg_win_pct = perf['avg_win_pct']
                    avg_loss_pct = perf['avg_loss_pct']

        # Calculate position size using the position sizer
        try:
            result = self.position_sizer.calculate_position_size(
                portfolio_value=portfolio_value,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                method=method,
                win_rate=win_rate,
                avg_win_pct=avg_win_pct,
                avg_loss_pct=avg_loss_pct
            )

            logger.info(f"Position size calculated for {ticker}: "
                       f"{result.shares} shares ({result.position_pct:.2f}%) "
                       f"using {result.method}")

            return {
                'shares': result.shares,
                'position_value': result.position_value,
                'position_pct': result.position_pct,
                'method': result.method,
                'kelly_fraction': result.kelly_fraction,
                'risk_amount': result.risk_amount,
                'notes': result.notes
            }

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            # Fallback to simple fixed risk calculation
            max_risk_amount = portfolio_value * (self.risk_params.max_portfolio_risk / 100)
            shares = int(max_risk_amount / risk_per_share)
            max_position_value = portfolio_value * (self.risk_params.max_position_size / 100)
            max_shares = int(max_position_value / entry_price)
            shares = min(shares, max_shares)

            return {
                'shares': shares,
                'position_value': shares * entry_price,
                'position_pct': (shares * entry_price / portfolio_value * 100),
                'method': 'Fixed Risk (Fallback)',
                'kelly_fraction': None,
                'risk_amount': max_risk_amount,
                'notes': f'Fallback calculation due to error: {str(e)}'
            }

    def check_portfolio_risk(self, user_id: str, db: Session) -> Dict:
        """
        Check current portfolio risk metrics.

        Args:
            user_id: User identifier
            db: Database session

        Returns:
            Dictionary with risk metrics and status
        """
        metrics = self.calculate_portfolio_metrics(user_id, db)

        risk_status = {
            'status': 'OK',
            'metrics': {
                'total_value': metrics.total_value,
                'total_pnl': metrics.total_pnl,
                'total_pnl_pct': metrics.total_pnl_pct,
                'current_drawdown': metrics.current_drawdown,
                'total_loss_from_initial_pct': metrics.total_loss_from_initial_pct,
                'position_count': metrics.position_count,
                'largest_position_pct': metrics.largest_position_pct,
                'is_trading_halted': metrics.is_trading_halted
            },
            'limits': {
                'max_position_size': self.risk_params.max_position_size,
                'max_drawdown': self.risk_params.max_drawdown,
                'max_total_loss': self.risk_params.max_total_loss
            },
            'violations': [],
            'warnings': []
        }

        # Check for violations
        if metrics.is_trading_halted:
            risk_status['status'] = 'HALTED'
            risk_status['violations'].append(
                f"Trading halted: Loss {metrics.total_loss_from_initial_pct:.2f}% "
                f"exceeds {self.risk_params.max_total_loss}% limit"
            )

        if metrics.current_drawdown > self.risk_params.max_drawdown:
            risk_status['status'] = 'WARNING'
            risk_status['violations'].append(
                f"Drawdown {metrics.current_drawdown:.2f}% exceeds {self.risk_params.max_drawdown}% limit"
            )

        if metrics.largest_position_pct > self.risk_params.max_position_size:
            if risk_status['status'] == 'OK':
                risk_status['status'] = 'WARNING'
            risk_status['violations'].append(
                f"Position {metrics.largest_position_ticker} at {metrics.largest_position_pct:.2f}% "
                f"exceeds {self.risk_params.max_position_size}% limit"
            )

        # Add warnings
        if metrics.total_loss_from_initial_pct > self.risk_params.max_total_loss * 0.8:
            risk_status['warnings'].append(
                f"Total loss {metrics.total_loss_from_initial_pct:.2f}% approaching "
                f"{self.risk_params.max_total_loss}% limit"
            )

        if metrics.current_drawdown > self.risk_params.max_drawdown * 0.8:
            risk_status['warnings'].append(
                f"Drawdown {metrics.current_drawdown:.2f}% approaching "
                f"{self.risk_params.max_drawdown}% limit"
            )

        return risk_status

    def get_position_summary(self, user_id: str, db: Session) -> Dict:
        """
        Get summary of all positions with risk metrics.

        Args:
            user_id: User identifier
            db: Database session

        Returns:
            Dictionary with position summary
        """
        metrics = self.calculate_portfolio_metrics(user_id, db)

        return {
            'user_id': user_id,
            'portfolio_summary': {
                'total_value': metrics.total_value,
                'cash_balance': metrics.cash_balance,
                'invested_amount': metrics.invested_amount,
                'total_pnl': metrics.total_pnl,
                'total_pnl_pct': metrics.total_pnl_pct,
                'position_count': metrics.position_count
            },
            'risk_metrics': {
                'current_drawdown': metrics.current_drawdown,
                'peak_value': metrics.peak_value,
                'total_loss_from_initial_pct': metrics.total_loss_from_initial_pct,
                'largest_position_pct': metrics.largest_position_pct,
                'largest_position_ticker': metrics.largest_position_ticker,
                'is_trading_halted': metrics.is_trading_halted
            },
            'positions': metrics.positions
        }


if __name__ == "__main__":
    service = RiskManagerService()
    service.start()

    # Example usage
    db = SessionLocal()
    try:
        # Check portfolio risk for a user
        user_id = "user123"
        risk_status = service.check_portfolio_risk(user_id, db)
        print(f"Risk Status: {risk_status}")

        # Calculate and update metrics
        metrics = service.calculate_portfolio_metrics(user_id, db)
        service.update_risk_metrics(metrics, db)

        # Validate an order
        test_order = {
            'ticker': '005930',
            'side': 'BUY',
            'quantity': 10,
            'price': 70000
        }
        validation = service.validate_order(test_order, user_id, db)
        print(f"Order Validation: {validation}")

    finally:
        db.close()
