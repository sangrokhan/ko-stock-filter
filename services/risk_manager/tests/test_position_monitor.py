"""
Tests for Position Monitor Service.
Tests stop-loss, trailing stop-loss, take-profit, and emergency liquidation logic.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from shared.database.models import Base, Portfolio, PortfolioRiskMetrics
from services.risk_manager.position_monitor import PositionMonitor, ExitSignal


# Test database setup
@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_position(db_session):
    """Create a sample position for testing."""
    position = Portfolio(
        user_id="test_user",
        ticker="005930",  # Samsung Electronics
        quantity=10,
        avg_price=Decimal("70000"),
        current_price=Decimal("70000"),
        current_value=700000,
        invested_amount=700000,
        unrealized_pnl=0,
        unrealized_pnl_pct=0.0,
        realized_pnl=0,
        stop_loss_price=Decimal("63000"),  # -10%
        stop_loss_pct=10.0,
        take_profit_price=Decimal("84000"),  # +20%
        take_profit_pct=20.0,
        trailing_stop_price=Decimal("63000"),
        trailing_stop_enabled=True,
        trailing_stop_distance_pct=10.0,
        highest_price_since_purchase=Decimal("70000"),
        first_purchase_date=datetime.utcnow()
    )
    db_session.add(position)
    db_session.commit()
    db_session.refresh(position)
    return position


@pytest.fixture
def position_monitor():
    """Create position monitor instance."""
    return PositionMonitor(
        check_stop_loss=True,
        check_trailing_stop=True,
        check_take_profit=True,
        check_emergency_liquidation=True,
        emergency_liquidation_threshold=28.0
    )


def test_stop_loss_trigger(db_session, sample_position, position_monitor):
    """Test that stop-loss is triggered when price falls below threshold."""
    # Price falls to 62,000 (below stop-loss of 63,000)
    sample_position.current_price = Decimal("62000")
    sample_position.unrealized_pnl = (62000 - 70000) * 10
    sample_position.unrealized_pnl_pct = ((62000 - 70000) / 70000) * 100
    db_session.commit()

    result = position_monitor.monitor_positions("test_user", db_session)

    assert result.positions_checked == 1
    assert len(result.exit_signals) == 1
    signal = result.exit_signals[0]
    assert signal.signal_type == "stop_loss"
    assert signal.ticker == "005930"
    assert signal.urgency == "high"


def test_trailing_stop_update(db_session, sample_position, position_monitor):
    """Test that trailing stop moves up when price increases."""
    # Price rises to 80,000
    sample_position.current_price = Decimal("80000")
    db_session.commit()

    result = position_monitor.monitor_positions("test_user", db_session)

    db_session.refresh(sample_position)

    # Highest price should be updated
    assert float(sample_position.highest_price_since_purchase) == 80000.0

    # Trailing stop should move up (10% below 80,000 = 72,000)
    assert float(sample_position.trailing_stop_price) == 72000.0
    assert result.trailing_stops_updated == 1


def test_trailing_stop_trigger(db_session, sample_position, position_monitor):
    """Test that trailing stop triggers when price falls after rising."""
    # First, price rises to 80,000
    sample_position.current_price = Decimal("80000")
    sample_position.highest_price_since_purchase = Decimal("80000")
    sample_position.trailing_stop_price = Decimal("72000")  # 10% below 80,000
    db_session.commit()

    # Then price falls to 71,000 (below trailing stop of 72,000)
    sample_position.current_price = Decimal("71000")
    sample_position.unrealized_pnl = (71000 - 70000) * 10
    sample_position.unrealized_pnl_pct = ((71000 - 70000) / 70000) * 100
    db_session.commit()

    result = position_monitor.monitor_positions("test_user", db_session)

    assert len(result.exit_signals) == 1
    signal = result.exit_signals[0]
    assert signal.signal_type == "trailing_stop"
    assert signal.urgency == "high"


def test_take_profit_trigger(db_session, sample_position, position_monitor):
    """Test that take-profit triggers when price reaches target."""
    # Price rises to 85,000 (above take-profit of 84,000)
    sample_position.current_price = Decimal("85000")
    sample_position.unrealized_pnl = (85000 - 70000) * 10
    sample_position.unrealized_pnl_pct = ((85000 - 70000) / 70000) * 100
    db_session.commit()

    result = position_monitor.monitor_positions("test_user", db_session)

    assert len(result.exit_signals) == 1
    signal = result.exit_signals[0]
    assert signal.signal_type == "take_profit"
    assert signal.ticker == "005930"
    assert signal.urgency == "normal"


def test_emergency_liquidation(db_session, sample_position, position_monitor):
    """Test emergency liquidation when portfolio loss exceeds 28%."""
    # Create risk metrics showing 30% loss
    risk_metrics = PortfolioRiskMetrics(
        user_id="test_user",
        date=datetime.utcnow(),
        total_value=72_000_000,  # Down from 100M
        cash_balance=0,
        invested_amount=72_000_000,
        peak_value=100_000_000,
        initial_capital=100_000_000,
        total_pnl=-28_000_000,
        total_pnl_pct=-28.0,
        realized_pnl=0,
        unrealized_pnl=-28_000_000,
        current_drawdown=28.0,
        total_loss_from_initial_pct=28.0,
        is_trading_halted=False,
        position_count=1,
        max_loss_limit=28.0
    )
    db_session.add(risk_metrics)
    db_session.commit()

    result = position_monitor.monitor_positions("test_user", db_session)

    assert result.emergency_liquidation_triggered
    assert len(result.exit_signals) == 1
    signal = result.exit_signals[0]
    assert signal.signal_type == "emergency_liquidation"
    assert signal.urgency == "critical"


def test_initialize_position_limits(db_session, position_monitor):
    """Test initializing position limits."""
    position = Portfolio(
        user_id="test_user",
        ticker="000660",
        quantity=10,
        avg_price=Decimal("50000"),
        current_price=Decimal("50000"),
        current_value=500000,
        invested_amount=500000,
        unrealized_pnl=0,
        unrealized_pnl_pct=0.0,
        first_purchase_date=datetime.utcnow()
    )
    db_session.add(position)
    db_session.commit()

    position_monitor.initialize_position_limits(
        position=position,
        entry_price=50000.0,
        stop_loss_pct=10.0,
        take_profit_pct=20.0,
        trailing_stop_enabled=True,
        trailing_stop_distance_pct=10.0
    )

    assert float(position.stop_loss_price) == 45000.0
    assert position.stop_loss_pct == 10.0
    assert float(position.take_profit_price) == 60000.0
    assert position.take_profit_pct == 20.0
    assert position.trailing_stop_enabled is True
    assert float(position.highest_price_since_purchase) == 50000.0


def test_no_exit_signals_normal_price(db_session, sample_position, position_monitor):
    """Test that no exit signals are generated when price is within limits."""
    # Price at 75,000 (between stop-loss and take-profit)
    sample_position.current_price = Decimal("75000")
    sample_position.unrealized_pnl = (75000 - 70000) * 10
    sample_position.unrealized_pnl_pct = ((75000 - 70000) / 70000) * 100
    db_session.commit()

    result = position_monitor.monitor_positions("test_user", db_session)

    assert result.positions_checked == 1
    assert len(result.exit_signals) == 0
    assert result.emergency_liquidation_triggered is False


def test_trailing_stop_doesnt_move_down(db_session, sample_position, position_monitor):
    """Test that trailing stop never moves down."""
    # Set high trailing stop from previous peak
    sample_position.highest_price_since_purchase = Decimal("90000")
    sample_position.trailing_stop_price = Decimal("81000")  # 10% below 90,000
    sample_position.current_price = Decimal("85000")  # Lower than peak
    db_session.commit()

    result = position_monitor.monitor_positions("test_user", db_session)

    db_session.refresh(sample_position)

    # Trailing stop should remain at 81,000, not move down
    assert float(sample_position.trailing_stop_price) == 81000.0
    # Highest price should remain at 90,000
    assert float(sample_position.highest_price_since_purchase) == 90000.0


def test_multiple_positions_monitoring(db_session, position_monitor):
    """Test monitoring multiple positions at once."""
    # Create multiple positions
    positions = [
        Portfolio(
            user_id="test_user",
            ticker="005930",
            quantity=10,
            avg_price=Decimal("70000"),
            current_price=Decimal("62000"),  # Below stop-loss
            stop_loss_price=Decimal("63000"),
            stop_loss_pct=10.0,
            trailing_stop_enabled=True,
            highest_price_since_purchase=Decimal("70000")
        ),
        Portfolio(
            user_id="test_user",
            ticker="000660",
            quantity=20,
            avg_price=Decimal("50000"),
            current_price=Decimal("60000"),  # Above take-profit
            take_profit_price=Decimal("60000"),
            take_profit_pct=20.0,
            trailing_stop_enabled=True,
            highest_price_since_purchase=Decimal("50000")
        ),
        Portfolio(
            user_id="test_user",
            ticker="035720",
            quantity=5,
            avg_price=Decimal("100000"),
            current_price=Decimal("105000"),  # Normal
            stop_loss_price=Decimal("90000"),
            take_profit_price=Decimal("120000"),
            trailing_stop_enabled=True,
            highest_price_since_purchase=Decimal("100000")
        )
    ]

    for p in positions:
        db_session.add(p)
    db_session.commit()

    result = position_monitor.monitor_positions("test_user", db_session)

    assert result.positions_checked == 3
    assert len(result.exit_signals) == 2  # One stop-loss, one take-profit
    signal_types = {s.signal_type for s in result.exit_signals}
    assert "stop_loss" in signal_types
    assert "take_profit" in signal_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
