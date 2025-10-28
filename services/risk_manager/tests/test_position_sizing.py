"""
Tests for Position Sizing Module.
Tests Kelly Criterion, fixed percent, and fixed risk position sizing methods.
"""
import pytest
from services.risk_manager.position_sizing import (
    PositionSizer,
    PositionSizingMethod,
    PositionSizingResult
)


@pytest.fixture
def position_sizer():
    """Create position sizer instance."""
    return PositionSizer(
        default_method=PositionSizingMethod.KELLY_HALF,
        max_position_size_pct=10.0,
        default_fixed_pct=5.0,
        default_risk_pct=2.0
    )


def test_kelly_criterion_calculation(position_sizer):
    """Test Kelly Criterion calculation."""
    # Win rate 60%, avg win 15%, avg loss 8%
    kelly = position_sizer.calculate_kelly_criterion(
        win_rate=0.6,
        avg_win_pct=15.0,
        avg_loss_pct=8.0
    )

    # Expected Kelly = (0.6 * 1.875 - 0.4) / 1.875 = 0.386 (38.6%)
    assert 0.35 < kelly < 0.42  # Approximate range


def test_kelly_criterion_negative_expectancy(position_sizer):
    """Test Kelly Criterion with negative expectancy returns 0."""
    # Win rate 40%, avg win 10%, avg loss 15% (negative expectancy)
    kelly = position_sizer.calculate_kelly_criterion(
        win_rate=0.4,
        avg_win_pct=10.0,
        avg_loss_pct=15.0
    )

    assert kelly == 0.0  # Should not bet with negative expectancy


def test_fixed_percent_position_sizing(position_sizer):
    """Test fixed percentage position sizing."""
    result = position_sizer.calculate_position_size(
        portfolio_value=100_000_000,  # 100M KRW
        entry_price=70_000,
        stop_loss_price=63_000,
        method=PositionSizingMethod.FIXED_PERCENT,
        fixed_pct=5.0
    )

    # 5% of 100M = 5M KRW
    # At 70,000 per share = 71 shares (rounded)
    assert result.shares == 71
    assert abs(result.position_pct - 5.0) < 0.2  # Within 0.2%


def test_fixed_risk_position_sizing(position_sizer):
    """Test fixed risk position sizing."""
    result = position_sizer.calculate_position_size(
        portfolio_value=100_000_000,  # 100M KRW
        entry_price=70_000,
        stop_loss_price=63_000,  # Risk of 7,000 per share
        method=PositionSizingMethod.FIXED_RISK,
        risk_pct=2.0
    )

    # 2% risk of 100M = 2M KRW
    # Risk per share = 7,000
    # Shares = 2,000,000 / 7,000 = 285 shares
    assert result.shares == 285
    assert result.risk_amount == 2_000_000


def test_kelly_half_position_sizing(position_sizer):
    """Test Kelly half (conservative Kelly) position sizing."""
    result = position_sizer.calculate_position_size(
        portfolio_value=100_000_000,
        entry_price=70_000,
        stop_loss_price=63_000,
        method=PositionSizingMethod.KELLY_HALF,
        win_rate=0.6,
        avg_win_pct=15.0,
        avg_loss_pct=8.0
    )

    # Kelly = 38.6%, Half Kelly = 19.3%
    # Position value = 19.3M KRW
    # Shares = 275 (approximately)
    assert 250 < result.shares < 300
    assert result.kelly_fraction is not None
    assert 0.15 < result.kelly_fraction < 0.25


def test_kelly_quarter_position_sizing(position_sizer):
    """Test Kelly quarter (very conservative Kelly) position sizing."""
    result = position_sizer.calculate_position_size(
        portfolio_value=100_000_000,
        entry_price=70_000,
        stop_loss_price=63_000,
        method=PositionSizingMethod.KELLY_QUARTER,
        win_rate=0.6,
        avg_win_pct=15.0,
        avg_loss_pct=8.0
    )

    # Kelly = 38.6%, Quarter Kelly = 9.65%
    assert result.shares < 150
    assert result.kelly_fraction is not None
    assert 0.08 < result.kelly_fraction < 0.12


def test_max_position_size_cap(position_sizer):
    """Test that position size is capped at max limit."""
    result = position_sizer.calculate_position_size(
        portfolio_value=100_000_000,
        entry_price=70_000,
        stop_loss_price=63_000,
        method=PositionSizingMethod.FIXED_PERCENT,
        fixed_pct=15.0  # Try to allocate 15%, but max is 10%
    )

    # Should be capped at 10%
    assert result.position_pct <= 10.1  # Allow small rounding error
    assert "[Capped at 10.0% max]" in (result.notes or "")


def test_historical_performance_calculation(position_sizer):
    """Test historical performance metrics calculation."""
    trades = [
        {'pnl_pct': 15.0},
        {'pnl_pct': -8.0},
        {'pnl_pct': 12.0},
        {'pnl_pct': -5.0},
        {'pnl_pct': 20.0},
        {'pnl_pct': -7.0},
        {'pnl_pct': 18.0},
        {'pnl_pct': -6.0}
    ]

    perf = position_sizer.get_historical_performance(trades)

    assert perf['total_trades'] == 8
    assert perf['winning_trades'] == 4
    assert perf['losing_trades'] == 4
    assert perf['win_rate'] == 0.5  # 50%
    assert perf['avg_win_pct'] > 0
    assert perf['avg_loss_pct'] > 0
    assert perf['profit_factor'] > 0


def test_empty_historical_performance(position_sizer):
    """Test historical performance with no trades."""
    perf = position_sizer.get_historical_performance([])

    # Should return defaults
    assert perf['win_rate'] == 0.5
    assert perf['avg_win_pct'] == 10.0
    assert perf['avg_loss_pct'] == 5.0
    assert perf['total_trades'] == 0


def test_kelly_fallback_without_history(position_sizer):
    """Test Kelly method falls back to fixed risk when no history available."""
    result = position_sizer.calculate_position_size(
        portfolio_value=100_000_000,
        entry_price=70_000,
        stop_loss_price=63_000,
        method=PositionSizingMethod.KELLY_HALF
        # No win_rate, avg_win_pct, avg_loss_pct provided
    )

    # Should fallback to fixed risk
    assert "Fixed Risk" in result.method or "Fallback" in (result.notes or "")
    assert result.shares > 0


def test_zero_risk_raises_error(position_sizer):
    """Test that zero risk per share raises ValueError."""
    with pytest.raises(ValueError, match="Risk per share cannot be zero"):
        position_sizer.calculate_position_size(
            portfolio_value=100_000_000,
            entry_price=70_000,
            stop_loss_price=70_000,  # Same as entry price = zero risk
            method=PositionSizingMethod.FIXED_RISK
        )


def test_volatility_adjusted_sizing(position_sizer):
    """Test volatility-adjusted position sizing."""
    # High volatility stock (40%)
    high_vol_result = position_sizer.calculate_position_size(
        portfolio_value=100_000_000,
        entry_price=70_000,
        stop_loss_price=63_000,
        method=PositionSizingMethod.VOLATILITY_ADJUSTED,
        volatility=40.0
    )

    # Low volatility stock (10%)
    low_vol_result = position_sizer.calculate_position_size(
        portfolio_value=100_000_000,
        entry_price=70_000,
        stop_loss_price=63_000,
        method=PositionSizingMethod.VOLATILITY_ADJUSTED,
        volatility=10.0
    )

    # Lower volatility should result in larger position
    assert low_vol_result.shares > high_vol_result.shares


def test_position_sizing_result_dataclass():
    """Test PositionSizingResult dataclass."""
    result = PositionSizingResult(
        shares=100,
        position_value=7_000_000,
        position_pct=7.0,
        method="Kelly Half",
        kelly_fraction=0.193,
        risk_amount=2_000_000,
        notes="Test calculation"
    )

    assert result.shares == 100
    assert result.position_value == 7_000_000
    assert result.position_pct == 7.0
    assert result.method == "Kelly Half"
    assert result.kelly_fraction == 0.193
    assert result.risk_amount == 2_000_000
    assert result.notes == "Test calculation"


def test_realistic_samsung_position_sizing(position_sizer):
    """Test realistic position sizing for Samsung Electronics stock."""
    # Portfolio: 100M KRW
    # Samsung stock: 70,000 KRW per share
    # Stop-loss at -10% = 63,000 KRW
    # Historical: 55% win rate, avg win 18%, avg loss 9%

    result = position_sizer.calculate_position_size(
        portfolio_value=100_000_000,
        entry_price=70_000,
        stop_loss_price=63_000,
        method=PositionSizingMethod.KELLY_HALF,
        win_rate=0.55,
        avg_win_pct=18.0,
        avg_loss_pct=9.0
    )

    # Verify result is reasonable
    assert result.shares > 0
    assert result.position_pct <= 10.0  # Within max limit
    assert result.position_value > 0
    assert result.kelly_fraction > 0

    print(f"\nRealistic Samsung Position Sizing:")
    print(f"  Shares: {result.shares}")
    print(f"  Position Value: {result.position_value:,.0f} KRW")
    print(f"  Position %: {result.position_pct:.2f}%")
    print(f"  Method: {result.method}")
    print(f"  Kelly Fraction: {result.kelly_fraction:.2%}")
    print(f"  Notes: {result.notes}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
