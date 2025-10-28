"""
Paper Trading Executor.

Simulates order execution with realistic market behavior including:
- Price slippage based on order size and market conditions
- Partial fills for large orders
- Market impact simulation
- Realistic order status progression
"""
import logging
import random
import uuid
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.trading_engine.broker_interface import (
    BrokerInterface, Order, OrderRequest, OrderExecution, Position,
    OrderStatus, OrderSide, OrderType, TimeInForce
)
from services.trading_engine.commission_calculator import (
    CommissionCalculator, MarketType
)
from shared.database.models import Trade, Portfolio, StockPrice, Stock


logger = logging.getLogger(__name__)


class SlippageModel:
    """
    Slippage model for simulating realistic price slippage.

    Slippage factors:
    - Order size relative to average volume
    - Market volatility
    - Bid-ask spread
    - Market conditions
    """

    def __init__(
        self,
        base_slippage_bps: float = 5.0,      # Base slippage in basis points
        volume_impact_factor: float = 0.5,   # How much volume affects slippage
        volatility_impact_factor: float = 0.3  # How much volatility affects slippage
    ):
        """
        Initialize slippage model.

        Args:
            base_slippage_bps: Base slippage in basis points (1 bps = 0.01%)
            volume_impact_factor: Volume impact multiplier
            volatility_impact_factor: Volatility impact multiplier
        """
        self.base_slippage_bps = base_slippage_bps
        self.volume_impact_factor = volume_impact_factor
        self.volatility_impact_factor = volatility_impact_factor

    def calculate_slippage(
        self,
        order_price: float,
        order_quantity: int,
        side: OrderSide,
        avg_daily_volume: Optional[int] = None,
        volatility: Optional[float] = None
    ) -> float:
        """
        Calculate price slippage for an order.

        Args:
            order_price: Order price
            order_quantity: Order quantity
            side: Order side (buy/sell)
            avg_daily_volume: Average daily volume (optional)
            volatility: Price volatility (optional)

        Returns:
            Slippage amount (positive value, added to buy / subtracted from sell)
        """
        # Start with base slippage
        slippage_bps = self.base_slippage_bps

        # Add volume impact if available
        if avg_daily_volume and avg_daily_volume > 0:
            volume_ratio = order_quantity / avg_daily_volume
            # More slippage for larger orders relative to volume
            volume_impact_bps = volume_ratio * 100 * self.volume_impact_factor
            slippage_bps += volume_impact_bps

        # Add volatility impact if available
        if volatility:
            # Higher volatility = more slippage
            volatility_impact_bps = volatility * self.volatility_impact_factor
            slippage_bps += volatility_impact_bps

        # Add random component for realism (±20% of calculated slippage)
        random_factor = random.uniform(0.8, 1.2)
        slippage_bps *= random_factor

        # Convert basis points to price slippage
        slippage_amount = order_price * (slippage_bps / 10000)

        # Slippage is positive for buys (pay more) and negative for sells (receive less)
        if side == OrderSide.SELL:
            slippage_amount = -slippage_amount

        return slippage_amount


class PaperTradingExecutor(BrokerInterface):
    """
    Paper trading executor with realistic simulation.

    Simulates order execution without real money, including:
    - Realistic slippage
    - Order status progression
    - Portfolio tracking
    - Commission and tax calculation
    """

    def __init__(
        self,
        db: Session,
        user_id: str,
        initial_cash: float = 10000000.0,  # 10M KRW default
        market_type: MarketType = MarketType.KOSPI,
        enable_slippage: bool = True,
        slippage_model: Optional[SlippageModel] = None
    ):
        """
        Initialize paper trading executor.

        Args:
            db: Database session
            user_id: User identifier
            initial_cash: Initial cash balance
            market_type: Market type for commission calculation
            enable_slippage: Enable slippage simulation
            slippage_model: Custom slippage model (optional)
        """
        self.db = db
        self.user_id = user_id
        self.cash_balance = initial_cash
        self.initial_cash = initial_cash
        self.market_type = market_type

        # Commission calculator
        self.commission_calc = CommissionCalculator(market_type=market_type)

        # Slippage simulation
        self.enable_slippage = enable_slippage
        self.slippage_model = slippage_model or SlippageModel()

        # Order tracking (in-memory for paper trading)
        self.orders: Dict[str, Order] = {}

        logger.info(f"Paper Trading Executor initialized for user {user_id}")
        logger.info(f"Initial cash: {initial_cash:,.0f} KRW, Slippage: {enable_slippage}")

    def submit_order(self, order_request: OrderRequest) -> Order:
        """
        Submit an order for paper trading execution.

        Args:
            order_request: Order request details

        Returns:
            Order object with status

        Raises:
            ValueError: If order request is invalid
        """
        # Validate order request
        if not order_request.validate():
            raise ValueError("Invalid order request")

        # Generate order ID
        order_id = f"PAPER_{order_request.side.value.upper()}_{uuid.uuid4().hex[:12].upper()}"
        client_order_id = order_request.client_order_id or f"CLIENT_{uuid.uuid4().hex[:8]}"

        # Create order object
        order = Order(
            order_id=order_id,
            client_order_id=client_order_id,
            ticker=order_request.ticker,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            status=OrderStatus.PENDING,
            limit_price=order_request.limit_price,
            stop_price=order_request.stop_price,
            filled_quantity=0,
            avg_fill_price=None,
            executions=[],
            created_at=datetime.now(),
            time_in_force=order_request.time_in_force,
            notes=order_request.notes
        )

        # Store order
        self.orders[order_id] = order

        logger.info(f"Order submitted: {order_id} - {order_request.side.value.upper()} "
                   f"{order_request.quantity} {order_request.ticker} @ "
                   f"{order_request.limit_price or 'MARKET'}")

        # Process market orders immediately
        if order_request.order_type == OrderType.MARKET:
            self._execute_market_order(order)

        # Process limit orders if price is favorable
        elif order_request.order_type == OrderType.LIMIT:
            self._process_limit_order(order)

        return order

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an active order.

        Args:
            order_id: Order ID

        Returns:
            True if cancellation successful
        """
        order = self.orders.get(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False

        if not order.is_active:
            logger.error(f"Order {order_id} is not active (status: {order.status.value})")
            return False

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()

        logger.info(f"Order cancelled: {order_id}")
        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)

    def get_orders(
        self,
        ticker: Optional[str] = None,
        status: Optional[OrderStatus] = None
    ) -> List[Order]:
        """Get list of orders with optional filters."""
        orders = list(self.orders.values())

        if ticker:
            orders = [o for o in orders if o.ticker == ticker]

        if status:
            orders = [o for o in orders if o.status == status]

        return sorted(orders, key=lambda o: o.created_at, reverse=True)

    def get_position(self, ticker: str) -> Optional[Position]:
        """Get current position for a ticker."""
        portfolio = self.db.query(Portfolio).filter(
            Portfolio.user_id == self.user_id,
            Portfolio.ticker == ticker
        ).first()

        if not portfolio:
            return None

        current_price = self._get_current_price(ticker)
        if not current_price:
            current_price = float(portfolio.current_price or portfolio.avg_price)

        return Position(
            ticker=ticker,
            quantity=portfolio.quantity,
            avg_price=float(portfolio.avg_price),
            current_price=current_price
        )

    def get_positions(self) -> List[Position]:
        """Get all current positions."""
        portfolios = self.db.query(Portfolio).filter(
            Portfolio.user_id == self.user_id
        ).all()

        positions = []
        for portfolio in portfolios:
            current_price = self._get_current_price(portfolio.ticker)
            if not current_price:
                current_price = float(portfolio.current_price or portfolio.avg_price)

            positions.append(Position(
                ticker=portfolio.ticker,
                quantity=portfolio.quantity,
                avg_price=float(portfolio.avg_price),
                current_price=current_price
            ))

        return positions

    def get_account_balance(self) -> Dict[str, float]:
        """Get account balance information."""
        # Calculate portfolio value
        positions = self.get_positions()
        portfolio_value = sum(p.market_value for p in positions)

        total_value = self.cash_balance + portfolio_value
        equity = total_value

        return {
            'cash': self.cash_balance,
            'buying_power': self.cash_balance,  # Simplified (no margin)
            'portfolio_value': portfolio_value,
            'total_value': total_value,
            'equity': equity
        }

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current market price for a ticker."""
        return self._get_current_price(ticker)

    def _execute_market_order(self, order: Order):
        """Execute a market order immediately."""
        # Get current market price
        market_price = self._get_current_price(order.ticker)
        if not market_price:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = "Price not available"
            logger.error(f"Order {order.order_id} rejected: Price not available")
            return

        # Calculate slippage
        execution_price = market_price
        if self.enable_slippage:
            slippage = self._calculate_order_slippage(
                order.ticker, market_price, order.quantity, order.side
            )
            execution_price = market_price + slippage

            logger.debug(f"Order {order.order_id}: Market price {market_price:,.0f}, "
                        f"Slippage {slippage:,.2f}, Execution price {execution_price:,.0f}")

        # Check if we have sufficient funds/shares
        if not self._check_execution_feasibility(order, execution_price):
            order.status = OrderStatus.REJECTED
            order.rejection_reason = "Insufficient funds or shares"
            logger.error(f"Order {order.order_id} rejected: {order.rejection_reason}")
            return

        # Execute the order
        self._execute_order(order, execution_price, order.quantity)

    def _process_limit_order(self, order: Order):
        """
        Process a limit order.

        In paper trading, we immediately check if the limit price is favorable.
        """
        market_price = self._get_current_price(order.ticker)
        if not market_price:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = "Price not available"
            logger.error(f"Order {order.order_id} rejected: Price not available")
            return

        # Check if limit order can be filled
        can_fill = False
        if order.side == OrderSide.BUY and market_price <= order.limit_price:
            can_fill = True
        elif order.side == OrderSide.SELL and market_price >= order.limit_price:
            can_fill = True

        if can_fill:
            # Use limit price for execution (favorable to us)
            execution_price = order.limit_price

            if not self._check_execution_feasibility(order, execution_price):
                order.status = OrderStatus.REJECTED
                order.rejection_reason = "Insufficient funds or shares"
                logger.error(f"Order {order.order_id} rejected: {order.rejection_reason}")
                return

            self._execute_order(order, execution_price, order.quantity)
        else:
            # Order accepted but not filled yet
            order.status = OrderStatus.ACCEPTED
            order.submitted_at = datetime.now()
            logger.info(f"Limit order {order.order_id} accepted, waiting for price")

    def _execute_order(self, order: Order, execution_price: float, quantity: int):
        """
        Execute an order at a given price.

        Args:
            order: Order to execute
            execution_price: Execution price
            quantity: Quantity to execute
        """
        # Calculate commission and tax
        if order.side == OrderSide.BUY:
            costs = self.commission_calc.calculate_buy_costs(quantity, execution_price)
        else:
            costs = self.commission_calc.calculate_sell_costs(quantity, execution_price)

        # Create execution record
        execution = OrderExecution(
            execution_id=f"EXEC_{uuid.uuid4().hex[:12].upper()}",
            order_id=order.order_id,
            ticker=order.ticker,
            side=order.side,
            quantity=quantity,
            price=execution_price,
            timestamp=datetime.now(),
            commission=costs.commission,
            tax=costs.transaction_tax + costs.agri_fish_tax
        )

        # Update order
        order.executions.append(execution)
        order.filled_quantity += quantity

        # Calculate average fill price
        total_value = sum(e.quantity * e.price for e in order.executions)
        total_quantity = sum(e.quantity for e in order.executions)
        order.avg_fill_price = total_value / total_quantity if total_quantity > 0 else 0

        # Update order status
        if order.is_filled:
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.now()
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        order.updated_at = datetime.now()

        # Update portfolio and cash balance
        self._update_account(order, execution)

        # Save to database
        self._save_trade_to_db(order, execution, costs)

        logger.info(f"Order {order.order_id} executed: {quantity} @ {execution_price:,.0f}, "
                   f"Commission: {costs.commission:,.0f}, Tax: {costs.transaction_tax:,.0f}")

    def _check_execution_feasibility(self, order: Order, execution_price: float) -> bool:
        """Check if order can be executed (sufficient funds/shares)."""
        if order.side == OrderSide.BUY:
            # Check if we have enough cash
            costs = self.commission_calc.calculate_buy_costs(order.quantity, execution_price)
            required_cash = costs.net_amount

            if required_cash > self.cash_balance:
                logger.warning(f"Insufficient cash: Need {required_cash:,.0f}, "
                             f"Have {self.cash_balance:,.0f}")
                return False

        elif order.side == OrderSide.SELL:
            # Check if we have enough shares
            position = self.get_position(order.ticker)
            if not position or position.quantity < order.quantity:
                have_qty = position.quantity if position else 0
                logger.warning(f"Insufficient shares: Need {order.quantity}, Have {have_qty}")
                return False

        return True

    def _update_account(self, order: Order, execution: OrderExecution):
        """Update cash balance and portfolio."""
        if order.side == OrderSide.BUY:
            # Deduct cash (including fees)
            self.cash_balance -= execution.net_amount
            self._update_portfolio_on_buy(order, execution)
        else:
            # Add cash (minus fees)
            self.cash_balance += execution.net_amount
            self._update_portfolio_on_sell(order, execution)

        logger.debug(f"Cash balance updated: {self.cash_balance:,.0f} KRW")

    def _update_portfolio_on_buy(self, order: Order, execution: OrderExecution):
        """Update portfolio after buy execution."""
        position = self.db.query(Portfolio).filter(
            Portfolio.user_id == self.user_id,
            Portfolio.ticker == order.ticker
        ).first()

        if position:
            # Update existing position
            old_quantity = position.quantity
            old_avg_price = float(position.avg_price)
            new_quantity = execution.quantity
            new_price = execution.price

            total_quantity = old_quantity + new_quantity
            new_avg_price = (old_quantity * old_avg_price + new_quantity * new_price) / total_quantity

            position.quantity = total_quantity
            position.avg_price = Decimal(str(new_avg_price))
            position.current_price = Decimal(str(execution.price))
            position.invested_amount = int(total_quantity * new_avg_price)
            position.total_commission += int(execution.commission)
            position.total_tax += int(execution.tax)
            position.last_transaction_date = datetime.now()
            position.updated_at = datetime.now()

        else:
            # Create new position
            position = Portfolio(
                user_id=self.user_id,
                ticker=order.ticker,
                quantity=execution.quantity,
                avg_price=Decimal(str(execution.price)),
                current_price=Decimal(str(execution.price)),
                invested_amount=int(execution.quantity * execution.price),
                unrealized_pnl=0,
                unrealized_pnl_pct=0.0,
                realized_pnl=0,
                total_commission=int(execution.commission),
                total_tax=int(execution.tax),
                first_purchase_date=datetime.now(),
                last_transaction_date=datetime.now()
            )
            self.db.add(position)

        self.db.commit()
        logger.debug(f"Portfolio updated: {order.ticker} - {position.quantity} shares @ {position.avg_price:,.0f}")

    def _update_portfolio_on_sell(self, order: Order, execution: OrderExecution):
        """Update portfolio after sell execution."""
        position = self.db.query(Portfolio).filter(
            Portfolio.user_id == self.user_id,
            Portfolio.ticker == order.ticker
        ).first()

        if not position:
            logger.error(f"Position not found for {order.ticker}")
            return

        # Calculate P&L
        avg_price = float(position.avg_price)
        pnl = (execution.price - avg_price) * execution.quantity - execution.commission - execution.tax

        remaining_quantity = position.quantity - execution.quantity

        if remaining_quantity <= 0:
            # Full exit
            self.db.delete(position)
            logger.info(f"Position closed: {order.ticker}, P&L: {pnl:,.0f} KRW")
        else:
            # Partial exit
            position.quantity = remaining_quantity
            position.current_price = Decimal(str(execution.price))
            position.realized_pnl += int(pnl)
            position.total_commission += int(execution.commission)
            position.total_tax += int(execution.tax)
            position.last_transaction_date = datetime.now()
            position.updated_at = datetime.now()

        self.db.commit()

    def _save_trade_to_db(self, order: Order, execution: OrderExecution, costs):
        """Save trade execution to database."""
        trade = Trade(
            order_id=order.order_id,
            ticker=order.ticker,
            action="BUY" if order.side == OrderSide.BUY else "SELL",
            order_type=order.order_type.value.upper(),
            quantity=execution.quantity,
            price=Decimal(str(execution.price)),
            executed_price=Decimal(str(execution.price)),
            executed_quantity=execution.quantity,
            total_amount=int(costs.gross_amount),
            commission=int(costs.commission),
            tax=int(costs.transaction_tax + costs.agri_fish_tax),
            status="EXECUTED",
            reason=order.notes or "Paper trading execution",
            strategy="paper_trading",
            created_at=order.created_at,
            executed_at=execution.timestamp
        )

        self.db.add(trade)
        self.db.commit()

        logger.debug(f"Trade saved to database: {trade.order_id}")

    def _get_current_price(self, ticker: str) -> Optional[float]:
        """Get current market price from database."""
        stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            logger.warning(f"Stock not found: {ticker}")
            return None

        latest_price = self.db.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).order_by(StockPrice.date.desc()).first()

        if not latest_price:
            logger.warning(f"No price data for {ticker}")
            return None

        return float(latest_price.close)

    def _calculate_order_slippage(
        self,
        ticker: str,
        price: float,
        quantity: int,
        side: OrderSide
    ) -> float:
        """Calculate slippage for an order."""
        # Get average volume for the stock
        stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            # Use default slippage
            return self.slippage_model.calculate_slippage(price, quantity, side)

        # Get recent volume data
        recent_prices = self.db.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).order_by(StockPrice.date.desc()).limit(20).all()

        if not recent_prices:
            return self.slippage_model.calculate_slippage(price, quantity, side)

        # Calculate average volume
        avg_volume = sum(int(p.volume) for p in recent_prices) / len(recent_prices)

        # Calculate volatility (std dev of returns)
        if len(recent_prices) >= 2:
            returns = []
            for i in range(len(recent_prices) - 1):
                ret = (float(recent_prices[i].close) / float(recent_prices[i + 1].close) - 1) * 100
                returns.append(ret)
            volatility = (sum((r - sum(returns) / len(returns)) ** 2 for r in returns) / len(returns)) ** 0.5
        else:
            volatility = 1.0

        return self.slippage_model.calculate_slippage(
            price, quantity, side, avg_volume, volatility
        )
