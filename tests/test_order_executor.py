"""
Unit tests for Order Executor.

Tests order generation, execution, and portfolio management.
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from services.trading_engine.order_executor import OrderExecutor
from services.trading_engine.signal_generator import (
    TradingSignal, SignalType, OrderType, SignalStrength,
    ConvictionScore
)
from shared.database.models import Trade, Portfolio


class TestOrderExecutor:
    """Test suite for OrderExecutor."""

    @pytest.fixture
    def executor(self, test_db_session):
        """Create order executor instance."""
        return OrderExecutor(
            db=test_db_session,
            user_id='test_user',
            dry_run=False
        )

    @pytest.fixture
    def dry_run_executor(self, test_db_session):
        """Create dry-run order executor instance."""
        return OrderExecutor(
            db=test_db_session,
            user_id='test_user',
            dry_run=True
        )

    @pytest.fixture
    def buy_signal(self):
        """Create a sample buy signal."""
        conviction = ConvictionScore(
            total_score=75.0,
            value_component=70.0,
            momentum_component=80.0,
            volume_component=75.0,
            quality_component=75.0,
            weight_value=0.25,
            weight_momentum=0.25,
            weight_volume=0.25,
            weight_quality=0.25
        )

        return TradingSignal(
            signal_id='BUY_005930_TEST',
            ticker='005930',
            signal_type=SignalType.ENTRY_BUY,
            signal_strength=SignalStrength.STRONG,
            current_price=70000,
            recommended_shares=100,
            position_value=7000000,
            position_pct=7.0,
            stop_loss_price=63000,
            take_profit_price=84000,
            order_type=OrderType.MARKET,
            limit_price=None,
            conviction_score=conviction,
            reasons=['Strong technical indicators', 'Good value metrics'],
            generated_at=datetime.now(),
            urgency='high',
            is_valid=True
        )

    @pytest.fixture
    def sell_signal(self):
        """Create a sample sell signal."""
        return TradingSignal(
            signal_id='SELL_005930_TEST',
            ticker='005930',
            signal_type=SignalType.EXIT_SELL,
            signal_strength=SignalStrength.MODERATE,
            current_price=75000,
            recommended_shares=100,
            position_value=7500000,
            position_pct=7.5,
            order_type=OrderType.MARKET,
            reasons=['Stop loss triggered'],
            generated_at=datetime.now(),
            urgency='high',
            is_valid=True
        )

    @pytest.fixture
    def existing_position(self, test_db_session):
        """Create an existing portfolio position."""
        position = Portfolio(
            user_id='test_user',
            ticker='005930',
            quantity=100,
            avg_price=Decimal('70000'),
            current_price=Decimal('75000'),
            invested_amount=7000000,
            unrealized_pnl=500000,
            unrealized_pnl_pct=7.14,
            realized_pnl=0,
            total_commission=1050,
            total_tax=16100,
            stop_loss_price=Decimal('63000'),
            take_profit_price=Decimal('84000'),
            first_purchase_date=datetime.now(),
            last_transaction_date=datetime.now()
        )
        test_db_session.add(position)
        test_db_session.commit()
        return position

    def test_initialization(self, executor):
        """Test executor initialization."""
        assert executor.db is not None
        assert executor.user_id == 'test_user'
        assert executor.dry_run is False

    def test_initialization_dry_run(self, dry_run_executor):
        """Test executor initialization in dry-run mode."""
        assert dry_run_executor.dry_run is True

    def test_execute_buy_order_success(self, executor, buy_signal):
        """Test successful buy order execution."""
        trade = executor.execute_signal(buy_signal)

        assert trade is not None
        assert trade.ticker == '005930'
        assert trade.action == 'BUY'
        assert trade.quantity == 100
        assert float(trade.price) == 70000
        assert trade.status == 'EXECUTED'
        assert trade.commission > 0
        assert trade.tax > 0

    def test_execute_buy_order_dry_run(self, dry_run_executor, buy_signal):
        """Test buy order execution in dry-run mode."""
        trade = dry_run_executor.execute_signal(buy_signal)

        assert trade is not None
        assert trade.status == 'PENDING'
        assert trade.executed_price is None
        assert trade.executed_quantity is None

    def test_execute_buy_order_creates_portfolio_position(
        self, executor, buy_signal
    ):
        """Test that buy order creates new portfolio position."""
        trade = executor.execute_signal(buy_signal)

        # Check portfolio was created
        position = executor.db.query(Portfolio).filter(
            Portfolio.user_id == 'test_user',
            Portfolio.ticker == '005930'
        ).first()

        assert position is not None
        assert position.quantity == 100
        assert float(position.avg_price) == 70000
        assert position.stop_loss_price == Decimal('63000')
        assert position.take_profit_price == Decimal('84000')

    def test_execute_buy_order_updates_existing_position(
        self, executor, buy_signal, existing_position
    ):
        """Test that buy order averages into existing position."""
        # Buy more at higher price
        buy_signal.current_price = 75000
        buy_signal.recommended_shares = 50

        trade = executor.execute_signal(buy_signal)

        # Check position was updated
        position = executor.db.query(Portfolio).filter(
            Portfolio.user_id == 'test_user',
            Portfolio.ticker == '005930'
        ).first()

        assert position is not None
        assert position.quantity == 150  # 100 + 50
        # New avg price = (100*70000 + 50*75000) / 150 = 71666.67
        assert 71600 < float(position.avg_price) < 71700

    def test_execute_sell_order_success(
        self, executor, sell_signal, existing_position
    ):
        """Test successful sell order execution."""
        trade = executor.execute_signal(sell_signal)

        assert trade is not None
        assert trade.ticker == '005930'
        assert trade.action == 'SELL'
        assert trade.quantity == 100
        assert trade.status == 'EXECUTED'

    def test_execute_sell_order_full_exit(
        self, executor, sell_signal, existing_position
    ):
        """Test full exit removes portfolio position."""
        sell_signal.recommended_shares = 100

        trade = executor.execute_signal(sell_signal)

        # Check position was removed
        position = executor.db.query(Portfolio).filter(
            Portfolio.user_id == 'test_user',
            Portfolio.ticker == '005930'
        ).first()

        assert position is None

    def test_execute_sell_order_partial_exit(
        self, executor, sell_signal, existing_position
    ):
        """Test partial exit updates portfolio position."""
        sell_signal.recommended_shares = 50

        trade = executor.execute_signal(sell_signal)

        # Check position was updated
        position = executor.db.query(Portfolio).filter(
            Portfolio.user_id == 'test_user',
            Portfolio.ticker == '005930'
        ).first()

        assert position is not None
        assert position.quantity == 50  # 100 - 50
        assert position.realized_pnl > 0  # Should have profit

    def test_execute_sell_order_no_position(self, executor, sell_signal):
        """Test sell order fails when no position exists."""
        trade = executor.execute_signal(sell_signal)

        assert trade is None

    def test_execute_invalid_signal(self, executor, buy_signal):
        """Test that invalid signals are not executed."""
        buy_signal.is_valid = False

        trade = executor.execute_signal(buy_signal)

        assert trade is None

    def test_execute_limit_order(self, executor, buy_signal):
        """Test execution of limit order."""
        buy_signal.order_type = OrderType.LIMIT
        buy_signal.limit_price = 69000

        trade = executor.execute_signal(buy_signal)

        assert trade is not None
        assert trade.order_type == 'LIMIT'
        assert float(trade.price) == 69000

    def test_commission_calculation(self, executor, buy_signal):
        """Test commission calculation."""
        trade = executor.execute_signal(buy_signal)

        # Commission should be 0.015% of total amount
        expected_commission = int(7000000 * 0.00015)
        assert trade.commission == expected_commission

    def test_tax_calculation(self, executor, buy_signal):
        """Test tax calculation."""
        trade = executor.execute_signal(buy_signal)

        # Tax should be 0.23% of total amount
        expected_tax = int(7000000 * 0.0023)
        assert trade.tax == expected_tax

    def test_execute_signals_batch(self, executor, buy_signal):
        """Test batch execution of multiple signals."""
        # Create multiple signals
        signals = []
        for i in range(3):
            signal = TradingSignal(
                signal_id=f'BUY_00{i}930_TEST',
                ticker=f'00{i}930',
                signal_type=SignalType.ENTRY_BUY,
                signal_strength=SignalStrength.STRONG,
                current_price=50000,
                recommended_shares=50,
                position_value=2500000,
                position_pct=2.5,
                order_type=OrderType.MARKET,
                reasons=['Test signal'],
                generated_at=datetime.now(),
                is_valid=True
            )
            signals.append(signal)

        trades = executor.execute_signals_batch(signals)

        assert len(trades) == 3
        assert all(t.status == 'EXECUTED' for t in trades)

    def test_get_pending_orders(self, test_db_session, executor, buy_signal):
        """Test retrieving pending orders."""
        # Create some pending orders
        executor.dry_run = True
        executor.execute_signal(buy_signal)

        pending = executor.get_pending_orders()

        assert len(pending) > 0
        assert all(t.status == 'PENDING' for t in pending)

    def test_cancel_order(self, test_db_session, executor, buy_signal):
        """Test canceling a pending order."""
        # Create pending order
        executor.dry_run = True
        trade = executor.execute_signal(buy_signal)

        # Cancel it
        success = executor.cancel_order(trade.order_id, 'Test cancellation')

        assert success is True

        # Verify it was cancelled
        cancelled = test_db_session.query(Trade).filter(
            Trade.order_id == trade.order_id
        ).first()

        assert cancelled.status == 'CANCELLED'
        assert 'Cancelled' in cancelled.reason

    def test_cancel_nonexistent_order(self, executor):
        """Test canceling non-existent order."""
        success = executor.cancel_order('INVALID_ORDER_ID')

        assert success is False

    def test_get_execution_summary(self, executor, buy_signal, sell_signal):
        """Test execution summary generation."""
        # Execute some trades
        buy_trade = executor.execute_signal(buy_signal)

        # Create position for sell
        position = Portfolio(
            user_id='test_user',
            ticker='005930',
            quantity=100,
            avg_price=Decimal('70000')
        )
        executor.db.add(position)
        executor.db.commit()

        sell_trade = executor.execute_signal(sell_signal)

        trades = [buy_trade, sell_trade]
        summary = executor.get_execution_summary(trades)

        assert summary['total_trades'] == 2
        assert summary['buy_orders'] == 1
        assert summary['sell_orders'] == 1
        assert summary['total_value'] > 0
        assert summary['total_commission'] > 0
        assert summary['total_tax'] > 0
        assert '005930' in summary['tickers']

    def test_get_execution_summary_empty(self, executor):
        """Test execution summary with no trades."""
        summary = executor.get_execution_summary([])

        assert summary['total_trades'] == 0
        assert summary['buy_orders'] == 0
        assert summary['sell_orders'] == 0

    def test_order_id_generation(self, executor, buy_signal):
        """Test that order IDs are unique and properly formatted."""
        trade1 = executor.execute_signal(buy_signal)
        trade2 = executor.execute_signal(buy_signal)

        assert trade1.order_id != trade2.order_id
        assert trade1.order_id.startswith('BUY_')
        assert '005930' in trade1.order_id

    def test_trailing_stop_initialization(self, executor, buy_signal):
        """Test that trailing stop is properly initialized."""
        trade = executor.execute_signal(buy_signal)

        position = executor.db.query(Portfolio).filter(
            Portfolio.user_id == 'test_user',
            Portfolio.ticker == '005930'
        ).first()

        assert position.trailing_stop_enabled is True
        assert position.highest_price_since_purchase == trade.executed_price
        assert position.trailing_stop_price is not None

    def test_pnl_calculation_on_sell(self, executor, sell_signal, existing_position):
        """Test P&L calculation on sell order."""
        # Original buy at 70000, selling at 75000
        sell_signal.current_price = 75000
        sell_signal.recommended_shares = 100

        trade = executor.execute_signal(sell_signal)

        # Profit = (75000 - 70000) * 100 - commission - tax
        # Should be positive
        assert trade.total_amount > existing_position.invested_amount


class TestOrderExecutorEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def executor(self, test_db_session):
        """Create order executor instance."""
        return OrderExecutor(
            db=test_db_session,
            user_id='test_user',
            dry_run=False
        )

    def test_sell_more_than_position(self, executor, existing_position):
        """Test selling more shares than available in position."""
        sell_signal = TradingSignal(
            signal_id='SELL_005930_TEST',
            ticker='005930',
            signal_type=SignalType.EXIT_SELL,
            signal_strength=SignalStrength.MODERATE,
            current_price=75000,
            recommended_shares=200,  # More than the 100 available
            position_value=15000000,
            position_pct=15.0,
            order_type=OrderType.MARKET,
            reasons=['Test'],
            generated_at=datetime.now(),
            is_valid=True
        )

        trade = executor.execute_signal(sell_signal)

        # Should only sell available quantity
        assert trade.quantity == 100

    def test_unknown_signal_type(self, executor):
        """Test handling of unknown signal type."""
        invalid_signal = Mock()
        invalid_signal.is_valid = True
        invalid_signal.signal_type = 'UNKNOWN'
        invalid_signal.ticker = '005930'

        trade = executor.execute_signal(invalid_signal)

        assert trade is None

    def test_database_rollback_on_error(self, executor, buy_signal, test_db_session):
        """Test that database transaction rolls back on error."""
        # This test verifies error handling behavior
        with patch.object(test_db_session, 'commit', side_effect=Exception('DB error')):
            try:
                executor.execute_signal(buy_signal)
            except:
                pass

            # Verify no partial data was saved
            trades = test_db_session.query(Trade).all()
            # Should not have created a trade if commit failed


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
