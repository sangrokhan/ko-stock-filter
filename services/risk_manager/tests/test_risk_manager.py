"""
Unit tests for Risk Manager Service.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from services.risk_manager.main import RiskManagerService, RiskParameters
from shared.database.models import Portfolio, PortfolioRiskMetrics
from shared.database.connection import SessionLocal


class TestRiskManagerService:
    """Test cases for RiskManagerService."""

    @pytest.fixture
    def risk_manager(self):
        """Create risk manager instance."""
        return RiskManagerService()

    @pytest.fixture
    def custom_risk_manager(self):
        """Create risk manager with custom parameters."""
        params = RiskParameters(
            max_position_size=15.0,
            max_portfolio_risk=3.0,
            max_drawdown=25.0,
            stop_loss_pct=7.0,
            max_leverage=1.5,
            max_total_loss=35.0
        )
        return RiskManagerService(params)

    def test_initialization_default_params(self, risk_manager):
        """Test initialization with default parameters."""
        assert risk_manager.risk_params.max_position_size == 10.0
        assert risk_manager.risk_params.max_total_loss == 30.0
        assert risk_manager.running == False

    def test_initialization_custom_params(self, custom_risk_manager):
        """Test initialization with custom parameters."""
        assert custom_risk_manager.risk_params.max_position_size == 15.0
        assert custom_risk_manager.risk_params.max_total_loss == 35.0

    def test_start_stop_service(self, risk_manager):
        """Test starting and stopping the service."""
        risk_manager.start()
        assert risk_manager.running == True

        risk_manager.stop()
        assert risk_manager.running == False

    def test_calculate_position_size(self, risk_manager):
        """Test position size calculation."""
        ticker = "005930"
        entry_price = 70000
        stop_loss_price = 66500  # 5% stop loss
        portfolio_value = 10000000  # 10M KRW

        shares = risk_manager.calculate_position_size(
            ticker, entry_price, stop_loss_price, portfolio_value
        )

        # Verify shares are calculated correctly
        assert shares > 0
        position_value = shares * entry_price
        position_pct = (position_value / portfolio_value) * 100
        assert position_pct <= risk_manager.risk_params.max_position_size

    def test_calculate_position_size_zero_risk(self, risk_manager):
        """Test that zero risk per share raises error."""
        with pytest.raises(ValueError, match="Risk per share cannot be zero"):
            risk_manager.calculate_position_size(
                "005930", 70000, 70000, 10000000
            )

    def test_validate_order_sell_always_allowed(self, risk_manager):
        """Test that sell orders are always allowed."""
        # Note: This requires a database session, so we'll mock it
        # In real tests, you'd use a test database
        pass

    def test_validate_order_halted_trading(self, risk_manager):
        """Test that buy orders are blocked when trading is halted."""
        # Note: This requires a database session with halted portfolio
        pass

    def test_validate_order_position_size_exceeded(self, risk_manager):
        """Test that oversized positions are rejected."""
        # Note: This requires a database session
        pass


def test_risk_parameters_validation():
    """Test that risk parameters can be created with various values."""
    params = RiskParameters(
        max_position_size=5.0,
        max_portfolio_risk=1.0,
        max_drawdown=15.0,
        stop_loss_pct=3.0,
        max_leverage=1.0,
        max_total_loss=20.0
    )

    assert params.max_position_size == 5.0
    assert params.max_total_loss == 20.0


def test_portfolio_metrics_empty_portfolio():
    """Test metrics calculation for empty portfolio."""
    # This would require actual database testing
    # You'd create a test database, add test data, and verify metrics
    pass


if __name__ == "__main__":
    # Run simple smoke tests
    print("Running Risk Manager smoke tests...")

    # Test 1: Create service
    service = RiskManagerService()
    print("✓ Service created successfully")

    # Test 2: Start/stop
    service.start()
    assert service.running
    print("✓ Service started")

    service.stop()
    assert not service.running
    print("✓ Service stopped")

    # Test 3: Position size calculation
    shares = service.calculate_position_size(
        ticker="005930",
        entry_price=70000,
        stop_loss_price=66500,
        portfolio_value=10000000
    )
    print(f"✓ Position size calculated: {shares} shares")

    # Test 4: Custom parameters
    custom_service = RiskManagerService(
        RiskParameters(
            max_position_size=15.0,
            max_portfolio_risk=3.0,
            max_drawdown=25.0,
            stop_loss_pct=7.0,
            max_leverage=1.5,
            max_total_loss=35.0
        )
    )
    assert custom_service.risk_params.max_total_loss == 35.0
    print("✓ Custom parameters working")

    print("\n✓ All smoke tests passed!")
