"""add watchlist history table

Revision ID: 20251028_1100_004
Revises: 20251028_1000_003
Create Date: 2025-10-28 11:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Numeric, BigInteger, Text


# revision identifiers, used by Alembic.
revision = '20251028_1100_004'
down_revision = '20251028_1000_003'
branch_labels = None
depends_on = None


def upgrade():
    """Create watchlist_history table and update watchlist table."""

    # Create watchlist_history table
    op.create_table(
        'watchlist_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('watchlist_id', sa.Integer(), nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False, comment='Snapshot date'),

        # Price Information
        sa.Column('price', Numeric(15, 2), nullable=True, comment='Stock price at snapshot'),
        sa.Column('price_change_pct', sa.Float(), nullable=True, comment='Price change % since added to watchlist'),
        sa.Column('price_change_amount', Numeric(15, 2), nullable=True, comment='Price change amount since added'),
        sa.Column('target_price', Numeric(15, 2), nullable=True, comment='Target price at this snapshot'),
        sa.Column('target_price_distance_pct', sa.Float(), nullable=True, comment='Distance from target price (%)'),

        # Volume and Trading
        sa.Column('volume', BigInteger, nullable=True, comment='Trading volume'),
        sa.Column('trading_value', BigInteger, nullable=True, comment='Trading value in KRW'),

        # Composite Scores (from CompositeScore table)
        sa.Column('composite_score', sa.Float(), nullable=True, comment='Overall composite score (0-100)'),
        sa.Column('value_score', sa.Float(), nullable=True, comment='Value score (0-100)'),
        sa.Column('growth_score', sa.Float(), nullable=True, comment='Growth score (0-100)'),
        sa.Column('quality_score', sa.Float(), nullable=True, comment='Quality score (0-100)'),
        sa.Column('momentum_score', sa.Float(), nullable=True, comment='Momentum score (0-100)'),
        sa.Column('percentile_rank', sa.Float(), nullable=True, comment='Percentile rank among all stocks'),

        # Score Changes (compared to previous snapshot)
        sa.Column('composite_score_change', sa.Float(), nullable=True, comment='Change in composite score since last snapshot'),
        sa.Column('value_score_change', sa.Float(), nullable=True, comment='Change in value score'),
        sa.Column('growth_score_change', sa.Float(), nullable=True, comment='Change in growth score'),
        sa.Column('quality_score_change', sa.Float(), nullable=True, comment='Change in quality score'),
        sa.Column('momentum_score_change', sa.Float(), nullable=True, comment='Change in momentum score'),

        # Stability Score (from StabilityScore table)
        sa.Column('stability_score', sa.Float(), nullable=True, comment='Overall stability score (0-100)'),
        sa.Column('price_volatility', sa.Float(), nullable=True, comment='Price volatility metric'),
        sa.Column('beta', sa.Float(), nullable=True, comment='Beta coefficient'),

        # Key Fundamental Metrics
        sa.Column('per', sa.Float(), nullable=True, comment='Price to Earnings Ratio'),
        sa.Column('pbr', sa.Float(), nullable=True, comment='Price to Book Ratio'),
        sa.Column('roe', sa.Float(), nullable=True, comment='Return on Equity (%)'),
        sa.Column('debt_ratio', sa.Float(), nullable=True, comment='Debt Ratio (%)'),
        sa.Column('dividend_yield', sa.Float(), nullable=True, comment='Dividend Yield (%)'),

        # Technical Indicators
        sa.Column('rsi_14', sa.Float(), nullable=True, comment='14-day RSI'),
        sa.Column('macd', sa.Float(), nullable=True, comment='MACD value'),
        sa.Column('macd_histogram', sa.Float(), nullable=True, comment='MACD histogram'),

        # Criteria Met Status
        sa.Column('meets_criteria', sa.Boolean(), nullable=True, comment='Whether stock still meets watchlist criteria'),
        sa.Column('criteria_violations', Text, nullable=True, comment='List of criteria violations if any'),

        # Performance Metrics
        sa.Column('days_on_watchlist', sa.Integer(), nullable=True, comment='Number of days on watchlist'),
        sa.Column('total_return_pct', sa.Float(), nullable=True, comment='Total return % since added'),
        sa.Column('annualized_return_pct', sa.Float(), nullable=True, comment='Annualized return %'),

        # Metadata
        sa.Column('snapshot_reason', sa.String(50), nullable=True, comment='Reason for snapshot: daily_update, manual, criteria_check'),
        sa.Column('notes', Text, nullable=True, comment='Additional notes for this snapshot'),

        sa.Column('created_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['watchlist_id'], ['watchlist.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ondelete='CASCADE'),
    )

    # Create indexes for watchlist_history
    op.create_index('ix_watchlist_history_watchlist_id', 'watchlist_history', ['watchlist_id'])
    op.create_index('ix_watchlist_history_stock_id', 'watchlist_history', ['stock_id'])
    op.create_index('ix_watchlist_history_date', 'watchlist_history', ['date'])
    op.create_index('ix_watchlist_history_watchlist_date', 'watchlist_history', ['watchlist_id', 'date'])
    op.create_index('ix_watchlist_history_stock_date', 'watchlist_history', ['stock_id', 'date'])
    op.create_index('ix_watchlist_history_performance', 'watchlist_history', ['total_return_pct', 'annualized_return_pct'])


def downgrade():
    """Drop watchlist_history table."""
    op.drop_index('ix_watchlist_history_performance', 'watchlist_history')
    op.drop_index('ix_watchlist_history_stock_date', 'watchlist_history')
    op.drop_index('ix_watchlist_history_watchlist_date', 'watchlist_history')
    op.drop_index('ix_watchlist_history_date', 'watchlist_history')
    op.drop_index('ix_watchlist_history_stock_id', 'watchlist_history')
    op.drop_index('ix_watchlist_history_watchlist_id', 'watchlist_history')
    op.drop_table('watchlist_history')
