"""
Database models for Korean stock trading system.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Index, BigInteger, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Stock(Base):
    """Stock information model."""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False, comment="Stock code (e.g., 005930 for Samsung)")
    name_kr = Column(String(100), nullable=False, comment="Korean name")
    name_en = Column(String(100), comment="English name")
    market = Column(String(20), index=True, comment="KOSPI, KOSDAQ, KONEX, etc.")
    sector = Column(String(50), index=True, comment="Business sector")
    industry = Column(String(100), comment="Industry classification")
    market_cap = Column(BigInteger, comment="Market capitalization in KRW")
    listed_shares = Column(BigInteger, comment="Total number of listed shares")
    listed_date = Column(DateTime, comment="IPO date")
    is_active = Column(Boolean, default=True, index=True, comment="Whether stock is actively traded")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    prices = relationship("StockPrice", back_populates="stock", cascade="all, delete-orphan")
    technical_indicators = relationship("TechnicalIndicator", back_populates="stock", cascade="all, delete-orphan")
    fundamental_indicators = relationship("FundamentalIndicator", back_populates="stock", cascade="all, delete-orphan")
    watchlist_entries = relationship("Watchlist", back_populates="stock", cascade="all, delete-orphan")


class StockPrice(Base):
    """Stock price data model."""
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True, comment="Trading date")
    open = Column(Numeric(15, 2), nullable=False, comment="Opening price")
    high = Column(Numeric(15, 2), nullable=False, comment="Highest price")
    low = Column(Numeric(15, 2), nullable=False, comment="Lowest price")
    close = Column(Numeric(15, 2), nullable=False, comment="Closing price")
    volume = Column(BigInteger, nullable=False, comment="Trading volume")
    adjusted_close = Column(Numeric(15, 2), comment="Adjusted closing price for splits/dividends")
    trading_value = Column(BigInteger, comment="Total trading value in KRW")
    change_pct = Column(Float, comment="Daily change percentage")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="prices")

    # Composite index for efficient queries
    __table_args__ = (
        Index('ix_stock_prices_stock_date', 'stock_id', 'date'),
        Index('ix_stock_prices_date_volume', 'date', 'volume'),
    )


class TechnicalIndicator(Base):
    """Technical indicators model."""
    __tablename__ = "technical_indicators"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True, comment="Indicator calculation date")

    # Momentum Indicators
    rsi_14 = Column(Float, comment="14-day Relative Strength Index")
    rsi_9 = Column(Float, comment="9-day Relative Strength Index")
    stochastic_k = Column(Float, comment="Stochastic %K")
    stochastic_d = Column(Float, comment="Stochastic %D")

    # Trend Indicators
    macd = Column(Float, comment="MACD line")
    macd_signal = Column(Float, comment="MACD signal line")
    macd_histogram = Column(Float, comment="MACD histogram")
    adx = Column(Float, comment="Average Directional Index")

    # Moving Averages
    sma_5 = Column(Float, comment="5-day Simple Moving Average")
    sma_20 = Column(Float, comment="20-day Simple Moving Average")
    sma_50 = Column(Float, comment="50-day Simple Moving Average")
    sma_120 = Column(Float, comment="120-day Simple Moving Average")
    sma_200 = Column(Float, comment="200-day Simple Moving Average")
    ema_12 = Column(Float, comment="12-day Exponential Moving Average")
    ema_26 = Column(Float, comment="26-day Exponential Moving Average")

    # Volatility Indicators
    bollinger_upper = Column(Float, comment="Bollinger Upper Band")
    bollinger_middle = Column(Float, comment="Bollinger Middle Band")
    bollinger_lower = Column(Float, comment="Bollinger Lower Band")
    atr = Column(Float, comment="Average True Range")

    # Volume Indicators
    obv = Column(BigInteger, comment="On Balance Volume")
    volume_ma_20 = Column(BigInteger, comment="20-day Volume Moving Average")

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="technical_indicators")

    # Composite index
    __table_args__ = (
        Index('ix_tech_indicators_stock_date', 'stock_id', 'date'),
    )


class FundamentalIndicator(Base):
    """Fundamental indicators and financial metrics model."""
    __tablename__ = "fundamental_indicators"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True, comment="Reporting date or calculation date")

    # Valuation Ratios
    per = Column(Float, comment="Price to Earnings Ratio")
    pbr = Column(Float, comment="Price to Book Ratio")
    pcr = Column(Float, comment="Price to Cashflow Ratio")
    psr = Column(Float, comment="Price to Sales Ratio")

    # Profitability Ratios
    roe = Column(Float, comment="Return on Equity (%)")
    roa = Column(Float, comment="Return on Assets (%)")
    roic = Column(Float, comment="Return on Invested Capital (%)")
    operating_margin = Column(Float, comment="Operating Profit Margin (%)")
    net_margin = Column(Float, comment="Net Profit Margin (%)")

    # Financial Health Ratios
    debt_ratio = Column(Float, comment="Total Debt to Total Assets (%)")
    debt_to_equity = Column(Float, comment="Debt to Equity Ratio")
    current_ratio = Column(Float, comment="Current Assets to Current Liabilities")
    quick_ratio = Column(Float, comment="Quick Ratio (Acid Test)")
    interest_coverage = Column(Float, comment="Interest Coverage Ratio")

    # Growth Metrics
    revenue_growth = Column(Float, comment="YoY Revenue Growth (%)")
    earnings_growth = Column(Float, comment="YoY Earnings Growth (%)")
    equity_growth = Column(Float, comment="YoY Equity Growth (%)")

    # Dividend Metrics
    dividend_yield = Column(Float, comment="Dividend Yield (%)")
    dividend_payout_ratio = Column(Float, comment="Dividend Payout Ratio (%)")

    # Per Share Metrics
    eps = Column(Float, comment="Earnings Per Share")
    bps = Column(Float, comment="Book value Per Share")
    cps = Column(Float, comment="Cashflow Per Share")
    sps = Column(Float, comment="Sales Per Share")
    dps = Column(Float, comment="Dividend Per Share")

    # Absolute Values (in KRW millions)
    revenue = Column(BigInteger, comment="Total Revenue")
    operating_profit = Column(BigInteger, comment="Operating Profit")
    net_income = Column(BigInteger, comment="Net Income")
    total_assets = Column(BigInteger, comment="Total Assets")
    total_equity = Column(BigInteger, comment="Total Equity")
    total_debt = Column(BigInteger, comment="Total Debt")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="fundamental_indicators")

    # Composite indexes
    __table_args__ = (
        Index('ix_fund_indicators_stock_date', 'stock_id', 'date'),
        Index('ix_fund_indicators_per_pbr', 'per', 'pbr'),
        Index('ix_fund_indicators_roe', 'roe'),
    )


class StabilityScore(Base):
    """Stability score and risk metrics model."""
    __tablename__ = "stability_scores"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True, comment="Calculation date")

    # Price Volatility Metrics
    price_volatility = Column(Float, comment="Price volatility (std dev of returns)")
    price_volatility_score = Column(Float, comment="Price volatility score (0-100, higher is more stable)")
    returns_mean = Column(Float, comment="Mean of daily returns")
    returns_std = Column(Float, comment="Standard deviation of daily returns")

    # Beta Coefficient (Market Risk)
    beta = Column(Float, comment="Beta coefficient (systematic risk vs market)")
    beta_score = Column(Float, comment="Beta score (0-100, closer to 1.0 is more stable)")
    market_correlation = Column(Float, comment="Correlation with market index")

    # Volume Stability Metrics
    volume_stability = Column(Float, comment="Volume stability (coefficient of variation)")
    volume_stability_score = Column(Float, comment="Volume stability score (0-100)")
    volume_mean = Column(BigInteger, comment="Mean trading volume")
    volume_std = Column(BigInteger, comment="Standard deviation of trading volume")

    # Earnings Consistency Metrics
    earnings_consistency = Column(Float, comment="Earnings consistency (coefficient of variation)")
    earnings_consistency_score = Column(Float, comment="Earnings consistency score (0-100)")
    earnings_trend = Column(Float, comment="Earnings trend (slope)")

    # Debt Stability Metrics
    debt_stability = Column(Float, comment="Debt stability (trend analysis)")
    debt_stability_score = Column(Float, comment="Debt stability score (0-100)")
    debt_trend = Column(Float, comment="Debt ratio trend (slope)")
    debt_ratio_current = Column(Float, comment="Current debt ratio")

    # Overall Stability Score
    stability_score = Column(Float, nullable=False, index=True, comment="Overall stability score (0-100)")

    # Component Weights (for transparency)
    weight_price = Column(Float, default=0.25, comment="Weight of price volatility component")
    weight_beta = Column(Float, default=0.20, comment="Weight of beta component")
    weight_volume = Column(Float, default=0.15, comment="Weight of volume stability component")
    weight_earnings = Column(Float, default=0.25, comment="Weight of earnings consistency component")
    weight_debt = Column(Float, default=0.15, comment="Weight of debt stability component")

    # Data Quality Indicators
    data_points_price = Column(Integer, comment="Number of price data points used")
    data_points_earnings = Column(Integer, comment="Number of earnings data points used")
    data_points_debt = Column(Integer, comment="Number of debt data points used")
    calculation_period_days = Column(Integer, comment="Period used for calculation in days")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", backref="stability_scores")

    # Composite indexes
    __table_args__ = (
        Index('ix_stability_scores_stock_date', 'stock_id', 'date'),
        Index('ix_stability_scores_score', 'stability_score'),
    )


class Trade(Base):
    """Trade execution model (trade_history)."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, nullable=False, index=True, comment="Unique order identifier")
    ticker = Column(String(20), nullable=False, index=True, comment="Stock code")
    action = Column(String(10), nullable=False, index=True, comment="BUY, SELL")
    order_type = Column(String(20), nullable=False, comment="MARKET, LIMIT, STOP_LOSS")
    quantity = Column(Integer, nullable=False, comment="Number of shares")
    price = Column(Numeric(15, 2), comment="Order price (limit/stop price)")
    executed_price = Column(Numeric(15, 2), comment="Actual execution price")
    executed_quantity = Column(Integer, comment="Actual executed quantity")
    total_amount = Column(BigInteger, comment="Total transaction amount in KRW")
    commission = Column(Integer, comment="Commission fees in KRW")
    tax = Column(Integer, comment="Tax amount in KRW")
    status = Column(String(20), nullable=False, index=True, comment="PENDING, EXECUTED, PARTIALLY_FILLED, CANCELLED, FAILED")
    reason = Column(Text, comment="Reason for trade or failure reason")
    strategy = Column(String(50), comment="Trading strategy that generated this order")
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="Order creation timestamp")
    executed_at = Column(DateTime, index=True, comment="Execution timestamp")
    cancelled_at = Column(DateTime, comment="Cancellation timestamp")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite indexes
    __table_args__ = (
        Index('ix_trades_ticker_date', 'ticker', 'created_at'),
        Index('ix_trades_status_date', 'status', 'created_at'),
    )


class Portfolio(Base):
    """Portfolio holdings model."""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True, comment="User identifier")
    ticker = Column(String(20), nullable=False, index=True, comment="Stock code")
    quantity = Column(Integer, nullable=False, comment="Number of shares held")
    avg_price = Column(Numeric(15, 2), nullable=False, comment="Average purchase price per share")
    current_price = Column(Numeric(15, 2), comment="Current market price per share")
    current_value = Column(BigInteger, comment="Current total value (quantity * current_price)")
    invested_amount = Column(BigInteger, comment="Total invested amount (quantity * avg_price)")
    unrealized_pnl = Column(BigInteger, comment="Unrealized profit/loss in KRW")
    unrealized_pnl_pct = Column(Float, comment="Unrealized profit/loss percentage")
    realized_pnl = Column(BigInteger, comment="Realized profit/loss in KRW")
    total_commission = Column(Integer, comment="Total commission paid")
    total_tax = Column(Integer, comment="Total tax paid")
    first_purchase_date = Column(DateTime, comment="Date of first purchase")
    last_transaction_date = Column(DateTime, comment="Date of last transaction")

    # Stop-Loss and Take-Profit Fields
    stop_loss_price = Column(Numeric(15, 2), comment="Stop-loss trigger price (absolute price)")
    stop_loss_pct = Column(Float, default=10.0, comment="Stop-loss percentage from avg price (default -10%)")
    trailing_stop_price = Column(Numeric(15, 2), comment="Trailing stop-loss price (moves up with profit)")
    trailing_stop_enabled = Column(Boolean, default=True, comment="Whether trailing stop-loss is enabled")
    trailing_stop_distance_pct = Column(Float, default=10.0, comment="Distance % for trailing stop from highest price")
    highest_price_since_purchase = Column(Numeric(15, 2), comment="Highest price achieved since purchase (for trailing stop)")
    take_profit_price = Column(Numeric(15, 2), comment="Take-profit trigger price (absolute price)")
    take_profit_pct = Column(Float, default=20.0, comment="Take-profit percentage from avg price (default +20%)")
    take_profit_use_technical = Column(Boolean, default=False, comment="Use technical signals for take-profit")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite indexes
    __table_args__ = (
        Index('ix_portfolios_user_ticker', 'user_id', 'ticker', unique=True),
    )


class CompositeScore(Base):
    """Composite investment score model combining value, growth, quality, and momentum scores."""
    __tablename__ = "composite_scores"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True, comment="Calculation date")

    # Component Scores (0-100 scale)
    value_score = Column(Float, comment="Value score based on PER, PBR, dividend yield (0-100)")
    growth_score = Column(Float, comment="Growth score based on earnings/revenue growth (0-100)")
    quality_score = Column(Float, comment="Quality score based on ROE, margins, debt (0-100)")
    momentum_score = Column(Float, comment="Momentum score based on price trend, RSI (0-100)")

    # Overall Composite Score
    composite_score = Column(Float, nullable=False, index=True, comment="Overall composite score (0-100)")
    percentile_rank = Column(Float, comment="Percentile rank among all stocks (0-100)")

    # Component Weights (for transparency and customization)
    weight_value = Column(Float, default=0.25, comment="Weight of value component")
    weight_growth = Column(Float, default=0.25, comment="Weight of growth component")
    weight_quality = Column(Float, default=0.25, comment="Weight of quality component")
    weight_momentum = Column(Float, default=0.25, comment="Weight of momentum component")

    # Value Score Components
    per_score = Column(Float, comment="PER score component (0-100)")
    pbr_score = Column(Float, comment="PBR score component (0-100)")
    dividend_yield_score = Column(Float, comment="Dividend yield score component (0-100)")
    psr_score = Column(Float, comment="PSR score component (0-100)")

    # Growth Score Components
    revenue_growth_score = Column(Float, comment="Revenue growth score component (0-100)")
    earnings_growth_score = Column(Float, comment="Earnings growth score component (0-100)")
    equity_growth_score = Column(Float, comment="Equity growth score component (0-100)")

    # Quality Score Components
    roe_score = Column(Float, comment="ROE score component (0-100)")
    operating_margin_score = Column(Float, comment="Operating margin score component (0-100)")
    net_margin_score = Column(Float, comment="Net margin score component (0-100)")
    debt_ratio_score = Column(Float, comment="Debt ratio score component (0-100)")
    current_ratio_score = Column(Float, comment="Current ratio score component (0-100)")

    # Momentum Score Components
    rsi_score = Column(Float, comment="RSI score component (0-100)")
    price_trend_score = Column(Float, comment="Price trend score component (0-100)")
    macd_score = Column(Float, comment="MACD score component (0-100)")
    volume_trend_score = Column(Float, comment="Volume trend score component (0-100)")

    # Data Quality Indicators
    data_quality_score = Column(Float, comment="Data completeness score (0-100)")
    missing_value_count = Column(Integer, comment="Number of missing values in calculation")
    total_metric_count = Column(Integer, comment="Total number of metrics evaluated")

    # Metadata
    calculation_method = Column(String(50), default="standard", comment="Calculation method version")
    notes = Column(Text, comment="Additional notes or warnings")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", backref="composite_scores")

    # Composite indexes
    __table_args__ = (
        Index('ix_composite_scores_stock_date', 'stock_id', 'date'),
        Index('ix_composite_scores_score', 'composite_score'),
        Index('ix_composite_scores_date_score', 'date', 'composite_score'),
    )


class Watchlist(Base):
    """Watchlist model for tracking stocks of interest."""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True, comment="User identifier")
    ticker = Column(String(20), nullable=False, index=True, comment="Stock code (denormalized for quick access)")
    reason = Column(Text, comment="Reason for adding to watchlist")
    score = Column(Float, comment="Custom score or rating (0-100)")
    target_price = Column(Numeric(15, 2), comment="Target buy/sell price")
    notes = Column(Text, comment="Additional notes")
    tags = Column(String(200), comment="Comma-separated tags")
    alert_enabled = Column(Boolean, default=False, comment="Whether price alerts are enabled")
    alert_price_upper = Column(Numeric(15, 2), comment="Alert if price goes above this")
    alert_price_lower = Column(Numeric(15, 2), comment="Alert if price goes below this")
    is_active = Column(Boolean, default=True, index=True, comment="Whether watchlist entry is active")
    added_date = Column(DateTime, default=datetime.utcnow, index=True, comment="Date added to watchlist")
    last_viewed = Column(DateTime, comment="Last time user viewed this stock")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="watchlist_entries")
    history = relationship("WatchlistHistory", back_populates="watchlist", cascade="all, delete-orphan")

    # Composite indexes
    __table_args__ = (
        Index('ix_watchlist_user_ticker', 'user_id', 'ticker'),
        Index('ix_watchlist_user_score', 'user_id', 'score'),
        Index('ix_watchlist_user_added', 'user_id', 'added_date'),
    )


class WatchlistHistory(Base):
    """Historical tracking of watchlist stocks' performance and scores."""
    __tablename__ = "watchlist_history"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlist.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, comment="Snapshot date")

    # Price Information
    price = Column(Numeric(15, 2), comment="Stock price at snapshot")
    price_change_pct = Column(Float, comment="Price change % since added to watchlist")
    price_change_amount = Column(Numeric(15, 2), comment="Price change amount since added")
    target_price = Column(Numeric(15, 2), comment="Target price at this snapshot")
    target_price_distance_pct = Column(Float, comment="Distance from target price (%)")

    # Volume and Trading
    volume = Column(BigInteger, comment="Trading volume")
    trading_value = Column(BigInteger, comment="Trading value in KRW")

    # Composite Scores (from CompositeScore table)
    composite_score = Column(Float, comment="Overall composite score (0-100)")
    value_score = Column(Float, comment="Value score (0-100)")
    growth_score = Column(Float, comment="Growth score (0-100)")
    quality_score = Column(Float, comment="Quality score (0-100)")
    momentum_score = Column(Float, comment="Momentum score (0-100)")
    percentile_rank = Column(Float, comment="Percentile rank among all stocks")

    # Score Changes (compared to previous snapshot)
    composite_score_change = Column(Float, comment="Change in composite score since last snapshot")
    value_score_change = Column(Float, comment="Change in value score")
    growth_score_change = Column(Float, comment="Change in growth score")
    quality_score_change = Column(Float, comment="Change in quality score")
    momentum_score_change = Column(Float, comment="Change in momentum score")

    # Stability Score (from StabilityScore table)
    stability_score = Column(Float, comment="Overall stability score (0-100)")
    price_volatility = Column(Float, comment="Price volatility metric")
    beta = Column(Float, comment="Beta coefficient")

    # Key Fundamental Metrics
    per = Column(Float, comment="Price to Earnings Ratio")
    pbr = Column(Float, comment="Price to Book Ratio")
    roe = Column(Float, comment="Return on Equity (%)")
    debt_ratio = Column(Float, comment="Debt Ratio (%)")
    dividend_yield = Column(Float, comment="Dividend Yield (%)")

    # Technical Indicators
    rsi_14 = Column(Float, comment="14-day RSI")
    macd = Column(Float, comment="MACD value")
    macd_histogram = Column(Float, comment="MACD histogram")

    # Criteria Met Status
    meets_criteria = Column(Boolean, comment="Whether stock still meets watchlist criteria")
    criteria_violations = Column(Text, comment="List of criteria violations if any")

    # Performance Metrics
    days_on_watchlist = Column(Integer, comment="Number of days on watchlist")
    total_return_pct = Column(Float, comment="Total return % since added")
    annualized_return_pct = Column(Float, comment="Annualized return %")

    # Metadata
    snapshot_reason = Column(String(50), comment="Reason for snapshot: daily_update, manual, criteria_check")
    notes = Column(Text, comment="Additional notes for this snapshot")

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    watchlist = relationship("Watchlist", back_populates="history")
    stock = relationship("Stock")

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('ix_watchlist_history_watchlist_date', 'watchlist_id', 'date'),
        Index('ix_watchlist_history_stock_date', 'stock_id', 'date'),
        Index('ix_watchlist_history_date', 'date'),
        Index('ix_watchlist_history_performance', 'total_return_pct', 'annualized_return_pct'),
    )


class PortfolioRiskMetrics(Base):
    """Portfolio-level risk metrics and tracking model."""
    __tablename__ = "portfolio_risk_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True, comment="User identifier")
    date = Column(DateTime, nullable=False, index=True, comment="Calculation date")

    # Portfolio Value Metrics
    total_value = Column(BigInteger, nullable=False, comment="Total portfolio value in KRW")
    cash_balance = Column(BigInteger, default=0, comment="Available cash balance in KRW")
    invested_amount = Column(BigInteger, comment="Total invested amount (cost basis)")
    peak_value = Column(BigInteger, comment="All-time peak portfolio value")
    initial_capital = Column(BigInteger, comment="Initial capital at portfolio inception")

    # P&L Metrics
    total_pnl = Column(BigInteger, comment="Total P&L (realized + unrealized) in KRW")
    total_pnl_pct = Column(Float, comment="Total P&L percentage")
    realized_pnl = Column(BigInteger, comment="Total realized profit/loss")
    unrealized_pnl = Column(BigInteger, comment="Total unrealized profit/loss")
    daily_pnl = Column(BigInteger, comment="Daily profit/loss in KRW")
    daily_pnl_pct = Column(Float, comment="Daily profit/loss percentage")

    # Drawdown Metrics
    current_drawdown = Column(Float, nullable=False, index=True, comment="Current drawdown from peak (%)")
    max_drawdown = Column(Float, comment="Maximum drawdown experienced (%)")
    drawdown_duration_days = Column(Integer, comment="Days since peak value")
    is_at_peak = Column(Boolean, default=False, comment="Whether portfolio is at all-time high")

    # Position Metrics
    position_count = Column(Integer, comment="Number of open positions")
    largest_position_pct = Column(Float, comment="Largest single position as % of portfolio")
    largest_position_ticker = Column(String(20), comment="Ticker of largest position")
    total_exposure_pct = Column(Float, comment="Total market exposure as % (invested/total value)")

    # Loss Tracking
    total_loss_from_initial = Column(BigInteger, comment="Total loss from initial capital in KRW")
    total_loss_from_initial_pct = Column(Float, nullable=False, index=True, comment="Total loss % from initial capital")
    total_loss_from_peak = Column(BigInteger, comment="Total loss from peak value in KRW")
    total_loss_from_peak_pct = Column(Float, comment="Total loss % from peak value")

    # Risk Limits Status
    max_position_size_limit = Column(Float, default=10.0, comment="Max position size limit (%)")
    max_loss_limit = Column(Float, default=30.0, comment="Max total loss limit (%)")
    is_trading_halted = Column(Boolean, default=False, index=True, comment="Whether trading is halted due to loss limit")
    trading_halt_reason = Column(Text, comment="Reason for trading halt")
    trading_halt_timestamp = Column(DateTime, comment="When trading was halted")

    # Violation Tracking
    position_size_violations = Column(Integer, default=0, comment="Count of position size limit violations")
    risk_warnings = Column(Text, comment="Active risk warnings")

    # Performance Metrics
    sharpe_ratio = Column(Float, comment="Sharpe ratio (if calculable)")
    win_rate = Column(Float, comment="Win rate % (winning trades / total trades)")
    profit_factor = Column(Float, comment="Profit factor (gross profit / gross loss)")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite indexes
    __table_args__ = (
        Index('ix_portfolio_risk_user_date', 'user_id', 'date'),
        Index('ix_portfolio_risk_drawdown', 'current_drawdown'),
        Index('ix_portfolio_risk_loss', 'total_loss_from_initial_pct'),
        Index('ix_portfolio_risk_halted', 'is_trading_halted', 'user_id'),
    )
