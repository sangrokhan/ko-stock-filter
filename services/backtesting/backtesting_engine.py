"""
Backtesting Engine

Simulates trading strategy over historical data using vectorized operations
for maximum performance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from .data_loader import BacktestDataLoader
from .performance_metrics import MetricsCalculator, PerformanceMetrics
from services.trading_engine.commission_calculator import CommissionCalculator


@dataclass
class BacktestConfig:
    """Configuration for backtest"""

    # Time period
    start_date: datetime
    end_date: datetime

    # Capital
    initial_capital: float = 100_000_000  # 100M KRW
    max_positions: int = 20  # Maximum number of positions
    max_position_size: float = 0.10  # Maximum 10% per position

    # Signal generation parameters
    min_composite_score: float = 60.0  # Minimum composite score for entry
    min_momentum_score: float = 50.0  # Minimum momentum score for entry
    min_quality_score: float = 40.0  # Minimum quality score

    # Exit parameters
    stop_loss_pct: float = 0.10  # 10% stop loss
    take_profit_pct: float = 0.20  # 20% take profit
    trailing_stop_pct: float = 0.08  # 8% trailing stop
    quality_exit_threshold: float = 40.0  # Exit if quality drops below this
    score_deterioration_threshold: float = 20.0  # Exit if score drops by this much

    # Position sizing
    position_sizing_method: str = "equal"  # equal, kelly, or volatility
    kelly_fraction: float = 0.25  # Use quarter-Kelly for conservatism

    # Commission and slippage
    commission_rate: float = 0.00015  # 0.015% commission
    slippage_bps: float = 10  # 10 basis points slippage

    # Stock universe filters
    markets: Optional[List[str]] = None  # e.g., ['KOSPI', 'KOSDAQ']
    sectors: Optional[List[str]] = None  # Sector filter
    min_volume: Optional[float] = None  # Minimum daily volume
    min_price: Optional[float] = None  # Minimum price

    # Rebalancing
    rebalance_frequency: str = "daily"  # daily, weekly, monthly

    # Risk management
    max_sector_concentration: float = 0.30  # Max 30% in one sector
    max_correlation: float = 0.70  # Max correlation between positions

    def __post_init__(self):
        """Validate configuration"""
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if not 0 < self.max_position_size <= 1:
            raise ValueError("max_position_size must be between 0 and 1")


@dataclass
class BacktestResult:
    """Results from a backtest run"""

    config: BacktestConfig
    metrics: PerformanceMetrics

    # Time series data
    portfolio_values: pd.Series  # Daily portfolio values
    positions: pd.DataFrame  # Position history
    trades: pd.DataFrame  # Trade history
    daily_returns: pd.Series  # Daily returns

    # Additional analytics
    position_analytics: Dict  # Position-level analytics
    drawdown_periods: List[Dict]  # Drawdown period details

    def summary(self) -> str:
        """Generate summary string"""
        m = self.metrics
        summary = f"""
=== Backtest Results ===
Period: {m.start_date.date()} to {m.end_date.date()} ({m.trading_days} days)

RETURNS:
  Total Return:       {m.total_return:>8.2f}%
  Annualized Return:  {m.annualized_return:>8.2f}%
  CAGR:              {m.cagr:>8.2f}%

RISK:
  Volatility:        {m.volatility:>8.2f}%
  Max Drawdown:      {m.max_drawdown:>8.2f}%
  Sharpe Ratio:      {m.sharpe_ratio:>8.2f}
  Sortino Ratio:     {m.sortino_ratio:>8.2f}
  Calmar Ratio:      {m.calmar_ratio:>8.2f}

TRADES:
  Total Trades:      {m.total_trades:>8d}
  Win Rate:          {m.win_rate:>8.2f}%
  Profit Factor:     {m.profit_factor:>8.2f}
  Avg Win:           {m.avg_win:>8.2f}%
  Avg Loss:          {m.avg_loss:>8.2f}%

PORTFOLIO:
  Initial Capital:   {m.initial_capital:>15,.0f} KRW
  Final Value:       {m.final_portfolio_value:>15,.0f} KRW
  Total Fees:        {m.total_fees:>15,.0f} KRW
"""
        return summary


class BacktestingEngine:
    """
    Backtesting engine for trading strategies

    Uses vectorized operations for efficient simulation over historical data.
    """

    def __init__(
        self, config: BacktestConfig, db_session: Optional[Session] = None
    ):
        """
        Initialize backtesting engine

        Args:
            config: Backtest configuration
            db_session: Database session (optional)
        """
        self.config = config
        self.data_loader = BacktestDataLoader(db_session)
        self.commission_calc = CommissionCalculator()

        # State tracking
        self.portfolio: Dict[str, Dict] = {}  # ticker -> position info
        self.cash: float = config.initial_capital
        self.portfolio_value: float = config.initial_capital
        self.trades: List[Dict] = []
        self.daily_portfolio_values: List[Tuple[datetime, float]] = []

    def run(self) -> BacktestResult:
        """
        Run the backtest

        Returns:
            BacktestResult with metrics and analytics
        """
        print(f"Loading data from {self.config.start_date.date()} to {self.config.end_date.date()}...")

        # Load stock universe
        stock_universe = self.data_loader.load_stock_universe(
            markets=self.config.markets, sectors=self.config.sectors
        )

        if stock_universe.empty:
            raise ValueError("No stocks found matching criteria")

        print(f"Found {len(stock_universe)} stocks in universe")

        # Load historical data
        tickers = stock_universe["ticker"].tolist()
        data = self.data_loader.load_complete_dataset(
            tickers, self.config.start_date, self.config.end_date
        )

        if data.empty:
            raise ValueError("No historical data found")

        print(f"Loaded data for {len(data.index.get_level_values('ticker').unique())} stocks")

        # Get trading days
        trading_days = sorted(data.index.get_level_values("date").unique())
        print(f"Simulating {len(trading_days)} trading days...")

        # Run simulation
        self._simulate(data, trading_days, stock_universe)

        # Calculate metrics
        print("Calculating performance metrics...")
        metrics = self._calculate_metrics()

        # Generate analytics
        print("Generating analytics...")
        position_analytics = self._analyze_positions()
        drawdown_periods = self._analyze_drawdowns()

        # Create result
        result = BacktestResult(
            config=self.config,
            metrics=metrics,
            portfolio_values=pd.Series(
                [v for _, v in self.daily_portfolio_values],
                index=[d for d, _ in self.daily_portfolio_values],
            ),
            positions=self._get_position_history(),
            trades=pd.DataFrame(self.trades),
            daily_returns=self._calculate_daily_returns(),
            position_analytics=position_analytics,
            drawdown_periods=drawdown_periods,
        )

        print("Backtest complete!")
        return result

    def _simulate(
        self, data: pd.DataFrame, trading_days: List[datetime], stock_universe: pd.DataFrame
    ):
        """Run day-by-day simulation"""
        for i, current_date in enumerate(trading_days):
            # Get data for current date
            try:
                current_data = data.xs(current_date, level="date")
            except KeyError:
                continue

            # Update portfolio with current prices
            self._update_portfolio_prices(current_data)

            # Check exit conditions for existing positions
            self._check_exit_signals(current_date, current_data)

            # Generate entry signals if we have capacity
            if len(self.portfolio) < self.config.max_positions:
                self._check_entry_signals(current_date, current_data, stock_universe)

            # Record daily portfolio value
            self.daily_portfolio_values.append((current_date, self.portfolio_value))

            # Progress update
            if (i + 1) % 50 == 0:
                print(f"  Day {i+1}/{len(trading_days)}: Portfolio value = {self.portfolio_value:,.0f} KRW, Positions = {len(self.portfolio)}")

    def _update_portfolio_prices(self, current_data: pd.DataFrame):
        """Update portfolio with current prices"""
        portfolio_equity = 0.0

        for ticker, position in self.portfolio.items():
            if ticker in current_data.index:
                current_price = current_data.loc[ticker, "close"]
                position["current_price"] = current_price
                position["market_value"] = position["shares"] * current_price
                position["unrealized_pnl"] = position["market_value"] - position["cost_basis"]
                position["unrealized_pnl_pct"] = (
                    position["unrealized_pnl"] / position["cost_basis"] * 100
                )
                portfolio_equity += position["market_value"]

                # Update trailing stop
                if current_price > position["highest_price"]:
                    position["highest_price"] = current_price
                    position["trailing_stop_price"] = current_price * (
                        1 - self.config.trailing_stop_pct
                    )

        self.portfolio_value = self.cash + portfolio_equity

    def _check_exit_signals(self, current_date: datetime, current_data: pd.DataFrame):
        """Check for exit conditions on existing positions"""
        to_exit = []

        for ticker, position in self.portfolio.items():
            if ticker not in current_data.index:
                continue

            current_price = position["current_price"]
            entry_price = position["entry_price"]

            # Exit reasons
            exit_reason = None

            # Stop loss
            if current_price <= position["stop_loss_price"]:
                exit_reason = "stop_loss"

            # Take profit
            elif current_price >= position["take_profit_price"]:
                exit_reason = "take_profit"

            # Trailing stop
            elif current_price <= position["trailing_stop_price"]:
                exit_reason = "trailing_stop"

            # Quality deterioration
            elif "quality_score" in current_data.columns:
                quality_score = current_data.loc[ticker, "quality_score"]
                if not pd.isna(quality_score) and quality_score < self.config.quality_exit_threshold:
                    exit_reason = "quality_deterioration"

            # Score deterioration
            if exit_reason is None and "composite_score" in current_data.columns:
                current_score = current_data.loc[ticker, "composite_score"]
                entry_score = position["entry_composite_score"]
                if not pd.isna(current_score) and (
                    entry_score - current_score > self.config.score_deterioration_threshold
                ):
                    exit_reason = "score_deterioration"

            if exit_reason:
                to_exit.append((ticker, exit_reason))

        # Execute exits
        for ticker, reason in to_exit:
            self._execute_sell(ticker, current_date, reason)

    def _check_entry_signals(
        self, current_date: datetime, current_data: pd.DataFrame, stock_universe: pd.DataFrame
    ):
        """Generate and execute entry signals"""
        # Filter for entry candidates
        candidates = current_data.copy()

        # Apply filters
        if "composite_score" in candidates.columns:
            candidates = candidates[
                candidates["composite_score"] >= self.config.min_composite_score
            ]

        if "momentum_score" in candidates.columns:
            candidates = candidates[
                candidates["momentum_score"] >= self.config.min_momentum_score
            ]

        if "quality_score" in candidates.columns:
            candidates = candidates[
                candidates["quality_score"] >= self.config.min_quality_score
            ]

        if self.config.min_volume and "volume" in candidates.columns:
            candidates = candidates[candidates["volume"] >= self.config.min_volume]

        if self.config.min_price and "close" in candidates.columns:
            candidates = candidates[candidates["close"] >= self.config.min_price]

        # Remove stocks already in portfolio
        candidates = candidates[~candidates.index.isin(self.portfolio.keys())]

        if candidates.empty:
            return

        # Rank by composite score
        if "composite_score" in candidates.columns:
            candidates = candidates.sort_values("composite_score", ascending=False)

        # Calculate position sizes
        available_slots = self.config.max_positions - len(self.portfolio)
        num_to_buy = min(available_slots, len(candidates))

        for ticker in candidates.index[:num_to_buy]:
            position_size = self._calculate_position_size(
                ticker, candidates.loc[ticker], current_data
            )

            if position_size > 0:
                self._execute_buy(ticker, current_date, candidates.loc[ticker], position_size)

    def _calculate_position_size(
        self, ticker: str, stock_data: pd.Series, market_data: pd.DataFrame
    ) -> float:
        """Calculate position size based on sizing method"""
        max_position_value = self.portfolio_value * self.config.max_position_size
        available_cash = self.cash

        if self.config.position_sizing_method == "equal":
            # Equal weighting
            target_positions = self.config.max_positions
            position_value = min(
                self.portfolio_value / target_positions, available_cash, max_position_value
            )

        elif self.config.position_sizing_method == "kelly":
            # Kelly criterion
            win_rate = 0.55  # Estimate from historical data
            avg_win_loss_ratio = 1.5  # Estimate
            kelly_fraction = win_rate - (1 - win_rate) / avg_win_loss_ratio
            kelly_fraction = max(0, min(kelly_fraction, 1)) * self.config.kelly_fraction
            position_value = min(
                self.portfolio_value * kelly_fraction, available_cash, max_position_value
            )

        elif self.config.position_sizing_method == "volatility":
            # Volatility-adjusted sizing
            atr = stock_data.get("atr", 0)
            close = stock_data["close"]
            if atr > 0 and close > 0:
                volatility_factor = 1 / (atr / close)
                position_value = min(
                    self.portfolio_value * self.config.max_position_size * volatility_factor,
                    available_cash,
                    max_position_value,
                )
            else:
                position_value = min(
                    self.portfolio_value / self.config.max_positions,
                    available_cash,
                    max_position_value,
                )
        else:
            position_value = min(
                self.portfolio_value / self.config.max_positions,
                available_cash,
                max_position_value,
            )

        return position_value

    def _execute_buy(
        self, ticker: str, date: datetime, stock_data: pd.Series, position_value: float
    ):
        """Execute a buy order"""
        price = stock_data["close"]

        # Apply slippage
        price_with_slippage = price * (1 + self.config.slippage_bps / 10000)

        # Calculate shares and fees
        shares = int(position_value / price_with_slippage)
        if shares == 0:
            return

        gross_amount = shares * price_with_slippage
        commission = gross_amount * self.config.commission_rate
        total_cost = gross_amount + commission

        if total_cost > self.cash:
            return

        # Update cash
        self.cash -= total_cost

        # Create position
        self.portfolio[ticker] = {
            "ticker": ticker,
            "shares": shares,
            "entry_price": price_with_slippage,
            "entry_date": date,
            "current_price": price_with_slippage,
            "cost_basis": total_cost,
            "market_value": shares * price_with_slippage,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
            "stop_loss_price": price_with_slippage * (1 - self.config.stop_loss_pct),
            "take_profit_price": price_with_slippage * (1 + self.config.take_profit_pct),
            "trailing_stop_price": price_with_slippage * (1 - self.config.trailing_stop_pct),
            "highest_price": price_with_slippage,
            "entry_composite_score": stock_data.get("composite_score", 0),
        }

        # Record trade
        self.trades.append(
            {
                "date": date,
                "ticker": ticker,
                "action": "BUY",
                "shares": shares,
                "price": price_with_slippage,
                "amount": gross_amount,
                "commission": commission,
                "tax": 0.0,
                "total_cost": total_cost,
            }
        )

    def _execute_sell(self, ticker: str, date: datetime, reason: str):
        """Execute a sell order"""
        position = self.portfolio[ticker]
        price = position["current_price"]

        # Apply slippage
        price_with_slippage = price * (1 - self.config.slippage_bps / 10000)

        shares = position["shares"]
        gross_proceeds = shares * price_with_slippage

        # Calculate fees (commission + tax for sells)
        commission = gross_proceeds * self.config.commission_rate
        tax = gross_proceeds * 0.0023  # 0.23% transaction tax
        agri_fish_tax = tax * 0.15  # 0.15% of transaction tax
        total_tax = tax + agri_fish_tax
        net_proceeds = gross_proceeds - commission - total_tax

        # Update cash
        self.cash += net_proceeds

        # Calculate trade performance
        holding_period = (date - position["entry_date"]).days
        profit = net_proceeds - position["cost_basis"]
        return_pct = profit / position["cost_basis"] * 100

        # Record trade
        self.trades.append(
            {
                "date": date,
                "ticker": ticker,
                "action": "SELL",
                "shares": shares,
                "price": price_with_slippage,
                "amount": gross_proceeds,
                "commission": commission,
                "tax": total_tax,
                "total_proceeds": net_proceeds,
                "profit": profit,
                "return_pct": return_pct,
                "holding_period": holding_period,
                "exit_reason": reason,
                "entry_price": position["entry_price"],
                "entry_date": position["entry_date"],
            }
        )

        # Remove position
        del self.portfolio[ticker]

    def _calculate_metrics(self) -> PerformanceMetrics:
        """Calculate performance metrics"""
        portfolio_series = pd.Series(
            [v for _, v in self.daily_portfolio_values],
            index=[d for d, _ in self.daily_portfolio_values],
        )

        trades_df = pd.DataFrame(self.trades)

        metrics = MetricsCalculator.calculate_metrics(
            portfolio_series, trades_df, self.config.initial_capital
        )

        return metrics

    def _calculate_daily_returns(self) -> pd.Series:
        """Calculate daily returns"""
        portfolio_series = pd.Series(
            [v for _, v in self.daily_portfolio_values],
            index=[d for d, _ in self.daily_portfolio_values],
        )
        return portfolio_series.pct_change()

    def _get_position_history(self) -> pd.DataFrame:
        """Get position history"""
        # Extract position snapshots from trades
        positions = []
        for trade in self.trades:
            if trade["action"] == "BUY":
                positions.append(
                    {
                        "ticker": trade["ticker"],
                        "entry_date": trade["date"],
                        "entry_price": trade["price"],
                        "shares": trade["shares"],
                    }
                )

        return pd.DataFrame(positions)

    def _analyze_positions(self) -> Dict:
        """Analyze position-level performance"""
        trades_df = pd.DataFrame(self.trades)
        sell_trades = trades_df[trades_df["action"] == "SELL"]

        if sell_trades.empty:
            return {}

        # Per-ticker performance
        ticker_performance = (
            sell_trades.groupby("ticker")
            .agg(
                {
                    "return_pct": ["mean", "sum", "count"],
                    "holding_period": "mean",
                    "profit": "sum",
                }
            )
            .round(2)
        )

        return {
            "ticker_performance": ticker_performance.to_dict(),
            "total_tickers_traded": len(sell_trades["ticker"].unique()),
        }

    def _analyze_drawdowns(self) -> List[Dict]:
        """Analyze drawdown periods"""
        portfolio_series = pd.Series(
            [v for _, v in self.daily_portfolio_values],
            index=[d for d, _ in self.daily_portfolio_values],
        )

        running_max = portfolio_series.expanding().max()
        drawdown = (portfolio_series - running_max) / running_max

        # Find drawdown periods
        in_drawdown = drawdown < 0
        drawdown_groups = (in_drawdown != in_drawdown.shift()).cumsum()

        drawdown_periods = []
        for group_id in drawdown_groups[in_drawdown].unique():
            period_mask = (drawdown_groups == group_id) & in_drawdown
            period = drawdown[period_mask]

            if len(period) > 0:
                drawdown_periods.append(
                    {
                        "start_date": period.index[0],
                        "end_date": period.index[-1],
                        "duration_days": len(period),
                        "max_drawdown_pct": abs(period.min() * 100),
                    }
                )

        # Sort by max drawdown
        drawdown_periods.sort(key=lambda x: x["max_drawdown_pct"], reverse=True)

        return drawdown_periods
