"""
Position sizing module with Kelly Criterion and fixed percentage methods.
Calculates optimal position sizes based on risk parameters and historical performance.
"""
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PositionSizingMethod(Enum):
    """Position sizing methods."""
    KELLY_CRITERION = "kelly_criterion"
    KELLY_HALF = "kelly_half"  # Conservative Kelly (50% of Kelly)
    KELLY_QUARTER = "kelly_quarter"  # Very conservative Kelly (25% of Kelly)
    FIXED_PERCENT = "fixed_percent"
    FIXED_RISK = "fixed_risk"
    VOLATILITY_ADJUSTED = "volatility_adjusted"


@dataclass
class PositionSizingResult:
    """Result of position sizing calculation."""
    shares: int
    position_value: float
    position_pct: float
    method: str
    kelly_fraction: Optional[float] = None
    risk_amount: Optional[float] = None
    notes: Optional[str] = None


class PositionSizer:
    """
    Position sizing calculator supporting multiple methods.

    Methods:
    - Kelly Criterion: Optimal bet sizing based on win rate and profit factor
    - Fixed Percent: Fixed percentage of portfolio per position
    - Fixed Risk: Fixed dollar/percentage risk per trade
    - Volatility Adjusted: Position size inversely proportional to volatility
    """

    def __init__(
        self,
        default_method: PositionSizingMethod = PositionSizingMethod.KELLY_HALF,
        max_position_size_pct: float = 10.0,
        default_fixed_pct: float = 5.0,
        default_risk_pct: float = 2.0
    ):
        """
        Initialize position sizer.

        Args:
            default_method: Default sizing method
            max_position_size_pct: Maximum position size as % of portfolio
            default_fixed_pct: Default fixed percentage for FIXED_PERCENT method
            default_risk_pct: Default risk percentage for FIXED_RISK method
        """
        self.default_method = default_method
        self.max_position_size_pct = max_position_size_pct
        self.default_fixed_pct = default_fixed_pct
        self.default_risk_pct = default_risk_pct

    def calculate_kelly_criterion(
        self,
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float
    ) -> float:
        """
        Calculate Kelly Criterion fraction.

        Formula: f* = (p * b - q) / b
        where:
        - p = win rate (probability of winning)
        - q = 1 - p (probability of losing)
        - b = avg_win / avg_loss (win/loss ratio)

        Args:
            win_rate: Win rate as decimal (e.g., 0.6 for 60%)
            avg_win_pct: Average win percentage (e.g., 15.0 for +15%)
            avg_loss_pct: Average loss percentage (e.g., 8.0 for -8%)

        Returns:
            Kelly fraction (percentage of portfolio to risk)
        """
        if win_rate <= 0 or win_rate >= 1:
            logger.warning(f"Invalid win rate: {win_rate}. Using 0% Kelly.")
            return 0.0

        if avg_loss_pct <= 0:
            logger.warning(f"Invalid average loss: {avg_loss_pct}. Using 0% Kelly.")
            return 0.0

        if avg_win_pct <= 0:
            logger.warning(f"Invalid average win: {avg_win_pct}. Using 0% Kelly.")
            return 0.0

        # Calculate win/loss ratio
        win_loss_ratio = avg_win_pct / avg_loss_pct

        # Kelly formula
        p = win_rate
        q = 1 - win_rate
        b = win_loss_ratio

        kelly_fraction = (p * b - q) / b

        # Kelly can be negative if expected value is negative
        if kelly_fraction < 0:
            logger.warning(f"Negative Kelly fraction: {kelly_fraction:.4f}. System has negative expectancy.")
            return 0.0

        # Cap at 100%
        kelly_fraction = min(kelly_fraction, 1.0)

        logger.info(f"Kelly Criterion: win_rate={win_rate:.2%}, "
                   f"win/loss_ratio={win_loss_ratio:.2f}, kelly={kelly_fraction:.2%}")

        return kelly_fraction

    def calculate_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss_price: float,
        method: Optional[PositionSizingMethod] = None,
        win_rate: Optional[float] = None,
        avg_win_pct: Optional[float] = None,
        avg_loss_pct: Optional[float] = None,
        volatility: Optional[float] = None,
        fixed_pct: Optional[float] = None,
        risk_pct: Optional[float] = None
    ) -> PositionSizingResult:
        """
        Calculate position size using specified method.

        Args:
            portfolio_value: Total portfolio value
            entry_price: Entry price per share
            stop_loss_price: Stop-loss price
            method: Sizing method (defaults to self.default_method)
            win_rate: Historical win rate (for Kelly)
            avg_win_pct: Average win percentage (for Kelly)
            avg_loss_pct: Average loss percentage (for Kelly)
            volatility: Stock volatility (for volatility-adjusted)
            fixed_pct: Fixed percentage (for FIXED_PERCENT)
            risk_pct: Risk percentage (for FIXED_RISK)

        Returns:
            PositionSizingResult with calculated position size
        """
        method = method or self.default_method
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share == 0:
            raise ValueError("Risk per share cannot be zero. Stop-loss price must differ from entry price.")

        if entry_price <= 0:
            raise ValueError("Entry price must be positive")

        if portfolio_value <= 0:
            raise ValueError("Portfolio value must be positive")

        # Calculate based on method
        if method == PositionSizingMethod.KELLY_CRITERION:
            result = self._calculate_kelly_position(
                portfolio_value, entry_price, stop_loss_price, risk_per_share,
                win_rate, avg_win_pct, avg_loss_pct, kelly_fraction=1.0
            )
        elif method == PositionSizingMethod.KELLY_HALF:
            result = self._calculate_kelly_position(
                portfolio_value, entry_price, stop_loss_price, risk_per_share,
                win_rate, avg_win_pct, avg_loss_pct, kelly_fraction=0.5
            )
        elif method == PositionSizingMethod.KELLY_QUARTER:
            result = self._calculate_kelly_position(
                portfolio_value, entry_price, stop_loss_price, risk_per_share,
                win_rate, avg_win_pct, avg_loss_pct, kelly_fraction=0.25
            )
        elif method == PositionSizingMethod.FIXED_PERCENT:
            result = self._calculate_fixed_percent_position(
                portfolio_value, entry_price, fixed_pct or self.default_fixed_pct
            )
        elif method == PositionSizingMethod.FIXED_RISK:
            result = self._calculate_fixed_risk_position(
                portfolio_value, entry_price, risk_per_share,
                risk_pct or self.default_risk_pct
            )
        elif method == PositionSizingMethod.VOLATILITY_ADJUSTED:
            result = self._calculate_volatility_adjusted_position(
                portfolio_value, entry_price, volatility
            )
        else:
            raise ValueError(f"Unknown position sizing method: {method}")

        # Apply maximum position size constraint
        max_position_value = portfolio_value * (self.max_position_size_pct / 100)
        max_shares = int(max_position_value / entry_price)

        if result.shares > max_shares:
            logger.info(f"Position size capped at {self.max_position_size_pct}%: "
                       f"{result.shares} → {max_shares} shares")
            result.shares = max_shares
            result.position_value = max_shares * entry_price
            result.position_pct = (result.position_value / portfolio_value) * 100
            result.notes = (result.notes or "") + f" [Capped at {self.max_position_size_pct}% max]"

        return result

    def _calculate_kelly_position(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss_price: float,
        risk_per_share: float,
        win_rate: Optional[float],
        avg_win_pct: Optional[float],
        avg_loss_pct: Optional[float],
        kelly_fraction: float = 1.0
    ) -> PositionSizingResult:
        """Calculate position size using Kelly Criterion."""
        if not all([win_rate, avg_win_pct, avg_loss_pct]):
            # Fallback to fixed risk if Kelly inputs not available
            logger.warning("Kelly Criterion requires win_rate, avg_win_pct, and avg_loss_pct. "
                         "Falling back to fixed risk method.")
            return self._calculate_fixed_risk_position(
                portfolio_value, entry_price, risk_per_share, self.default_risk_pct
            )

        # Calculate Kelly percentage
        kelly_pct = self.calculate_kelly_criterion(win_rate, avg_win_pct, avg_loss_pct)

        # Apply Kelly fraction (e.g., 0.5 for half-Kelly)
        adjusted_kelly_pct = kelly_pct * kelly_fraction

        # Calculate position value and shares
        position_value = portfolio_value * adjusted_kelly_pct
        shares = int(position_value / entry_price)

        position_pct = (position_value / portfolio_value) * 100

        method_name = f"Kelly Criterion (fraction={kelly_fraction})"
        notes = f"Full Kelly={kelly_pct:.2%}, Adjusted Kelly={adjusted_kelly_pct:.2%}"

        return PositionSizingResult(
            shares=shares,
            position_value=position_value,
            position_pct=position_pct,
            method=method_name,
            kelly_fraction=adjusted_kelly_pct,
            notes=notes
        )

    def _calculate_fixed_percent_position(
        self,
        portfolio_value: float,
        entry_price: float,
        fixed_pct: float
    ) -> PositionSizingResult:
        """Calculate position size as fixed percentage of portfolio."""
        position_value = portfolio_value * (fixed_pct / 100)
        shares = int(position_value / entry_price)
        actual_pct = (shares * entry_price / portfolio_value) * 100

        return PositionSizingResult(
            shares=shares,
            position_value=shares * entry_price,
            position_pct=actual_pct,
            method=f"Fixed Percent ({fixed_pct}%)",
            notes=f"Target: {fixed_pct}%, Actual: {actual_pct:.2f}%"
        )

    def _calculate_fixed_risk_position(
        self,
        portfolio_value: float,
        entry_price: float,
        risk_per_share: float,
        risk_pct: float
    ) -> PositionSizingResult:
        """Calculate position size based on fixed risk percentage."""
        risk_amount = portfolio_value * (risk_pct / 100)
        shares = int(risk_amount / risk_per_share)
        position_value = shares * entry_price
        position_pct = (position_value / portfolio_value) * 100

        return PositionSizingResult(
            shares=shares,
            position_value=position_value,
            position_pct=position_pct,
            method=f"Fixed Risk ({risk_pct}%)",
            risk_amount=risk_amount,
            notes=f"Risk: {risk_amount:,.0f} KRW ({risk_pct}% of portfolio)"
        )

    def _calculate_volatility_adjusted_position(
        self,
        portfolio_value: float,
        entry_price: float,
        volatility: Optional[float]
    ) -> PositionSizingResult:
        """
        Calculate position size inversely proportional to volatility.
        Higher volatility = smaller position.
        """
        if volatility is None or volatility <= 0:
            logger.warning("Invalid volatility for volatility-adjusted sizing. Using fixed 5%.")
            return self._calculate_fixed_percent_position(portfolio_value, entry_price, 5.0)

        # Base position size is 10%, scaled by inverse of volatility
        # If volatility is 20%, position = 10% * (20% / volatility)
        base_volatility = 20.0  # Reference volatility
        base_position_pct = 5.0

        adjusted_pct = base_position_pct * (base_volatility / volatility)
        adjusted_pct = max(1.0, min(adjusted_pct, self.max_position_size_pct))

        position_value = portfolio_value * (adjusted_pct / 100)
        shares = int(position_value / entry_price)
        actual_pct = (shares * entry_price / portfolio_value) * 100

        return PositionSizingResult(
            shares=shares,
            position_value=shares * entry_price,
            position_pct=actual_pct,
            method="Volatility Adjusted",
            notes=f"Volatility: {volatility:.1f}%, Adjusted to {adjusted_pct:.2f}%"
        )

    def get_historical_performance(
        self,
        trades: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate historical performance metrics from trade history.

        Args:
            trades: List of trade dictionaries with 'pnl' or 'pnl_pct' fields

        Returns:
            Dictionary with win_rate, avg_win_pct, avg_loss_pct, profit_factor
        """
        if not trades:
            return {
                'win_rate': 0.5,  # Default 50%
                'avg_win_pct': 10.0,  # Default +10%
                'avg_loss_pct': 5.0,  # Default -5%
                'profit_factor': 2.0,
                'total_trades': 0
            }

        winning_trades = []
        losing_trades = []

        for trade in trades:
            pnl_pct = trade.get('pnl_pct', 0)
            if pnl_pct > 0:
                winning_trades.append(pnl_pct)
            elif pnl_pct < 0:
                losing_trades.append(abs(pnl_pct))

        total_trades = len(winning_trades) + len(losing_trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.5

        avg_win_pct = sum(winning_trades) / len(winning_trades) if winning_trades else 10.0
        avg_loss_pct = sum(losing_trades) / len(losing_trades) if losing_trades else 5.0

        total_wins = sum(winning_trades)
        total_losses = sum(losing_trades)
        profit_factor = total_wins / total_losses if total_losses > 0 else 2.0

        return {
            'win_rate': win_rate,
            'avg_win_pct': avg_win_pct,
            'avg_loss_pct': avg_loss_pct,
            'profit_factor': profit_factor,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades)
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example: Calculate position size with Kelly Criterion
    sizer = PositionSizer(
        default_method=PositionSizingMethod.KELLY_HALF,
        max_position_size_pct=10.0,
        default_risk_pct=2.0
    )

    # Historical performance (example)
    historical_trades = [
        {'pnl_pct': 15.0},
        {'pnl_pct': -8.0},
        {'pnl_pct': 12.0},
        {'pnl_pct': -5.0},
        {'pnl_pct': 20.0},
        {'pnl_pct': -7.0},
    ]

    perf = sizer.get_historical_performance(historical_trades)
    print(f"Historical Performance: {perf}")

    # Calculate position size
    result = sizer.calculate_position_size(
        portfolio_value=100_000_000,  # 100M KRW
        entry_price=70_000,  # 70,000 KRW per share
        stop_loss_price=63_000,  # -10% stop loss
        method=PositionSizingMethod.KELLY_HALF,
        win_rate=perf['win_rate'],
        avg_win_pct=perf['avg_win_pct'],
        avg_loss_pct=perf['avg_loss_pct']
    )

    print(f"\nPosition Sizing Result:")
    print(f"  Method: {result.method}")
    print(f"  Shares: {result.shares}")
    print(f"  Position Value: {result.position_value:,.0f} KRW")
    print(f"  Position %: {result.position_pct:.2f}%")
    print(f"  Notes: {result.notes}")
