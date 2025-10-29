"""
Service communication integration tests.

Tests HTTP API endpoints, inter-service communication,
request/response validation, and service orchestration.
"""

import pytest
import requests
from datetime import datetime

from tests.integration.test_utils import (
    assert_response_success,
    assert_response_contains_fields,
    retry_on_failure,
)


@pytest.mark.integration
@pytest.mark.service
class TestServiceCommunication:
    """Service communication and API tests."""

    def test_data_collector_health_check(self, service_urls, api_client):
        """Test data collector service health endpoint."""
        health_url = f"{service_urls['data_collector']}/health"

        response = api_client.get(health_url, timeout=10)
        assert_response_success(response, 200)

        data = response.json()
        assert data.get("status") in ["healthy", "ok"]

    def test_indicator_calculator_health_check(self, service_urls, api_client):
        """Test indicator calculator service health endpoint."""
        health_url = f"{service_urls['indicator_calculator']}/health"

        response = api_client.get(health_url, timeout=10)
        assert_response_success(response, 200)

    def test_stock_screener_health_check(self, service_urls, api_client):
        """Test stock screener service health endpoint."""
        health_url = f"{service_urls['stock_screener']}/health"

        response = api_client.get(health_url, timeout=10)
        assert_response_success(response, 200)

    def test_trading_engine_health_check(self, service_urls, api_client):
        """Test trading engine service health endpoint."""
        health_url = f"{service_urls['trading_engine']}/health"

        response = api_client.get(health_url, timeout=10)
        assert_response_success(response, 200)

    def test_risk_manager_health_check(self, service_urls, api_client):
        """Test risk manager service health endpoint."""
        health_url = f"{service_urls['risk_manager']}/health"

        response = api_client.get(health_url, timeout=10)
        assert_response_success(response, 200)

    def test_indicator_calculator_api(
        self,
        service_urls,
        api_client,
        sample_stocks,
        sample_stock_prices,
        test_timeout,
    ):
        """Test indicator calculator API endpoints."""
        stock = sample_stocks[0]

        # Test calculate indicators endpoint
        calc_url = f"{service_urls['indicator_calculator']}/api/v1/indicators/calculate"

        response = api_client.post(
            calc_url,
            json={"stock_id": stock.id},
            timeout=test_timeout,
        )

        assert_response_success(response, 200)

        data = response.json()
        assert_response_contains_fields(data, ["stock_id", "indicators"])

        # Test get indicators endpoint
        get_url = f"{service_urls['indicator_calculator']}/api/v1/indicators/{stock.id}"

        response = api_client.get(get_url, timeout=test_timeout)
        assert_response_success(response, 200)

    def test_stock_screener_api(
        self,
        service_urls,
        api_client,
        sample_stocks,
        sample_stock_prices,
        sample_technical_indicators,
        test_timeout,
    ):
        """Test stock screener API endpoints."""
        # Test screening endpoint
        screen_url = f"{service_urls['stock_screener']}/api/v1/screen"

        screen_criteria = {
            "min_volume": 500000,
            "max_volatility": 50.0,
            "max_per": 20.0,
            "min_roe": 5.0,
        }

        response = api_client.post(
            screen_url,
            json=screen_criteria,
            timeout=test_timeout,
        )

        assert_response_success(response, 200)

        data = response.json()
        assert "stocks" in data
        assert isinstance(data["stocks"], list)

    def test_trading_engine_signal_generation_api(
        self,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        sample_technical_indicators,
        test_timeout,
    ):
        """Test trading engine signal generation API."""
        signal_url = f"{service_urls['trading_engine']}/api/v1/signals/generate"

        request_data = {
            "user_id": test_user_id,
            "stock_ids": [stock.id for stock in sample_stocks[:3]],
        }

        response = api_client.post(
            signal_url,
            json=request_data,
            timeout=test_timeout,
        )

        assert_response_success(response, 200)

        data = response.json()
        assert "signals" in data
        assert isinstance(data["signals"], list)

    def test_trading_engine_order_execution_api(
        self,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        test_timeout,
    ):
        """Test trading engine order execution API."""
        execute_url = f"{service_urls['trading_engine']}/api/v1/orders/execute"

        order_data = {
            "user_id": test_user_id,
            "stock_id": sample_stocks[0].id,
            "order_type": "buy",
            "order_action": "market",
            "quantity": 10,
        }

        response = api_client.post(
            execute_url,
            json=order_data,
            timeout=test_timeout,
        )

        assert_response_success(response, 200)

        data = response.json()
        assert_response_contains_fields(data, ["order_id", "status"])

    def test_trading_engine_portfolio_api(
        self,
        service_urls,
        api_client,
        test_user_id,
        sample_portfolio,
        test_timeout,
    ):
        """Test trading engine portfolio API."""
        portfolio_url = f"{service_urls['trading_engine']}/api/v1/portfolio"

        response = api_client.get(
            portfolio_url,
            params={"user_id": test_user_id},
            timeout=test_timeout,
        )

        assert_response_success(response, 200)

        data = response.json()
        assert "positions" in data
        assert isinstance(data["positions"], list)

    def test_risk_manager_validation_api(
        self,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        test_timeout,
    ):
        """Test risk manager order validation API."""
        validate_url = f"{service_urls['risk_manager']}/api/v1/risk/validate"

        order_data = {
            "user_id": test_user_id,
            "stock_id": sample_stocks[0].id,
            "order_type": "buy",
            "quantity": 50,
            "price": 60000,
        }

        response = api_client.post(
            validate_url,
            json=order_data,
            timeout=test_timeout,
        )

        assert_response_success(response, 200)

        data = response.json()
        assert "is_valid" in data
        assert isinstance(data["is_valid"], bool)

    def test_risk_manager_portfolio_risk_api(
        self,
        service_urls,
        api_client,
        test_user_id,
        sample_portfolio,
        test_timeout,
    ):
        """Test risk manager portfolio risk API."""
        risk_url = f"{service_urls['risk_manager']}/api/v1/risk/portfolio"

        response = api_client.get(
            risk_url,
            params={"user_id": test_user_id},
            timeout=test_timeout,
        )

        assert_response_success(response, 200)

        data = response.json()
        assert_response_contains_fields(data, ["total_exposure", "risk_level"])

    def test_inter_service_workflow(
        self,
        service_urls,
        api_client,
        test_user_id,
        sample_stocks,
        sample_stock_prices,
        test_timeout,
    ):
        """
        Test workflow involving multiple service communications.

        1. Calculate indicators (indicator_calculator)
        2. Screen stocks (stock_screener)
        3. Validate order (risk_manager)
        4. Execute order (trading_engine)
        """
        stock = sample_stocks[0]

        # Step 1: Calculate indicators
        calc_url = f"{service_urls['indicator_calculator']}/api/v1/indicators/calculate"
        calc_response = api_client.post(
            calc_url,
            json={"stock_id": stock.id},
            timeout=test_timeout,
        )
        assert_response_success(calc_response, 200)

        # Step 2: Screen stocks
        screen_url = f"{service_urls['stock_screener']}/api/v1/screen"
        screen_response = api_client.post(
            screen_url,
            json={"min_volume": 500000},
            timeout=test_timeout,
        )
        assert_response_success(screen_response, 200)

        # Step 3: Validate order with risk manager
        validate_url = f"{service_urls['risk_manager']}/api/v1/risk/validate"
        validate_response = api_client.post(
            validate_url,
            json={
                "user_id": test_user_id,
                "stock_id": stock.id,
                "order_type": "buy",
                "quantity": 10,
                "price": 50000,
            },
            timeout=test_timeout,
        )
        assert_response_success(validate_response, 200)

        validation_data = validate_response.json()

        # Step 4: Execute order if validated
        if validation_data.get("is_valid"):
            execute_url = f"{service_urls['trading_engine']}/api/v1/orders/execute"
            execute_response = api_client.post(
                execute_url,
                json={
                    "user_id": test_user_id,
                    "stock_id": stock.id,
                    "order_type": "buy",
                    "order_action": "market",
                    "quantity": 10,
                },
                timeout=test_timeout,
            )
            assert_response_success(execute_response, 200)

    def test_api_error_responses(self, service_urls, api_client, test_timeout):
        """Test API error handling for invalid requests."""
        # Test invalid stock ID
        calc_url = f"{service_urls['indicator_calculator']}/api/v1/indicators/calculate"

        response = api_client.post(
            calc_url,
            json={"stock_id": 999999},  # Non-existent stock
            timeout=test_timeout,
        )

        # Should return error status
        assert response.status_code in [400, 404, 422]

        # Test invalid order data
        execute_url = f"{service_urls['trading_engine']}/api/v1/orders/execute"

        response = api_client.post(
            execute_url,
            json={
                "user_id": "test",
                # Missing required fields
            },
            timeout=test_timeout,
        )

        assert response.status_code in [400, 422]

    def test_api_request_validation(self, service_urls, api_client, test_timeout):
        """Test API request validation."""
        # Test screening with invalid parameters
        screen_url = f"{service_urls['stock_screener']}/api/v1/screen"

        invalid_requests = [
            {"min_volume": -1000},  # Negative volume
            {"max_per": -10.0},  # Negative PER
            {"min_roe": 150.0},  # Unrealistic ROE
        ]

        for invalid_request in invalid_requests:
            response = api_client.post(
                screen_url,
                json=invalid_request,
                timeout=test_timeout,
            )

            # Should reject invalid requests
            assert response.status_code in [400, 422]

    def test_concurrent_api_requests(
        self,
        service_urls,
        api_client,
        sample_stocks,
        test_timeout,
    ):
        """Test handling of concurrent API requests."""
        import concurrent.futures

        calc_url = f"{service_urls['indicator_calculator']}/api/v1/indicators/calculate"

        def make_request(stock_id):
            return api_client.post(
                calc_url,
                json={"stock_id": stock_id},
                timeout=test_timeout,
            )

        # Make concurrent requests
        stock_ids = [stock.id for stock in sample_stocks[:3]]

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request, stock_id) for stock_id in stock_ids]

            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        for response in results:
            assert response.status_code == 200

    def test_api_response_format(
        self,
        service_urls,
        api_client,
        sample_stocks,
        sample_stock_prices,
        test_timeout,
    ):
        """Test API response format consistency."""
        stock = sample_stocks[0]

        # Test indicator calculator response format
        calc_url = f"{service_urls['indicator_calculator']}/api/v1/indicators/calculate"
        response = api_client.post(
            calc_url,
            json={"stock_id": stock.id},
            timeout=test_timeout,
        )

        assert_response_success(response, 200)
        assert response.headers.get("content-type") == "application/json"

        data = response.json()
        assert isinstance(data, dict)

    def test_service_timeout_handling(self, service_urls, api_client):
        """Test service timeout handling."""
        # Test with very short timeout
        health_url = f"{service_urls['data_collector']}/health"

        try:
            response = api_client.get(health_url, timeout=0.001)  # 1ms timeout
        except requests.exceptions.Timeout:
            # Timeout is expected with such a short timeout
            pass

    def test_api_authentication_headers(self, service_urls, api_client, test_timeout):
        """Test API accepts requests with proper headers."""
        health_url = f"{service_urls['data_collector']}/health"

        # Request with headers
        response = api_client.get(
            health_url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=test_timeout,
        )

        assert_response_success(response, 200)

    def test_large_payload_handling(
        self,
        service_urls,
        api_client,
        sample_stocks,
        test_timeout,
    ):
        """Test handling of large request payloads."""
        signal_url = f"{service_urls['trading_engine']}/api/v1/signals/generate"

        # Request signals for all stocks
        request_data = {
            "user_id": "test_user",
            "stock_ids": [stock.id for stock in sample_stocks],
        }

        response = api_client.post(
            signal_url,
            json=request_data,
            timeout=test_timeout,
        )

        # Should handle large payload
        assert response.status_code in [200, 202]

    def test_api_retry_logic(self, service_urls, api_client, test_timeout):
        """Test retry logic for transient failures."""

        def make_health_request():
            health_url = f"{service_urls['data_collector']}/health"
            response = api_client.get(health_url, timeout=test_timeout)
            assert_response_success(response, 200)
            return response

        # Should succeed even if there are transient issues
        result = retry_on_failure(
            make_health_request,
            max_attempts=3,
            delay=1.0,
            exceptions=(requests.exceptions.RequestException,)
        )

        assert result is not None
