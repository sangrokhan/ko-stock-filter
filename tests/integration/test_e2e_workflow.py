"""
End-to-end workflow integration tests.

Tests the complete trading workflow from data collection through
order execution, including all service interactions.
"""

import pytest
from datetime import datetime, timedelta

from shared.database.models import Stock, StockPrice, TechnicalIndicator
from shared.database.models import Trade, Portfolio, Watchlist
from tests.integration.test_utils import (
    wait_for_condition,
    assert_response_success,
    assert_response_contains_fields,
    wait_for_database_record,
)


@pytest.mark.integration
@pytest.mark.e2e
class TestEndToEndWorkflow:
    """
    End-to-end workflow tests covering the complete trading pipeline.
    """

    def test_complete_trading_workflow(
        self,
        integration_db_session,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        sample_stock_prices,
        test_timeout,
    ):
        """
        Test the complete workflow:
        1. Data collection (stock and price data)
        2. Indicator calculation
        3. Stock screening
        4. Signal generation
        5. Order execution
        6. Portfolio update
        """
        session = integration_db_session
        stock = sample_stocks[0]

        # Step 1: Verify data collection - stock and prices exist
        assert stock.id is not None
        assert stock.ticker == "005930"

        price_count = session.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).count()
        assert price_count >= 30, "Should have at least 30 days of price data"

        # Step 2: Calculate technical indicators
        indicator_url = f"{service_urls['indicator_calculator']}/api/v1/indicators/calculate"
        response = api_client.post(
            indicator_url,
            json={"stock_id": stock.id},
            timeout=test_timeout,
        )
        assert_response_success(response, 200)

        # Verify indicators were calculated and stored
        indicator = wait_for_database_record(
            session,
            TechnicalIndicator,
            TechnicalIndicator.stock_id == stock.id,
            timeout=10,
        )
        assert indicator is not None
        assert indicator.rsi_14 is not None
        assert indicator.macd is not None

        # Step 3: Screen stocks
        screener_url = f"{service_urls['stock_screener']}/api/v1/screen"
        screen_response = api_client.post(
            screener_url,
            json={
                "min_volume": 500000,
                "max_volatility": 50.0,
                "max_per": 30.0,
            },
            timeout=test_timeout,
        )
        assert_response_success(screen_response, 200)

        screen_data = screen_response.json()
        assert "stocks" in screen_data
        assert len(screen_data["stocks"]) > 0

        # Step 4: Generate trading signals
        trading_url = f"{service_urls['trading_engine']}/api/v1/signals/generate"
        signal_response = api_client.post(
            trading_url,
            json={
                "user_id": test_user_id,
                "stock_ids": [stock.id],
            },
            timeout=test_timeout,
        )
        assert_response_success(signal_response, 200)

        signal_data = signal_response.json()
        assert "signals" in signal_data

        # Step 5: Execute a trade (paper trading)
        if len(signal_data["signals"]) > 0:
            signal = signal_data["signals"][0]

            execute_url = f"{service_urls['trading_engine']}/api/v1/orders/execute"
            execute_response = api_client.post(
                execute_url,
                json={
                    "user_id": test_user_id,
                    "stock_id": stock.id,
                    "order_type": signal.get("action", "buy"),
                    "quantity": 10,
                    "order_action": "market",
                },
                timeout=test_timeout,
            )
            assert_response_success(execute_response, 200)

            # Step 6: Verify portfolio was updated
            portfolio_entry = wait_for_database_record(
                session,
                Portfolio,
                (Portfolio.user_id == test_user_id) & (Portfolio.stock_id == stock.id),
                timeout=10,
            )
            assert portfolio_entry is not None
            assert portfolio_entry.quantity == 10

    def test_watchlist_to_trade_workflow(
        self,
        integration_db_session,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        sample_stock_prices,
        sample_technical_indicators,
        test_timeout,
    ):
        """
        Test workflow from adding to watchlist to executing a trade.
        """
        session = integration_db_session
        stock = sample_stocks[1]  # SK Hynix

        # Step 1: Add stock to watchlist
        watchlist_data = {
            "user_id": test_user_id,
            "stock_id": stock.id,
            "target_price": 120000,
            "notes": "Test watchlist entry",
        }

        # Create watchlist entry directly in DB
        watchlist_entry = Watchlist(**watchlist_data)
        session.add(watchlist_entry)
        session.commit()

        # Step 2: Monitor price changes (simulate price reaching target)
        latest_price = session.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).order_by(StockPrice.date.desc()).first()

        assert latest_price is not None

        # Step 3: Generate signal when price condition is met
        if latest_price.close >= watchlist_data["target_price"] * 0.95:
            trading_url = f"{service_urls['trading_engine']}/api/v1/signals/generate"
            signal_response = api_client.post(
                trading_url,
                json={
                    "user_id": test_user_id,
                    "stock_ids": [stock.id],
                },
                timeout=test_timeout,
            )
            assert_response_success(signal_response, 200)

        # Step 4: Execute trade
        execute_url = f"{service_urls['trading_engine']}/api/v1/orders/execute"
        execute_response = api_client.post(
            execute_url,
            json={
                "user_id": test_user_id,
                "stock_id": stock.id,
                "order_type": "buy",
                "quantity": 5,
                "order_action": "limit",
                "price": watchlist_data["target_price"],
            },
            timeout=test_timeout,
        )
        assert_response_success(execute_response, 200)

        # Step 5: Verify trade was recorded
        trade = wait_for_database_record(
            session,
            Trade,
            (Trade.user_id == test_user_id) & (Trade.stock_id == stock.id),
            timeout=10,
        )
        assert trade is not None
        assert trade.order_type == "buy"
        assert trade.quantity == 5

    def test_risk_management_workflow(
        self,
        integration_db_session,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        sample_portfolio,
        test_timeout,
    ):
        """
        Test risk management workflow including position sizing and risk limits.
        """
        stock = sample_stocks[0]

        # Step 1: Check current risk metrics
        risk_url = f"{service_urls['risk_manager']}/api/v1/risk/portfolio"
        risk_response = api_client.get(
            risk_url,
            params={"user_id": test_user_id},
            timeout=test_timeout,
        )
        assert_response_success(risk_response, 200)

        risk_data = risk_response.json()
        assert_response_contains_fields(risk_data, ["total_exposure", "risk_level"])

        # Step 2: Validate a new order against risk limits
        validate_url = f"{service_urls['risk_manager']}/api/v1/risk/validate"
        validate_response = api_client.post(
            validate_url,
            json={
                "user_id": test_user_id,
                "stock_id": stock.id,
                "order_type": "buy",
                "quantity": 50,
                "price": 60000,
            },
            timeout=test_timeout,
        )
        assert_response_success(validate_response, 200)

        validation_data = validate_response.json()
        assert "is_valid" in validation_data

        # Step 3: If valid, execute the trade
        if validation_data.get("is_valid"):
            execute_url = f"{service_urls['trading_engine']}/api/v1/orders/execute"
            execute_response = api_client.post(
                execute_url,
                json={
                    "user_id": test_user_id,
                    "stock_id": stock.id,
                    "order_type": "buy",
                    "quantity": 50,
                    "order_action": "market",
                },
                timeout=test_timeout,
            )
            assert_response_success(execute_response, 200)

        # Step 4: Verify risk metrics were updated
        updated_risk_response = api_client.get(
            risk_url,
            params={"user_id": test_user_id},
            timeout=test_timeout,
        )
        assert_response_success(updated_risk_response, 200)

    def test_multi_stock_screening_workflow(
        self,
        integration_db_session,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        sample_stock_prices,
        sample_technical_indicators,
        sample_fundamental_indicators,
        test_timeout,
    ):
        """
        Test screening multiple stocks and building a portfolio.
        """
        # Step 1: Screen for undervalued stocks
        screener_url = f"{service_urls['stock_screener']}/api/v1/screen"
        screen_response = api_client.post(
            screener_url,
            json={
                "max_per": 15.0,
                "min_roe": 10.0,
                "max_debt_ratio": 50.0,
                "min_volume": 500000,
            },
            timeout=test_timeout,
        )
        assert_response_success(screen_response, 200)

        screen_data = screen_response.json()
        screened_stocks = screen_data.get("stocks", [])

        assert len(screened_stocks) > 0, "Should find at least one stock meeting criteria"

        # Step 2: Add screened stocks to watchlist
        watchlist_entries = []
        for stock_data in screened_stocks[:3]:  # Top 3 stocks
            stock_id = stock_data.get("stock_id")

            watchlist_entry = Watchlist(
                user_id=test_user_id,
                stock_id=stock_id,
                target_price=stock_data.get("current_price", 0) * 1.15,
                score=stock_data.get("score", 0),
                notes="Added from screening",
            )
            watchlist_entries.append(watchlist_entry)
            integration_db_session.add(watchlist_entry)

        integration_db_session.commit()

        # Step 3: Generate signals for watchlist stocks
        stock_ids = [entry.stock_id for entry in watchlist_entries]

        trading_url = f"{service_urls['trading_engine']}/api/v1/signals/generate"
        signal_response = api_client.post(
            trading_url,
            json={
                "user_id": test_user_id,
                "stock_ids": stock_ids,
            },
            timeout=test_timeout,
        )
        assert_response_success(signal_response, 200)

        # Step 4: Verify signals were generated
        signal_data = signal_response.json()
        assert "signals" in signal_data
        assert len(signal_data["signals"]) > 0

    def test_position_monitoring_workflow(
        self,
        integration_db_session,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        sample_portfolio,
        test_timeout,
    ):
        """
        Test monitoring existing positions and stop-loss/take-profit triggers.
        """
        session = integration_db_session
        position = sample_portfolio[0]

        # Step 1: Get current positions
        portfolio_url = f"{service_urls['trading_engine']}/api/v1/portfolio"
        portfolio_response = api_client.get(
            portfolio_url,
            params={"user_id": test_user_id},
            timeout=test_timeout,
        )
        assert_response_success(portfolio_response, 200)

        portfolio_data = portfolio_response.json()
        assert "positions" in portfolio_data
        assert len(portfolio_data["positions"]) > 0

        # Step 2: Update current prices
        current_price = position.current_price * 0.92  # Price drops below stop-loss

        # Simulate price update
        latest_price = session.query(StockPrice).filter(
            StockPrice.stock_id == position.stock_id
        ).order_by(StockPrice.date.desc()).first()

        if latest_price:
            new_price = StockPrice(
                stock_id=position.stock_id,
                date=datetime.now().date(),
                open=current_price,
                high=current_price * 1.01,
                low=current_price * 0.99,
                close=current_price,
                volume=1000000,
            )
            session.add(new_price)
            session.commit()

        # Step 3: Monitor for stop-loss triggers
        monitor_url = f"{service_urls['trading_engine']}/api/v1/positions/monitor"
        monitor_response = api_client.post(
            monitor_url,
            json={"user_id": test_user_id},
            timeout=test_timeout,
        )
        assert_response_success(monitor_response, 200)

        monitor_data = monitor_response.json()
        assert "alerts" in monitor_data

        # Step 4: If stop-loss triggered, verify sell signal
        if len(monitor_data.get("alerts", [])) > 0:
            alert = monitor_data["alerts"][0]
            assert alert.get("type") in ["stop_loss", "take_profit"]
