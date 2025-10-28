"""
Order Execution Module Example.

Demonstrates the comprehensive order execution system with:
- Paper trading execution
- Realistic slippage simulation
- Order status tracking
- Commission and fee calculation
- Portfolio management
- Trade logging
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from shared.database.connection import get_db_session
from services.trading_engine.broker_interface import (
    OrderRequest, OrderSide, OrderType, TimeInForce
)
from services.trading_engine.paper_trading_executor import (
    PaperTradingExecutor, SlippageModel
)
from services.trading_engine.commission_calculator import (
    CommissionCalculator, MarketType
)
from services.trading_engine.trade_logger import TradeLogger


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_basic_market_orders(db: Session):
    """Example 1: Basic market order execution."""
    print("\n" + "=" * 80)
    print("Example 1: Basic Market Orders")
    print("=" * 80 + "\n")

    # Initialize paper trading executor
    executor = PaperTradingExecutor(
        db=db,
        user_id="demo_user",
        initial_cash=10_000_000,  # 10M KRW
        market_type=MarketType.KOSPI,
        enable_slippage=True
    )

    # Initialize trade logger
    trade_logger = TradeLogger(db=db, enable_console_logging=True)

    # Get account balance
    balance = executor.get_account_balance()
    print(f"Initial Cash: {balance['cash']:,.0f} KRW")
    print(f"Portfolio Value: {balance['portfolio_value']:,.0f} KRW")
    print(f"Total Value: {balance['total_value']:,.0f} KRW\n")

    # Submit a market buy order
    print("Submitting market BUY order for Samsung Electronics (005930)...")
    buy_order_request = OrderRequest(
        ticker="005930",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
        client_order_id="DEMO_BUY_001",
        notes="Example market buy order"
    )

    buy_order = executor.submit_order(buy_order_request)
    trade_logger.log_order_submitted(buy_order)

    if buy_order.executions:
        for execution in buy_order.executions:
            trade_logger.log_order_executed(buy_order, execution)

    print(f"\nOrder Status: {buy_order.status.value}")
    print(f"Filled Quantity: {buy_order.filled_quantity}")
    print(f"Average Fill Price: {buy_order.avg_fill_price:,.0f} KRW" if buy_order.avg_fill_price else "N/A")

    # Check updated balance
    balance = executor.get_account_balance()
    print(f"\nUpdated Cash: {balance['cash']:,.0f} KRW")
    print(f"Portfolio Value: {balance['portfolio_value']:,.0f} KRW")
    print(f"Total Value: {balance['total_value']:,.0f} KRW")

    # Check position
    position = executor.get_position("005930")
    if position:
        print(f"\nPosition in 005930:")
        print(f"  Quantity: {position.quantity}")
        print(f"  Avg Price: {position.avg_price:,.0f} KRW")
        print(f"  Current Price: {position.current_price:,.0f} KRW")
        print(f"  Market Value: {position.market_value:,.0f} KRW")
        print(f"  Unrealized P&L: {position.unrealized_pnl:,.0f} KRW ({position.unrealized_pnl_pct:+.2f}%)")


def example_2_limit_orders(db: Session):
    """Example 2: Limit order execution."""
    print("\n" + "=" * 80)
    print("Example 2: Limit Orders")
    print("=" * 80 + "\n")

    executor = PaperTradingExecutor(
        db=db,
        user_id="demo_user_2",
        initial_cash=10_000_000,
        enable_slippage=True
    )

    trade_logger = TradeLogger(db=db)

    # Get current price
    current_price = executor.get_current_price("005930")
    print(f"Current Price for 005930: {current_price:,.0f} KRW")

    # Submit limit buy order at lower price
    limit_price = current_price * 0.98  # 2% below current price
    print(f"\nSubmitting LIMIT BUY order at {limit_price:,.0f} KRW...")

    limit_order_request = OrderRequest(
        ticker="005930",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10,
        limit_price=limit_price,
        time_in_force=TimeInForce.GTC,
        notes="Example limit buy order"
    )

    limit_order = executor.submit_order(limit_order_request)
    trade_logger.log_order_submitted(limit_order)

    print(f"Order Status: {limit_order.status.value}")
    print(f"Order is Active: {limit_order.is_active}")

    # Submit limit buy order at favorable price (should execute)
    favorable_limit_price = current_price * 1.02  # 2% above current price
    print(f"\nSubmitting LIMIT BUY order at favorable price {favorable_limit_price:,.0f} KRW...")

    favorable_order_request = OrderRequest(
        ticker="005930",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=5,
        limit_price=favorable_limit_price,
        notes="Example favorable limit buy"
    )

    favorable_order = executor.submit_order(favorable_order_request)

    print(f"Order Status: {favorable_order.status.value}")
    if favorable_order.avg_fill_price:
        print(f"Fill Price: {favorable_order.avg_fill_price:,.0f} KRW")


def example_3_commission_calculator(db: Session):
    """Example 3: Commission and fee calculation."""
    print("\n" + "=" * 80)
    print("Example 3: Commission and Fee Calculation")
    print("=" * 80 + "\n")

    # Initialize commission calculator
    calc = CommissionCalculator(market_type=MarketType.KOSPI)

    # Example buy order
    quantity = 10
    price = 70_000

    print(f"Order: BUY {quantity} shares @ {price:,} KRW")
    print("-" * 80)

    buy_costs = calc.calculate_buy_costs(quantity, price)
    print(f"Gross Amount:        {buy_costs.gross_amount:>15,.2f} KRW")
    print(f"Commission:          {buy_costs.commission:>15,.2f} KRW")
    print(f"Transaction Tax:     {buy_costs.transaction_tax:>15,.2f} KRW")
    print(f"Total Fees:          {buy_costs.total_fees:>15,.2f} KRW")
    print(f"Net Amount:          {buy_costs.net_amount:>15,.2f} KRW")
    print(f"Effective Price:     {buy_costs.effective_price:>15,.2f} KRW/share")
    print(f"Fee Percentage:      {buy_costs.fee_percentage:>15,.4f}%")

    print("\n" + "-" * 80)
    print(f"Order: SELL {quantity} shares @ {price:,} KRW")
    print("-" * 80)

    sell_costs = calc.calculate_sell_costs(quantity, price)
    print(f"Gross Amount:        {sell_costs.gross_amount:>15,.2f} KRW")
    print(f"Commission:          {sell_costs.commission:>15,.2f} KRW")
    print(f"Transaction Tax:     {sell_costs.transaction_tax:>15,.2f} KRW")
    print(f"Agri/Fish Tax:       {sell_costs.agri_fish_tax:>15,.2f} KRW")
    print(f"Total Fees:          {sell_costs.total_fees:>15,.2f} KRW")
    print(f"Net Amount:          {sell_costs.net_amount:>15,.2f} KRW")
    print(f"Effective Price:     {sell_costs.effective_price:>15,.2f} KRW/share")
    print(f"Fee Percentage:      {sell_costs.fee_percentage:>15,.4f}%")

    # Calculate round trip
    print("\n" + "-" * 80)
    print("Round Trip Analysis (Buy + Sell)")
    print("-" * 80)

    buy_price = 70_000
    sell_price = 75_000  # 7.14% profit before fees

    round_trip = calc.calculate_round_trip_costs(quantity, buy_price, sell_price)
    print(f"Buy Price:           {buy_price:>15,.0f} KRW")
    print(f"Sell Price:          {sell_price:>15,.0f} KRW")
    print(f"Gross P&L:           {round_trip['gross_pnl']:>15,.2f} KRW")
    print(f"Total Fees:          {round_trip['total_fees']:>15,.2f} KRW")
    print(f"Net P&L:             {round_trip['net_pnl']:>15,.2f} KRW")
    print(f"Net P&L %:           {round_trip['net_pnl_pct']:>15,.2f}%")
    print(f"Breakeven Price:     {round_trip['breakeven_price']:>15,.2f} KRW")


def example_4_slippage_simulation(db: Session):
    """Example 4: Slippage simulation."""
    print("\n" + "=" * 80)
    print("Example 4: Slippage Simulation")
    print("=" * 80 + "\n")

    # Create custom slippage model
    slippage_model = SlippageModel(
        base_slippage_bps=10.0,     # 10 bps base
        volume_impact_factor=0.5,
        volatility_impact_factor=0.3
    )

    # Test with different order sizes
    market_price = 70_000
    avg_daily_volume = 1_000_000
    volatility = 2.0  # 2% daily volatility

    print(f"Market Price: {market_price:,} KRW")
    print(f"Avg Daily Volume: {avg_daily_volume:,} shares")
    print(f"Volatility: {volatility:.2f}%\n")

    print("-" * 80)
    print(f"{'Order Size':<15} {'Side':<10} {'Slippage (bps)':<20} {'Execution Price':<20}")
    print("-" * 80)

    for quantity in [100, 1000, 10000, 50000]:
        # Buy order
        buy_slippage = slippage_model.calculate_slippage(
            market_price, quantity, OrderSide.BUY, avg_daily_volume, volatility
        )
        buy_exec_price = market_price + buy_slippage
        buy_slippage_bps = (buy_slippage / market_price) * 10000

        print(f"{quantity:<15,} {'BUY':<10} {buy_slippage_bps:>15.2f} {buy_exec_price:>19,.0f}")

        # Sell order
        sell_slippage = slippage_model.calculate_slippage(
            market_price, quantity, OrderSide.SELL, avg_daily_volume, volatility
        )
        sell_exec_price = market_price + sell_slippage
        sell_slippage_bps = abs((sell_slippage / market_price) * 10000)

        print(f"{quantity:<15,} {'SELL':<10} {sell_slippage_bps:>15.2f} {sell_exec_price:>19,.0f}")
        print()


def example_5_trade_logging_and_export(db: Session):
    """Example 5: Trade logging and export."""
    print("\n" + "=" * 80)
    print("Example 5: Trade Logging and Export")
    print("=" * 80 + "\n")

    # Create trade logger with file output
    log_file = "/tmp/trade_log.txt"
    trade_logger = TradeLogger(
        db=db,
        log_file_path=log_file,
        enable_console_logging=True
    )

    # Get trade statistics
    stats = trade_logger.get_trade_statistics()

    print("Trade Statistics:")
    print("-" * 80)
    print(f"Total Trades:        {stats['total_trades']}")
    print(f"Buy Trades:          {stats['buy_trades']}")
    print(f"Sell Trades:         {stats['sell_trades']}")
    print(f"Unique Tickers:      {stats['unique_tickers']}")
    print(f"Total Volume:        {stats['total_volume']:,} shares")
    print(f"Total Value:         {stats['total_value']:,.0f} KRW")
    print(f"Total Commission:    {stats['total_commission']:,.0f} KRW")
    print(f"Total Tax:           {stats['total_tax']:,.0f} KRW")
    if stats['total_trades'] > 0:
        print(f"Avg Trade Size:      {stats['avg_trade_size']:,.0f} KRW")

    # Export trades to CSV
    csv_file = "/tmp/trades_export.csv"
    trade_logger.export_trades_to_csv(csv_file)
    print(f"\nTrades exported to: {csv_file}")
    print(f"Log file: {log_file}")


def example_6_complete_trading_workflow(db: Session):
    """Example 6: Complete trading workflow."""
    print("\n" + "=" * 80)
    print("Example 6: Complete Trading Workflow")
    print("=" * 80 + "\n")

    # Initialize executor and logger
    executor = PaperTradingExecutor(
        db=db,
        user_id="demo_trader",
        initial_cash=50_000_000,  # 50M KRW
        enable_slippage=True
    )

    trade_logger = TradeLogger(db=db)

    print("Step 1: Check initial balance")
    print("-" * 80)
    balance = executor.get_account_balance()
    print(f"Cash:                {balance['cash']:>20,.0f} KRW")
    print(f"Portfolio Value:     {balance['portfolio_value']:>20,.0f} KRW")
    print(f"Total Value:         {balance['total_value']:>20,.0f} KRW\n")

    # Buy multiple positions
    tickers_to_buy = [
        ("005930", 10),   # Samsung Electronics
        ("000660", 5),    # SK Hynix
        ("035420", 3),    # NAVER
    ]

    print("Step 2: Buy multiple positions")
    print("-" * 80)

    for ticker, quantity in tickers_to_buy:
        current_price = executor.get_current_price(ticker)
        if not current_price:
            print(f"Skipping {ticker}: No price data")
            continue

        print(f"\nBuying {quantity} shares of {ticker} @ ~{current_price:,.0f} KRW")

        order_request = OrderRequest(
            ticker=ticker,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=quantity,
            notes=f"Building position in {ticker}"
        )

        order = executor.submit_order(order_request)

        if order.status.value in ["filled", "partially_filled"]:
            print(f"  ✓ Order filled at {order.avg_fill_price:,.0f} KRW")
            print(f"  Commission: {order.total_commission:,.0f} KRW")
            print(f"  Tax: {order.total_tax:,.0f} KRW")
        else:
            print(f"  ✗ Order {order.status.value}")

    print("\n" + "-" * 80)
    print("Step 3: Review positions")
    print("-" * 80)

    positions = executor.get_positions()
    total_value = 0

    for position in positions:
        print(f"\n{position.ticker}:")
        print(f"  Quantity:        {position.quantity:>10,} shares")
        print(f"  Avg Price:       {position.avg_price:>10,.0f} KRW")
        print(f"  Current Price:   {position.current_price:>10,.0f} KRW")
        print(f"  Market Value:    {position.market_value:>10,.0f} KRW")
        print(f"  Unrealized P&L:  {position.unrealized_pnl:>10,.0f} KRW ({position.unrealized_pnl_pct:+.2f}%)")
        total_value += position.market_value

    print("\n" + "-" * 80)
    balance = executor.get_account_balance()
    print(f"Cash:                {balance['cash']:>20,.0f} KRW")
    print(f"Portfolio Value:     {total_value:>20,.0f} KRW")
    print(f"Total Value:         {balance['total_value']:>20,.0f} KRW")

    # Show all orders
    print("\n" + "-" * 80)
    print("Step 4: Order History")
    print("-" * 80)

    all_orders = executor.get_orders()
    print(f"\nTotal Orders: {len(all_orders)}")

    for order in all_orders[:5]:  # Show first 5
        print(f"\n{order.order_id}:")
        print(f"  {order.side.value.upper()} {order.quantity} {order.ticker}")
        print(f"  Status: {order.status.value}")
        if order.avg_fill_price:
            print(f"  Fill Price: {order.avg_fill_price:,.0f} KRW")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("ORDER EXECUTION MODULE - COMPREHENSIVE EXAMPLES")
    print("=" * 80)

    db = next(get_db_session())

    try:
        # Run examples
        example_1_basic_market_orders(db)
        example_2_limit_orders(db)
        example_3_commission_calculator(db)
        example_4_slippage_simulation(db)
        example_5_trade_logging_and_export(db)
        example_6_complete_trading_workflow(db)

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
