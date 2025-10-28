"""
Commission and Fee Calculator for Korean Stock Market.

Calculates transaction costs including:
- Brokerage commission
- Securities transaction tax
- Other fees and charges

Korean market standard fees:
- Commission: ~0.015% (varies by broker)
- Transaction tax: 0.23% for sell orders only
- Agricultural/Fisheries tax: 0.15% on transaction tax
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class MarketType(Enum):
    """Korean stock market types."""
    KOSPI = "kospi"
    KOSDAQ = "kosdaq"
    KONEX = "konex"


@dataclass
class FeeStructure:
    """Fee structure configuration."""
    # Commission rates (as percentage, e.g., 0.015 = 0.015%)
    commission_rate: float = 0.015

    # Minimum commission per trade (KRW)
    min_commission: float = 0.0

    # Transaction tax rate (sell only)
    transaction_tax_rate: float = 0.23

    # Agricultural/Fisheries tax (on transaction tax)
    agri_fish_tax_rate: float = 0.15

    # Additional fees
    exchange_fee_rate: float = 0.0      # Exchange transaction fee
    clearing_fee_rate: float = 0.0      # Clearing fee

    def __post_init__(self):
        """Validate fee structure."""
        if self.commission_rate < 0:
            raise ValueError("Commission rate cannot be negative")
        if self.min_commission < 0:
            raise ValueError("Minimum commission cannot be negative")


@dataclass
class TransactionCosts:
    """Breakdown of transaction costs."""
    # Order details
    quantity: int
    price: float
    is_buy: bool

    # Cost components
    gross_amount: float           # quantity * price
    commission: float
    transaction_tax: float = 0.0
    agri_fish_tax: float = 0.0
    exchange_fee: float = 0.0
    clearing_fee: float = 0.0

    @property
    def total_fees(self) -> float:
        """Total fees and charges."""
        return (
            self.commission +
            self.transaction_tax +
            self.agri_fish_tax +
            self.exchange_fee +
            self.clearing_fee
        )

    @property
    def net_amount(self) -> float:
        """
        Net amount after fees.
        For buy: gross + fees (cash needed)
        For sell: gross - fees (cash received)
        """
        if self.is_buy:
            return self.gross_amount + self.total_fees
        else:
            return self.gross_amount - self.total_fees

    @property
    def effective_price(self) -> float:
        """
        Effective price per share including fees.
        For buy: higher than order price
        For sell: lower than order price
        """
        if self.quantity == 0:
            return 0.0
        return self.net_amount / self.quantity

    @property
    def fee_percentage(self) -> float:
        """Total fees as percentage of gross amount."""
        if self.gross_amount == 0:
            return 0.0
        return (self.total_fees / self.gross_amount) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            'quantity': self.quantity,
            'price': self.price,
            'is_buy': self.is_buy,
            'gross_amount': round(self.gross_amount, 2),
            'commission': round(self.commission, 2),
            'transaction_tax': round(self.transaction_tax, 2),
            'agri_fish_tax': round(self.agri_fish_tax, 2),
            'total_fees': round(self.total_fees, 2),
            'net_amount': round(self.net_amount, 2),
            'effective_price': round(self.effective_price, 2),
            'fee_percentage': round(self.fee_percentage, 4)
        }


class CommissionCalculator:
    """
    Calculator for Korean stock market transaction costs.

    Handles commission, taxes, and fees for KOSPI, KOSDAQ, and KONEX markets.
    """

    # Standard fee structures by market
    STANDARD_FEES = {
        MarketType.KOSPI: FeeStructure(
            commission_rate=0.015,
            min_commission=0.0,
            transaction_tax_rate=0.23,
            agri_fish_tax_rate=0.15
        ),
        MarketType.KOSDAQ: FeeStructure(
            commission_rate=0.015,
            min_commission=0.0,
            transaction_tax_rate=0.23,
            agri_fish_tax_rate=0.15
        ),
        MarketType.KONEX: FeeStructure(
            commission_rate=0.015,
            min_commission=0.0,
            transaction_tax_rate=0.10,  # Lower tax for KONEX
            agri_fish_tax_rate=0.15
        )
    }

    def __init__(
        self,
        market_type: MarketType = MarketType.KOSPI,
        custom_fee_structure: Optional[FeeStructure] = None
    ):
        """
        Initialize commission calculator.

        Args:
            market_type: Market type (KOSPI, KOSDAQ, KONEX)
            custom_fee_structure: Custom fee structure (overrides default)
        """
        self.market_type = market_type

        if custom_fee_structure:
            self.fee_structure = custom_fee_structure
        else:
            self.fee_structure = self.STANDARD_FEES[market_type]

    def calculate_buy_costs(
        self,
        quantity: int,
        price: float
    ) -> TransactionCosts:
        """
        Calculate costs for a buy order.

        Args:
            quantity: Number of shares
            price: Price per share

        Returns:
            TransactionCosts object with breakdown
        """
        gross_amount = quantity * price

        # Calculate commission
        commission = self._calculate_commission(gross_amount)

        # No transaction tax on buy orders
        transaction_tax = 0.0
        agri_fish_tax = 0.0

        # Additional fees (if any)
        exchange_fee = self._calculate_exchange_fee(gross_amount)
        clearing_fee = self._calculate_clearing_fee(gross_amount)

        return TransactionCosts(
            quantity=quantity,
            price=price,
            is_buy=True,
            gross_amount=gross_amount,
            commission=commission,
            transaction_tax=transaction_tax,
            agri_fish_tax=agri_fish_tax,
            exchange_fee=exchange_fee,
            clearing_fee=clearing_fee
        )

    def calculate_sell_costs(
        self,
        quantity: int,
        price: float
    ) -> TransactionCosts:
        """
        Calculate costs for a sell order.

        Args:
            quantity: Number of shares
            price: Price per share

        Returns:
            TransactionCosts object with breakdown
        """
        gross_amount = quantity * price

        # Calculate commission
        commission = self._calculate_commission(gross_amount)

        # Calculate transaction tax (sell only)
        transaction_tax = (gross_amount * self.fee_structure.transaction_tax_rate) / 100

        # Calculate agricultural/fisheries tax (on transaction tax)
        agri_fish_tax = (transaction_tax * self.fee_structure.agri_fish_tax_rate) / 100

        # Additional fees (if any)
        exchange_fee = self._calculate_exchange_fee(gross_amount)
        clearing_fee = self._calculate_clearing_fee(gross_amount)

        return TransactionCosts(
            quantity=quantity,
            price=price,
            is_buy=False,
            gross_amount=gross_amount,
            commission=commission,
            transaction_tax=transaction_tax,
            agri_fish_tax=agri_fish_tax,
            exchange_fee=exchange_fee,
            clearing_fee=clearing_fee
        )

    def calculate_round_trip_costs(
        self,
        quantity: int,
        buy_price: float,
        sell_price: float
    ) -> dict:
        """
        Calculate total costs for a round trip (buy + sell).

        Args:
            quantity: Number of shares
            buy_price: Buy price per share
            sell_price: Sell price per share

        Returns:
            Dictionary with buy costs, sell costs, and total
        """
        buy_costs = self.calculate_buy_costs(quantity, buy_price)
        sell_costs = self.calculate_sell_costs(quantity, sell_price)

        gross_pnl = (sell_price - buy_price) * quantity
        net_pnl = gross_pnl - buy_costs.total_fees - sell_costs.total_fees

        return {
            'buy_costs': buy_costs,
            'sell_costs': sell_costs,
            'total_fees': buy_costs.total_fees + sell_costs.total_fees,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'net_pnl_pct': (net_pnl / buy_costs.net_amount) * 100 if buy_costs.net_amount > 0 else 0,
            'breakeven_price': self.calculate_breakeven_price(buy_price)
        }

    def calculate_breakeven_price(self, buy_price: float) -> float:
        """
        Calculate breakeven sell price accounting for all fees.

        Args:
            buy_price: Original buy price

        Returns:
            Price needed to break even after fees
        """
        # Buy fees percentage
        buy_commission_pct = self.fee_structure.commission_rate / 100

        # Sell fees percentage (commission + tax + agri tax)
        sell_commission_pct = self.fee_structure.commission_rate / 100
        sell_tax_pct = self.fee_structure.transaction_tax_rate / 100
        sell_agri_tax_pct = (sell_tax_pct * self.fee_structure.agri_fish_tax_rate) / 100
        sell_total_pct = sell_commission_pct + sell_tax_pct + sell_agri_tax_pct

        # Breakeven = buy_price * (1 + buy_fees) / (1 - sell_fees)
        breakeven = buy_price * (1 + buy_commission_pct) / (1 - sell_total_pct)

        return breakeven

    def _calculate_commission(self, gross_amount: float) -> float:
        """Calculate brokerage commission."""
        commission = (gross_amount * self.fee_structure.commission_rate) / 100
        return max(commission, self.fee_structure.min_commission)

    def _calculate_exchange_fee(self, gross_amount: float) -> float:
        """Calculate exchange transaction fee."""
        if self.fee_structure.exchange_fee_rate == 0:
            return 0.0
        return (gross_amount * self.fee_structure.exchange_fee_rate) / 100

    def _calculate_clearing_fee(self, gross_amount: float) -> float:
        """Calculate clearing fee."""
        if self.fee_structure.clearing_fee_rate == 0:
            return 0.0
        return (gross_amount * self.fee_structure.clearing_fee_rate) / 100

    def get_required_cash(
        self,
        quantity: int,
        price: float,
        is_buy: bool
    ) -> float:
        """
        Get cash required for a transaction.

        Args:
            quantity: Number of shares
            price: Price per share
            is_buy: True for buy, False for sell

        Returns:
            Cash required (buy) or received (sell)
        """
        if is_buy:
            costs = self.calculate_buy_costs(quantity, price)
            return costs.net_amount
        else:
            costs = self.calculate_sell_costs(quantity, price)
            return costs.net_amount

    def get_max_shares_to_buy(
        self,
        available_cash: float,
        price: float
    ) -> int:
        """
        Calculate maximum shares that can be bought with available cash.

        Args:
            available_cash: Available cash
            price: Price per share

        Returns:
            Maximum number of shares
        """
        # Account for commission (approximate)
        commission_pct = self.fee_structure.commission_rate / 100
        effective_price = price * (1 + commission_pct)

        max_shares = int(available_cash / effective_price)

        # Verify we can afford it
        while max_shares > 0:
            costs = self.calculate_buy_costs(max_shares, price)
            if costs.net_amount <= available_cash:
                break
            max_shares -= 1

        return max(0, max_shares)
