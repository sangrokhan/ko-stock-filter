"""Initial database schema for Korean stock trading system

Revision ID: 20251027_1400_001
Revises:
Create Date: 2025-10-27 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251027_1400_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for the stock trading system."""

    # Create stocks table
    op.create_table(
        'stocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False, comment='Stock code (e.g., 005930 for Samsung)'),
        sa.Column('name_kr', sa.String(length=100), nullable=False, comment='Korean name'),
        sa.Column('name_en', sa.String(length=100), nullable=True, comment='English name'),
        sa.Column('market', sa.String(length=20), nullable=True, comment='KOSPI, KOSDAQ, KONEX, etc.'),
        sa.Column('sector', sa.String(length=50), nullable=True, comment='Business sector'),
        sa.Column('industry', sa.String(length=100), nullable=True, comment='Industry classification'),
        sa.Column('market_cap', sa.BigInteger(), nullable=True, comment='Market capitalization in KRW'),
        sa.Column('listed_shares', sa.BigInteger(), nullable=True, comment='Total number of listed shares'),
        sa.Column('listed_date', sa.DateTime(), nullable=True, comment='IPO date'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='Whether stock is actively traded'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stocks_id'), 'stocks', ['id'], unique=False)
    op.create_index(op.f('ix_stocks_ticker'), 'stocks', ['ticker'], unique=True)
    op.create_index(op.f('ix_stocks_market'), 'stocks', ['market'], unique=False)
    op.create_index(op.f('ix_stocks_sector'), 'stocks', ['sector'], unique=False)
    op.create_index(op.f('ix_stocks_is_active'), 'stocks', ['is_active'], unique=False)

    # Create stock_prices table
    op.create_table(
        'stock_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False, comment='Trading date'),
        sa.Column('open', sa.Numeric(precision=15, scale=2), nullable=False, comment='Opening price'),
        sa.Column('high', sa.Numeric(precision=15, scale=2), nullable=False, comment='Highest price'),
        sa.Column('low', sa.Numeric(precision=15, scale=2), nullable=False, comment='Lowest price'),
        sa.Column('close', sa.Numeric(precision=15, scale=2), nullable=False, comment='Closing price'),
        sa.Column('volume', sa.BigInteger(), nullable=False, comment='Trading volume'),
        sa.Column('adjusted_close', sa.Numeric(precision=15, scale=2), nullable=True, comment='Adjusted closing price for splits/dividends'),
        sa.Column('trading_value', sa.BigInteger(), nullable=True, comment='Total trading value in KRW'),
        sa.Column('change_pct', sa.Float(), nullable=True, comment='Daily change percentage'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_prices_id'), 'stock_prices', ['id'], unique=False)
    op.create_index(op.f('ix_stock_prices_stock_id'), 'stock_prices', ['stock_id'], unique=False)
    op.create_index(op.f('ix_stock_prices_date'), 'stock_prices', ['date'], unique=False)
    op.create_index('ix_stock_prices_stock_date', 'stock_prices', ['stock_id', 'date'], unique=False)
    op.create_index('ix_stock_prices_date_volume', 'stock_prices', ['date', 'volume'], unique=False)

    # Create technical_indicators table
    op.create_table(
        'technical_indicators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False, comment='Indicator calculation date'),
        # Momentum Indicators
        sa.Column('rsi_14', sa.Float(), nullable=True, comment='14-day Relative Strength Index'),
        sa.Column('rsi_9', sa.Float(), nullable=True, comment='9-day Relative Strength Index'),
        sa.Column('stochastic_k', sa.Float(), nullable=True, comment='Stochastic %K'),
        sa.Column('stochastic_d', sa.Float(), nullable=True, comment='Stochastic %D'),
        # Trend Indicators
        sa.Column('macd', sa.Float(), nullable=True, comment='MACD line'),
        sa.Column('macd_signal', sa.Float(), nullable=True, comment='MACD signal line'),
        sa.Column('macd_histogram', sa.Float(), nullable=True, comment='MACD histogram'),
        sa.Column('adx', sa.Float(), nullable=True, comment='Average Directional Index'),
        # Moving Averages
        sa.Column('sma_5', sa.Float(), nullable=True, comment='5-day Simple Moving Average'),
        sa.Column('sma_20', sa.Float(), nullable=True, comment='20-day Simple Moving Average'),
        sa.Column('sma_50', sa.Float(), nullable=True, comment='50-day Simple Moving Average'),
        sa.Column('sma_120', sa.Float(), nullable=True, comment='120-day Simple Moving Average'),
        sa.Column('sma_200', sa.Float(), nullable=True, comment='200-day Simple Moving Average'),
        sa.Column('ema_12', sa.Float(), nullable=True, comment='12-day Exponential Moving Average'),
        sa.Column('ema_26', sa.Float(), nullable=True, comment='26-day Exponential Moving Average'),
        # Volatility Indicators
        sa.Column('bollinger_upper', sa.Float(), nullable=True, comment='Bollinger Upper Band'),
        sa.Column('bollinger_middle', sa.Float(), nullable=True, comment='Bollinger Middle Band'),
        sa.Column('bollinger_lower', sa.Float(), nullable=True, comment='Bollinger Lower Band'),
        sa.Column('atr', sa.Float(), nullable=True, comment='Average True Range'),
        # Volume Indicators
        sa.Column('obv', sa.BigInteger(), nullable=True, comment='On Balance Volume'),
        sa.Column('volume_ma_20', sa.BigInteger(), nullable=True, comment='20-day Volume Moving Average'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_technical_indicators_id'), 'technical_indicators', ['id'], unique=False)
    op.create_index(op.f('ix_technical_indicators_stock_id'), 'technical_indicators', ['stock_id'], unique=False)
    op.create_index(op.f('ix_technical_indicators_date'), 'technical_indicators', ['date'], unique=False)
    op.create_index('ix_tech_indicators_stock_date', 'technical_indicators', ['stock_id', 'date'], unique=False)

    # Create fundamental_indicators table
    op.create_table(
        'fundamental_indicators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False, comment='Reporting date or calculation date'),
        # Valuation Ratios
        sa.Column('per', sa.Float(), nullable=True, comment='Price to Earnings Ratio'),
        sa.Column('pbr', sa.Float(), nullable=True, comment='Price to Book Ratio'),
        sa.Column('pcr', sa.Float(), nullable=True, comment='Price to Cashflow Ratio'),
        sa.Column('psr', sa.Float(), nullable=True, comment='Price to Sales Ratio'),
        # Profitability Ratios
        sa.Column('roe', sa.Float(), nullable=True, comment='Return on Equity (%)'),
        sa.Column('roa', sa.Float(), nullable=True, comment='Return on Assets (%)'),
        sa.Column('roic', sa.Float(), nullable=True, comment='Return on Invested Capital (%)'),
        sa.Column('operating_margin', sa.Float(), nullable=True, comment='Operating Profit Margin (%)'),
        sa.Column('net_margin', sa.Float(), nullable=True, comment='Net Profit Margin (%)'),
        # Financial Health Ratios
        sa.Column('debt_ratio', sa.Float(), nullable=True, comment='Total Debt to Total Assets (%)'),
        sa.Column('debt_to_equity', sa.Float(), nullable=True, comment='Debt to Equity Ratio'),
        sa.Column('current_ratio', sa.Float(), nullable=True, comment='Current Assets to Current Liabilities'),
        sa.Column('quick_ratio', sa.Float(), nullable=True, comment='Quick Ratio (Acid Test)'),
        sa.Column('interest_coverage', sa.Float(), nullable=True, comment='Interest Coverage Ratio'),
        # Growth Metrics
        sa.Column('revenue_growth', sa.Float(), nullable=True, comment='YoY Revenue Growth (%)'),
        sa.Column('earnings_growth', sa.Float(), nullable=True, comment='YoY Earnings Growth (%)'),
        sa.Column('equity_growth', sa.Float(), nullable=True, comment='YoY Equity Growth (%)'),
        # Dividend Metrics
        sa.Column('dividend_yield', sa.Float(), nullable=True, comment='Dividend Yield (%)'),
        sa.Column('dividend_payout_ratio', sa.Float(), nullable=True, comment='Dividend Payout Ratio (%)'),
        # Per Share Metrics
        sa.Column('eps', sa.Float(), nullable=True, comment='Earnings Per Share'),
        sa.Column('bps', sa.Float(), nullable=True, comment='Book value Per Share'),
        sa.Column('cps', sa.Float(), nullable=True, comment='Cashflow Per Share'),
        sa.Column('sps', sa.Float(), nullable=True, comment='Sales Per Share'),
        sa.Column('dps', sa.Float(), nullable=True, comment='Dividend Per Share'),
        # Absolute Values (in KRW millions)
        sa.Column('revenue', sa.BigInteger(), nullable=True, comment='Total Revenue'),
        sa.Column('operating_profit', sa.BigInteger(), nullable=True, comment='Operating Profit'),
        sa.Column('net_income', sa.BigInteger(), nullable=True, comment='Net Income'),
        sa.Column('total_assets', sa.BigInteger(), nullable=True, comment='Total Assets'),
        sa.Column('total_equity', sa.BigInteger(), nullable=True, comment='Total Equity'),
        sa.Column('total_debt', sa.BigInteger(), nullable=True, comment='Total Debt'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fundamental_indicators_id'), 'fundamental_indicators', ['id'], unique=False)
    op.create_index(op.f('ix_fundamental_indicators_stock_id'), 'fundamental_indicators', ['stock_id'], unique=False)
    op.create_index(op.f('ix_fundamental_indicators_date'), 'fundamental_indicators', ['date'], unique=False)
    op.create_index('ix_fund_indicators_stock_date', 'fundamental_indicators', ['stock_id', 'date'], unique=False)
    op.create_index('ix_fund_indicators_per_pbr', 'fundamental_indicators', ['per', 'pbr'], unique=False)
    op.create_index('ix_fund_indicators_roe', 'fundamental_indicators', ['roe'], unique=False)

    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.String(length=50), nullable=False, comment='Unique order identifier'),
        sa.Column('ticker', sa.String(length=20), nullable=False, comment='Stock code'),
        sa.Column('action', sa.String(length=10), nullable=False, comment='BUY, SELL'),
        sa.Column('order_type', sa.String(length=20), nullable=False, comment='MARKET, LIMIT, STOP_LOSS'),
        sa.Column('quantity', sa.Integer(), nullable=False, comment='Number of shares'),
        sa.Column('price', sa.Numeric(precision=15, scale=2), nullable=True, comment='Order price (limit/stop price)'),
        sa.Column('executed_price', sa.Numeric(precision=15, scale=2), nullable=True, comment='Actual execution price'),
        sa.Column('executed_quantity', sa.Integer(), nullable=True, comment='Actual executed quantity'),
        sa.Column('total_amount', sa.BigInteger(), nullable=True, comment='Total transaction amount in KRW'),
        sa.Column('commission', sa.Integer(), nullable=True, comment='Commission fees in KRW'),
        sa.Column('tax', sa.Integer(), nullable=True, comment='Tax amount in KRW'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='PENDING, EXECUTED, PARTIALLY_FILLED, CANCELLED, FAILED'),
        sa.Column('reason', sa.Text(), nullable=True, comment='Reason for trade or failure reason'),
        sa.Column('strategy', sa.String(length=50), nullable=True, comment='Trading strategy that generated this order'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='Order creation timestamp'),
        sa.Column('executed_at', sa.DateTime(), nullable=True, comment='Execution timestamp'),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True, comment='Cancellation timestamp'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trades_id'), 'trades', ['id'], unique=False)
    op.create_index(op.f('ix_trades_order_id'), 'trades', ['order_id'], unique=True)
    op.create_index(op.f('ix_trades_ticker'), 'trades', ['ticker'], unique=False)
    op.create_index(op.f('ix_trades_action'), 'trades', ['action'], unique=False)
    op.create_index(op.f('ix_trades_status'), 'trades', ['status'], unique=False)
    op.create_index(op.f('ix_trades_created_at'), 'trades', ['created_at'], unique=False)
    op.create_index(op.f('ix_trades_executed_at'), 'trades', ['executed_at'], unique=False)
    op.create_index('ix_trades_ticker_date', 'trades', ['ticker', 'created_at'], unique=False)
    op.create_index('ix_trades_status_date', 'trades', ['status', 'created_at'], unique=False)

    # Create portfolios table
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=50), nullable=False, comment='User identifier'),
        sa.Column('ticker', sa.String(length=20), nullable=False, comment='Stock code'),
        sa.Column('quantity', sa.Integer(), nullable=False, comment='Number of shares held'),
        sa.Column('avg_price', sa.Numeric(precision=15, scale=2), nullable=False, comment='Average purchase price per share'),
        sa.Column('current_price', sa.Numeric(precision=15, scale=2), nullable=True, comment='Current market price per share'),
        sa.Column('current_value', sa.BigInteger(), nullable=True, comment='Current total value (quantity * current_price)'),
        sa.Column('invested_amount', sa.BigInteger(), nullable=True, comment='Total invested amount (quantity * avg_price)'),
        sa.Column('unrealized_pnl', sa.BigInteger(), nullable=True, comment='Unrealized profit/loss in KRW'),
        sa.Column('unrealized_pnl_pct', sa.Float(), nullable=True, comment='Unrealized profit/loss percentage'),
        sa.Column('realized_pnl', sa.BigInteger(), nullable=True, comment='Realized profit/loss in KRW'),
        sa.Column('total_commission', sa.Integer(), nullable=True, comment='Total commission paid'),
        sa.Column('total_tax', sa.Integer(), nullable=True, comment='Total tax paid'),
        sa.Column('first_purchase_date', sa.DateTime(), nullable=True, comment='Date of first purchase'),
        sa.Column('last_transaction_date', sa.DateTime(), nullable=True, comment='Date of last transaction'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolios_id'), 'portfolios', ['id'], unique=False)
    op.create_index(op.f('ix_portfolios_user_id'), 'portfolios', ['user_id'], unique=False)
    op.create_index(op.f('ix_portfolios_ticker'), 'portfolios', ['ticker'], unique=False)
    op.create_index('ix_portfolios_user_ticker', 'portfolios', ['user_id', 'ticker'], unique=True)

    # Create watchlist table
    op.create_table(
        'watchlist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=50), nullable=False, comment='User identifier'),
        sa.Column('ticker', sa.String(length=20), nullable=False, comment='Stock code (denormalized for quick access)'),
        sa.Column('reason', sa.Text(), nullable=True, comment='Reason for adding to watchlist'),
        sa.Column('score', sa.Float(), nullable=True, comment='Custom score or rating (0-100)'),
        sa.Column('target_price', sa.Numeric(precision=15, scale=2), nullable=True, comment='Target buy/sell price'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Additional notes'),
        sa.Column('tags', sa.String(length=200), nullable=True, comment='Comma-separated tags'),
        sa.Column('alert_enabled', sa.Boolean(), nullable=True, comment='Whether price alerts are enabled'),
        sa.Column('alert_price_upper', sa.Numeric(precision=15, scale=2), nullable=True, comment='Alert if price goes above this'),
        sa.Column('alert_price_lower', sa.Numeric(precision=15, scale=2), nullable=True, comment='Alert if price goes below this'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='Whether watchlist entry is active'),
        sa.Column('added_date', sa.DateTime(), nullable=True, comment='Date added to watchlist'),
        sa.Column('last_viewed', sa.DateTime(), nullable=True, comment='Last time user viewed this stock'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_watchlist_id'), 'watchlist', ['id'], unique=False)
    op.create_index(op.f('ix_watchlist_stock_id'), 'watchlist', ['stock_id'], unique=False)
    op.create_index(op.f('ix_watchlist_user_id'), 'watchlist', ['user_id'], unique=False)
    op.create_index(op.f('ix_watchlist_ticker'), 'watchlist', ['ticker'], unique=False)
    op.create_index(op.f('ix_watchlist_is_active'), 'watchlist', ['is_active'], unique=False)
    op.create_index(op.f('ix_watchlist_added_date'), 'watchlist', ['added_date'], unique=False)
    op.create_index('ix_watchlist_user_ticker', 'watchlist', ['user_id', 'ticker'], unique=False)
    op.create_index('ix_watchlist_user_score', 'watchlist', ['user_id', 'score'], unique=False)
    op.create_index('ix_watchlist_user_added', 'watchlist', ['user_id', 'added_date'], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('watchlist')
    op.drop_table('portfolios')
    op.drop_table('trades')
    op.drop_table('fundamental_indicators')
    op.drop_table('technical_indicators')
    op.drop_table('stock_prices')
    op.drop_table('stocks')
