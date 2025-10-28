"""add composite scores table

Revision ID: 20251028_1000_003
Revises: 20251027_1500_002
Create Date: 2025-10-28 10:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251028_1000_003'
down_revision = '20251027_1500_002'
branch_labels = None
depends_on = None


def upgrade():
    """Create composite_scores table."""
    op.create_table(
        'composite_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),

        # Component Scores (0-100 scale)
        sa.Column('value_score', sa.Float(), nullable=True, comment='Value score based on PER, PBR, dividend yield (0-100)'),
        sa.Column('growth_score', sa.Float(), nullable=True, comment='Growth score based on earnings/revenue growth (0-100)'),
        sa.Column('quality_score', sa.Float(), nullable=True, comment='Quality score based on ROE, margins, debt (0-100)'),
        sa.Column('momentum_score', sa.Float(), nullable=True, comment='Momentum score based on price trend, RSI (0-100)'),

        # Overall Composite Score
        sa.Column('composite_score', sa.Float(), nullable=False, comment='Overall composite score (0-100)'),
        sa.Column('percentile_rank', sa.Float(), nullable=True, comment='Percentile rank among all stocks (0-100)'),

        # Component Weights (for transparency and customization)
        sa.Column('weight_value', sa.Float(), nullable=True, comment='Weight of value component'),
        sa.Column('weight_growth', sa.Float(), nullable=True, comment='Weight of growth component'),
        sa.Column('weight_quality', sa.Float(), nullable=True, comment='Weight of quality component'),
        sa.Column('weight_momentum', sa.Float(), nullable=True, comment='Weight of momentum component'),

        # Value Score Components
        sa.Column('per_score', sa.Float(), nullable=True, comment='PER score component (0-100)'),
        sa.Column('pbr_score', sa.Float(), nullable=True, comment='PBR score component (0-100)'),
        sa.Column('dividend_yield_score', sa.Float(), nullable=True, comment='Dividend yield score component (0-100)'),
        sa.Column('psr_score', sa.Float(), nullable=True, comment='PSR score component (0-100)'),

        # Growth Score Components
        sa.Column('revenue_growth_score', sa.Float(), nullable=True, comment='Revenue growth score component (0-100)'),
        sa.Column('earnings_growth_score', sa.Float(), nullable=True, comment='Earnings growth score component (0-100)'),
        sa.Column('equity_growth_score', sa.Float(), nullable=True, comment='Equity growth score component (0-100)'),

        # Quality Score Components
        sa.Column('roe_score', sa.Float(), nullable=True, comment='ROE score component (0-100)'),
        sa.Column('operating_margin_score', sa.Float(), nullable=True, comment='Operating margin score component (0-100)'),
        sa.Column('net_margin_score', sa.Float(), nullable=True, comment='Net margin score component (0-100)'),
        sa.Column('debt_ratio_score', sa.Float(), nullable=True, comment='Debt ratio score component (0-100)'),
        sa.Column('current_ratio_score', sa.Float(), nullable=True, comment='Current ratio score component (0-100)'),

        # Momentum Score Components
        sa.Column('rsi_score', sa.Float(), nullable=True, comment='RSI score component (0-100)'),
        sa.Column('price_trend_score', sa.Float(), nullable=True, comment='Price trend score component (0-100)'),
        sa.Column('macd_score', sa.Float(), nullable=True, comment='MACD score component (0-100)'),
        sa.Column('volume_trend_score', sa.Float(), nullable=True, comment='Volume trend score component (0-100)'),

        # Data Quality Indicators
        sa.Column('data_quality_score', sa.Float(), nullable=True, comment='Data completeness score (0-100)'),
        sa.Column('missing_value_count', sa.Integer(), nullable=True, comment='Number of missing values in calculation'),
        sa.Column('total_metric_count', sa.Integer(), nullable=True, comment='Total number of metrics evaluated'),

        # Metadata
        sa.Column('calculation_method', sa.String(50), nullable=True, comment='Calculation method version'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Additional notes or warnings'),

        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_composite_scores_stock_id', 'composite_scores', ['stock_id'])
    op.create_index('ix_composite_scores_date', 'composite_scores', ['date'])
    op.create_index('ix_composite_scores_stock_date', 'composite_scores', ['stock_id', 'date'])
    op.create_index('ix_composite_scores_score', 'composite_scores', ['composite_score'])
    op.create_index('ix_composite_scores_date_score', 'composite_scores', ['date', 'composite_score'])


def downgrade():
    """Drop composite_scores table."""
    op.drop_index('ix_composite_scores_date_score', 'composite_scores')
    op.drop_index('ix_composite_scores_score', 'composite_scores')
    op.drop_index('ix_composite_scores_stock_date', 'composite_scores')
    op.drop_index('ix_composite_scores_date', 'composite_scores')
    op.drop_index('ix_composite_scores_stock_id', 'composite_scores')
    op.drop_table('composite_scores')
