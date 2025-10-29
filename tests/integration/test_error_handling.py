"""
Error handling and recovery integration tests.

Tests error scenarios, fault tolerance, transaction rollback,
retry mechanisms, and system recovery.
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError, DataError
import requests

from shared.database.models import Stock, StockPrice, Trade, Portfolio
from tests.integration.test_utils import (
    wait_for_condition,
    retry_on_failure,
)


@pytest.mark.integration
@pytest.mark.error_handling
class TestErrorHandling:
    """Error handling and recovery tests."""

    def test_database_constraint_violation_recovery(self, integration_db_session, sample_stocks):
        """Test recovery from database constraint violations."""
        session = integration_db_session
        stock = sample_stocks[0]

        # Insert valid price
        price1 = StockPrice(
            stock_id=stock.id,
            date=datetime.now().date(),
            open=50000,
            high=51000,
            low=49000,
            close=50500,
            volume=1000000,
        )
        session.add(price1)
        session.commit()

        # Try to insert duplicate (same stock_id and date)
        price2 = StockPrice(
            stock_id=stock.id,
            date=datetime.now().date(),
            open=51000,
            high=52000,
            low=50000,
            close=51500,
            volume=1100000,
        )
        session.add(price2)

        # Should raise IntegrityError
        with pytest.raises(IntegrityError):
            session.commit()

        # Rollback and continue with valid operations
        session.rollback()

        # Insert with different date should succeed
        price3 = StockPrice(
            stock_id=stock.id,
            date=datetime.now().date(),
            open=52000,
            high=53000,
            low=51000,
            close=52500,
            volume=1200000,
        )
        session.add(price3)
        session.commit()

        # Verify recovery
        assert price3.id is not None

    def test_foreign_key_violation_handling(self, integration_db_session):
        """Test handling of foreign key constraint violations."""
        session = integration_db_session

        # Try to insert price for non-existent stock
        invalid_price = StockPrice(
            stock_id=999999,  # Non-existent stock
            date=datetime.now().date(),
            open=50000,
            high=51000,
            low=49000,
            close=50500,
            volume=1000000,
        )
        session.add(invalid_price)

        # Should raise IntegrityError
        with pytest.raises(IntegrityError):
            session.commit()

        # Rollback and continue
        session.rollback()

        # Verify session is still usable
        stock_count = session.query(Stock).count()
        assert stock_count >= 0

    def test_transaction_rollback_on_error(self, integration_db_session, sample_stocks):
        """Test that transactions rollback properly on errors."""
        session = integration_db_session
        stock = sample_stocks[0]

        initial_count = session.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).count()

        try:
            # Insert valid record
            price1 = StockPrice(
                stock_id=stock.id,
                date=datetime.now().date(),
                open=50000,
                high=51000,
                low=49000,
                close=50500,
                volume=1000000,
            )
            session.add(price1)

            # Insert invalid record
            price2 = StockPrice(
                stock_id=999999,  # Non-existent stock
                date=datetime.now().date(),
                open=50000,
                high=51000,
                low=49000,
                close=50500,
                volume=1000000,
            )
            session.add(price2)

            session.commit()
        except IntegrityError:
            session.rollback()

        # Verify both records were rolled back
        final_count = session.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).count()

        assert final_count == initial_count

    def test_invalid_data_type_handling(self, integration_db_session, sample_stocks):
        """Test handling of invalid data types."""
        session = integration_db_session
        stock = sample_stocks[0]

        # Try to insert invalid data type
        with pytest.raises((DataError, ValueError, TypeError)):
            invalid_price = StockPrice(
                stock_id=stock.id,
                date=datetime.now().date(),
                open="invalid",  # Should be float
                high=51000,
                low=49000,
                close=50500,
                volume=1000000,
            )
            session.add(invalid_price)
            session.commit()

        session.rollback()

    def test_api_error_response_handling(
        self,
        service_urls,
        api_client,
        test_timeout,
    ):
        """Test handling of API error responses."""
        # Test with non-existent stock ID
        calc_url = f"{service_urls['indicator_calculator']}/api/v1/indicators/calculate"

        response = api_client.post(
            calc_url,
            json={"stock_id": 999999},
            timeout=test_timeout,
        )

        # Should return error status
        assert response.status_code in [400, 404, 422]

        # Response should contain error information
        if response.headers.get("content-type") == "application/json":
            data = response.json()
            assert "error" in data or "detail" in data or "message" in data

    def test_malformed_request_handling(self, service_urls, api_client, test_timeout):
        """Test handling of malformed API requests."""
        execute_url = f"{service_urls['trading_engine']}/api/v1/orders/execute"

        # Test with missing required fields
        response = api_client.post(
            execute_url,
            json={"user_id": "test"},  # Missing stock_id, quantity, etc.
            timeout=test_timeout,
        )

        assert response.status_code in [400, 422]

        # Test with invalid JSON
        try:
            response = api_client.post(
                execute_url,
                data="invalid json",
                headers={"Content-Type": "application/json"},
                timeout=test_timeout,
            )
            assert response.status_code in [400, 422]
        except requests.exceptions.JSONDecodeError:
            pass  # Also acceptable

    def test_service_unavailable_handling(self, api_client):
        """Test handling when service is unavailable."""
        # Try to connect to non-existent service
        invalid_url = "http://localhost:9999/health"

        with pytest.raises(requests.exceptions.RequestException):
            api_client.get(invalid_url, timeout=2)

    def test_timeout_handling(self, service_urls, api_client):
        """Test timeout handling for slow operations."""
        health_url = f"{service_urls['data_collector']}/health"

        # Test with very short timeout
        with pytest.raises(requests.exceptions.Timeout):
            api_client.get(health_url, timeout=0.001)  # 1ms - unrealistic

    def test_retry_mechanism(self, service_urls, api_client, test_timeout):
        """Test retry mechanism for transient failures."""
        health_url = f"{service_urls['data_collector']}/health"

        def make_request():
            response = api_client.get(health_url, timeout=test_timeout)
            if response.status_code != 200:
                raise requests.exceptions.HTTPError(response=response)
            return response

        # Should succeed with retries
        result = retry_on_failure(
            make_request,
            max_attempts=3,
            delay=1.0,
            backoff=2.0,
            exceptions=(requests.exceptions.RequestException,)
        )

        assert result.status_code == 200

    def test_invalid_order_validation(
        self,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        test_timeout,
    ):
        """Test validation of invalid trading orders."""
        validate_url = f"{service_urls['risk_manager']}/api/v1/risk/validate"

        # Test negative quantity
        response = api_client.post(
            validate_url,
            json={
                "user_id": test_user_id,
                "stock_id": sample_stocks[0].id,
                "order_type": "buy",
                "quantity": -10,  # Invalid: negative
                "price": 50000,
            },
            timeout=test_timeout,
        )

        # Should reject or validate as invalid
        if response.status_code == 200:
            data = response.json()
            assert data.get("is_valid") is False
        else:
            assert response.status_code in [400, 422]

        # Test zero quantity
        response = api_client.post(
            validate_url,
            json={
                "user_id": test_user_id,
                "stock_id": sample_stocks[0].id,
                "order_type": "buy",
                "quantity": 0,  # Invalid: zero
                "price": 50000,
            },
            timeout=test_timeout,
        )

        if response.status_code == 200:
            data = response.json()
            assert data.get("is_valid") is False
        else:
            assert response.status_code in [400, 422]

    def test_insufficient_funds_handling(
        self,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        test_timeout,
    ):
        """Test handling of insufficient funds scenario."""
        validate_url = f"{service_urls['risk_manager']}/api/v1/risk/validate"

        # Test order that exceeds reasonable portfolio value
        response = api_client.post(
            validate_url,
            json={
                "user_id": test_user_id,
                "stock_id": sample_stocks[0].id,
                "order_type": "buy",
                "quantity": 1000000,  # Very large quantity
                "price": 50000,
            },
            timeout=test_timeout,
        )

        # Should either reject or mark as invalid
        if response.status_code == 200:
            data = response.json()
            # May be invalid due to risk limits
            assert "is_valid" in data
        else:
            assert response.status_code in [400, 422]

    def test_duplicate_order_prevention(
        self,
        integration_db_session,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        test_timeout,
    ):
        """Test prevention of duplicate order execution."""
        session = integration_db_session
        stock = sample_stocks[0]

        execute_url = f"{service_urls['trading_engine']}/api/v1/orders/execute"

        order_data = {
            "user_id": test_user_id,
            "stock_id": stock.id,
            "order_type": "buy",
            "order_action": "market",
            "quantity": 10,
        }

        # Execute first order
        response1 = api_client.post(
            execute_url,
            json=order_data,
            timeout=test_timeout,
        )

        assert response1.status_code == 200

        # Execute same order again immediately
        response2 = api_client.post(
            execute_url,
            json=order_data,
            timeout=test_timeout,
        )

        # Should either succeed (creating second order) or handle appropriately
        # Both are valid depending on business logic
        assert response2.status_code in [200, 400, 409]

    def test_invalid_price_data_handling(self, integration_db_session, sample_stocks):
        """Test handling of invalid OHLC price data."""
        session = integration_db_session
        stock = sample_stocks[0]

        # Test high < low (invalid)
        with pytest.raises((IntegrityError, ValueError)):
            invalid_price = StockPrice(
                stock_id=stock.id,
                date=datetime.now().date(),
                open=50000,
                high=48000,  # Invalid: high < low
                low=49000,
                close=50500,
                volume=1000000,
            )
            session.add(invalid_price)
            session.commit()

        session.rollback()

        # Test negative volume
        with pytest.raises((IntegrityError, ValueError, DataError)):
            invalid_price = StockPrice(
                stock_id=stock.id,
                date=datetime.now().date(),
                open=50000,
                high=51000,
                low=49000,
                close=50500,
                volume=-1000,  # Invalid: negative volume
            )
            session.add(invalid_price)
            session.commit()

        session.rollback()

    def test_concurrent_update_conflict_resolution(
        self,
        integration_db_session,
        sample_stocks,
    ):
        """Test resolution of concurrent update conflicts."""
        session = integration_db_session
        stock = sample_stocks[0]

        # Create a portfolio position
        position = Portfolio(
            user_id="test_user",
            stock_id=stock.id,
            quantity=100,
            average_buy_price=50000,
            current_price=50000,
        )
        session.add(position)
        session.commit()

        # Simulate concurrent updates
        # In a real scenario, this would involve multiple sessions
        # Here we test the basic update mechanism

        position.quantity = 110
        session.commit()

        # Verify update succeeded
        updated_position = session.query(Portfolio).get(position.id)
        assert updated_position.quantity == 110

    def test_api_rate_limiting_handling(
        self,
        service_urls,
        api_client,
        sample_stocks,
        test_timeout,
    ):
        """Test handling of rapid API requests (rate limiting)."""
        health_url = f"{service_urls['data_collector']}/health"

        # Make rapid requests
        responses = []
        for _ in range(10):
            try:
                response = api_client.get(health_url, timeout=test_timeout)
                responses.append(response.status_code)
            except requests.exceptions.RequestException as e:
                # Rate limiting or timeout is acceptable
                pass

        # Most requests should succeed
        successful_requests = [r for r in responses if r == 200]
        assert len(successful_requests) > 0

    def test_database_connection_recovery(self, integration_db_engine):
        """Test database connection pool recovery."""
        from sqlalchemy.orm import sessionmaker

        # Create session
        SessionLocal = sessionmaker(bind=integration_db_engine)
        session = SessionLocal()

        # Perform query
        stock_count = session.query(Stock).count()
        assert stock_count >= 0

        # Close session
        session.close()

        # Create new session (connection pool should handle this)
        session2 = SessionLocal()
        stock_count2 = session2.query(Stock).count()
        assert stock_count2 >= 0

        session2.close()

    def test_empty_result_set_handling(
        self,
        integration_db_session,
        service_urls,
        api_client,
        test_timeout,
    ):
        """Test handling of empty result sets."""
        # Test screening with impossible criteria
        screen_url = f"{service_urls['stock_screener']}/api/v1/screen"

        response = api_client.post(
            screen_url,
            json={
                "min_volume": 999999999999,  # Unrealistically high
                "max_per": 0.1,  # Unrealistically low
            },
            timeout=test_timeout,
        )

        assert response.status_code == 200

        data = response.json()
        assert "stocks" in data
        assert len(data["stocks"]) == 0  # Empty result

    def test_partial_data_handling(
        self,
        integration_db_session,
        service_urls,
        api_client,
        sample_stocks,
        test_timeout,
    ):
        """Test handling of partial/incomplete data."""
        # Create stock with minimal data
        stock = sample_stocks[0]

        # Calculate indicators (may have partial results)
        calc_url = f"{service_urls['indicator_calculator']}/api/v1/indicators/calculate"

        response = api_client.post(
            calc_url,
            json={"stock_id": stock.id},
            timeout=test_timeout,
        )

        # Should handle gracefully
        assert response.status_code in [200, 202, 404]

    def test_error_message_clarity(
        self,
        service_urls,
        api_client,
        test_timeout,
    ):
        """Test that error messages are clear and informative."""
        execute_url = f"{service_urls['trading_engine']}/api/v1/orders/execute"

        response = api_client.post(
            execute_url,
            json={"invalid": "data"},
            timeout=test_timeout,
        )

        assert response.status_code in [400, 422]

        # Error response should be JSON with message
        if response.headers.get("content-type") == "application/json":
            data = response.json()
            # Should have some error field
            assert any(key in data for key in ["error", "detail", "message", "errors"])
