"""add stability scores table

Revision ID: 20251027_1500_002
Revises: 20251027_1400_001
Create Date: 2025-10-27 15:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251027_1500_002'
down_revision = '20251027_1400_001'
branch_labels = None
depends_on = None


def upgrade():
    """Create stability_scores table."""
    op.create_table(
        'stability_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),

        # Price Volatility Metrics
        sa.Column('price_volatility', sa.Float(), nullable=True, comment='Price volatility (std dev of returns)'),
        sa.Column('price_volatility_score', sa.Float(), nullable=True, comment='Price volatility score (0-100, higher is more stable)'),
        sa.Column('returns_mean', sa.Float(), nullable=True, comment='Mean of daily returns'),
        sa.Column('returns_std', sa.Float(), nullable=True, comment='Standard deviation of daily returns'),

        # Beta Coefficient (Market Risk)
        sa.Column('beta', sa.Float(), nullable=True, comment='Beta coefficient (systematic risk vs market)'),
        sa.Column('beta_score', sa.Float(), nullable=True, comment='Beta score (0-100, closer to 1.0 is more stable)'),
        sa.Column('market_correlation', sa.Float(), nullable=True, comment='Correlation with market index'),

        # Volume Stability Metrics
        sa.Column('volume_stability', sa.Float(), nullable=True, comment='Volume stability (coefficient of variation)'),
        sa.Column('volume_stability_score', sa.Float(), nullable=True, comment='Volume stability score (0-100)'),
        sa.Column('volume_mean', sa.BigInteger(), nullable=True, comment='Mean trading volume'),
        sa.Column('volume_std', sa.BigInteger(), nullable=True, comment='Standard deviation of trading volume'),

        # Earnings Consistency Metrics
        sa.Column('earnings_consistency', sa.Float(), nullable=True, comment='Earnings consistency (coefficient of variation)'),
        sa.Column('earnings_consistency_score', sa.Float(), nullable=True, comment='Earnings consistency score (0-100)'),
        sa.Column('earnings_trend', sa.Float(), nullable=True, comment='Earnings trend (slope)'),

        # Debt Stability Metrics
        sa.Column('debt_stability', sa.Float(), nullable=True, comment='Debt stability (trend analysis)'),
        sa.Column('debt_stability_score', sa.Float(), nullable=True, comment='Debt stability score (0-100)'),
        sa.Column('debt_trend', sa.Float(), nullable=True, comment='Debt ratio trend (slope)'),
        sa.Column('debt_ratio_current', sa.Float(), nullable=True, comment='Current debt ratio'),

        # Overall Stability Score
        sa.Column('stability_score', sa.Float(), nullable=False, comment='Overall stability score (0-100)'),

        # Component Weights (for transparency)
        sa.Column('weight_price', sa.Float(), nullable=True, comment='Weight of price volatility component'),
        sa.Column('weight_beta', sa.Float(), nullable=True, comment='Weight of beta component'),
        sa.Column('weight_volume', sa.Float(), nullable=True, comment='Weight of volume stability component'),
        sa.Column('weight_earnings', sa.Float(), nullable=True, comment='Weight of earnings consistency component'),
        sa.Column('weight_debt', sa.Float(), nullable=True, comment='Weight of debt stability component'),

        # Data Quality Indicators
        sa.Column('data_points_price', sa.Integer(), nullable=True, comment='Number of price data points used'),
        sa.Column('data_points_earnings', sa.Integer(), nullable=True, comment='Number of earnings data points used'),
        sa.Column('data_points_debt', sa.Integer(), nullable=True, comment='Number of debt data points used'),
        sa.Column('calculation_period_days', sa.Integer(), nullable=True, comment='Period used for calculation in days'),

        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_stability_scores_stock_id', 'stability_scores', ['stock_id'])
    op.create_index('ix_stability_scores_date', 'stability_scores', ['date'])
    op.create_index('ix_stability_scores_stock_date', 'stability_scores', ['stock_id', 'date'])
    op.create_index('ix_stability_scores_score', 'stability_scores', ['stability_score'])


def downgrade():
    """Drop stability_scores table."""
    op.drop_index('ix_stability_scores_score', table_name='stability_scores')
    op.drop_index('ix_stability_scores_stock_date', table_name='stability_scores')
    op.drop_index('ix_stability_scores_date', table_name='stability_scores')
    op.drop_index('ix_stability_scores_stock_id', table_name='stability_scores')
    op.drop_table('stability_scores')
