"""
Broker API Interface.

Abstract interface for broker integration. This allows the trading system
to work with different brokers (paper trading, real brokers) using the same interface.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OrderSide(Enum):
    """Order side (buy/sell)."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order execution status."""
    PENDING = "pending"              # Order created, not yet submitted
    SUBMITTED = "submitted"          # Order submitted to broker
    ACCEPTED = "accepted"            # Order accepted by broker
    PARTIALLY_FILLED = "partially_filled"  # Order partially executed
    FILLED = "filled"                # Order completely filled
    CANCELLED = "cancelled"          # Order cancelled
    REJECTED = "rejected"            # Order rejected by broker
    EXPIRED = "expired"              # Order expired
    FAILED = "failed"                # Order failed due to error


class TimeInForce(Enum):
    """Time in force for orders."""
    DAY = "day"                      # Valid for the trading day
    GTC = "gtc"                      # Good till cancelled
    IOC = "ioc"                      # Immediate or cancel
    FOK = "fok"                      # Fill or kill


@dataclass
class OrderRequest:
    """Order request to be submitted to broker."""
    ticker: str
    side: OrderSide
    order_type: OrderType
    quantity: int

    # Price fields (depending on order type)
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    # Order parameters
    time_in_force: TimeInForce = TimeInForce.DAY

    # Metadata
    client_order_id: Optional[str] = None
    notes: Optional[str] = None

    def validate(self) -> bool:
        """Validate order request."""
        if self.quantity <= 0:
            return False

        if self.order_type == OrderType.LIMIT and not self.limit_price:
            return False

        if self.order_type in (OrderType.STOP_LOSS, OrderType.STOP_LIMIT) and not self.stop_price:
            return False

        if self.order_type == OrderType.STOP_LIMIT and not self.limit_price:
            return False

        return True


@dataclass
class OrderExecution:
    """Order execution details."""
    execution_id: str
    order_id: str
    ticker: str
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime
    commission: float = 0.0
    tax: float = 0.0

    @property
    def total_amount(self) -> float:
        """Total transaction amount."""
        return self.quantity * self.price

    @property
    def net_amount(self) -> float:
        """Net amount after fees."""
        if self.side == OrderSide.BUY:
            return self.total_amount + self.commission + self.tax
        else:
            return self.total_amount - self.commission - self.tax


@dataclass
class Order:
    """Order with full status and execution information."""
    order_id: str
    client_order_id: Optional[str]
    ticker: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    status: OrderStatus

    # Price information
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    # Execution information
    filled_quantity: int = 0
    avg_fill_price: Optional[float] = None
    executions: List[OrderExecution] = None

    # Timestamps
    created_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None

    # Metadata
    time_in_force: TimeInForce = TimeInForce.DAY
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None

    def __post_init__(self):
        if self.executions is None:
            self.executions = []

    @property
    def remaining_quantity(self) -> int:
        """Remaining unfilled quantity."""
        return self.quantity - self.filled_quantity

    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.filled_quantity >= self.quantity

    @property
    def is_active(self) -> bool:
        """Check if order is still active."""
        return self.status in (
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED
        )

    @property
    def total_commission(self) -> float:
        """Total commission from all executions."""
        return sum(e.commission for e in self.executions)

    @property
    def total_tax(self) -> float:
        """Total tax from all executions."""
        return sum(e.tax for e in self.executions)


@dataclass
class Position:
    """Current position in a security."""
    ticker: str
    quantity: int
    avg_price: float
    current_price: float

    @property
    def market_value(self) -> float:
        """Current market value."""
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        """Total cost basis."""
        return self.quantity * self.avg_price

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss."""
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized profit/loss percentage."""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100


class BrokerInterface(ABC):
    """
    Abstract interface for broker integration.

    This interface defines the methods that any broker implementation
    (paper trading, real broker API) must implement.
    """

    @abstractmethod
    def submit_order(self, order_request: OrderRequest) -> Order:
        """
        Submit an order to the broker.

        Args:
            order_request: Order request details

        Returns:
            Order object with broker order ID and status

        Raises:
            ValueError: If order request is invalid
            Exception: If order submission fails
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an active order.

        Args:
            order_id: Broker order ID

        Returns:
            True if cancellation successful, False otherwise
        """
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order status and details.

        Args:
            order_id: Broker order ID

        Returns:
            Order object or None if not found
        """
        pass

    @abstractmethod
    def get_orders(
        self,
        ticker: Optional[str] = None,
        status: Optional[OrderStatus] = None
    ) -> List[Order]:
        """
        Get list of orders.

        Args:
            ticker: Filter by ticker (optional)
            status: Filter by status (optional)

        Returns:
            List of orders
        """
        pass

    @abstractmethod
    def get_position(self, ticker: str) -> Optional[Position]:
        """
        Get current position for a ticker.

        Args:
            ticker: Stock ticker

        Returns:
            Position object or None if no position
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """
        Get all current positions.

        Returns:
            List of positions
        """
        pass

    @abstractmethod
    def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance information.

        Returns:
            Dictionary with balance info:
            - cash: Available cash
            - buying_power: Available buying power
            - portfolio_value: Total portfolio value
            - equity: Total equity
        """
        pass

    @abstractmethod
    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current market price for a ticker.

        Args:
            ticker: Stock ticker

        Returns:
            Current price or None if not available
        """
        pass
