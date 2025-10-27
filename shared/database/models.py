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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite indexes
    __table_args__ = (
        Index('ix_portfolios_user_ticker', 'user_id', 'ticker', unique=True),
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

    # Composite indexes
    __table_args__ = (
        Index('ix_watchlist_user_ticker', 'user_id', 'ticker'),
        Index('ix_watchlist_user_score', 'user_id', 'score'),
        Index('ix_watchlist_user_added', 'user_id', 'added_date'),
    )
