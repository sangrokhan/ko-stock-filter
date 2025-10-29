"""
Example: Monitoring Integration for a Trading Service

This example shows how to integrate all monitoring components into a FastAPI service.
"""

import os
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from redis import Redis

# Import monitoring components
from shared.monitoring import (
    HealthCheck,
    ServiceMetrics,
    ResourceMonitor,
    AlertManager,
    ReportGenerator,
    StructuredLogger,
    AlertLevel,
    Alert,
    create_health_router,
    create_metrics_router,
    create_resource_alert,
    create_error_alert,
    create_risk_alert,
)


# ============================================================================
# 1. INITIALIZATION
# ============================================================================

app = FastAPI(title="Trading Engine", version="1.0.0")

# Configure structured logger
os.environ['SERVICE_NAME'] = 'trading_engine'
os.environ['ENVIRONMENT'] = os.getenv('ENVIRONMENT', 'development')

logger = StructuredLogger.get_logger(
    name="trading_engine",
    level=os.getenv('LOG_LEVEL', 'INFO'),
    json_format=True  # JSON format for log aggregation
)

# Health check
health_check = HealthCheck(
    service_name="trading_engine",
    version="1.0.0"
)

# Metrics
metrics = ServiceMetrics(service_name="trading_engine")
metrics.set_service_info(version="1.0.0", environment=os.getenv('ENVIRONMENT', 'development'))

# Resource monitor with custom thresholds
resource_monitor = ResourceMonitor(
    service_name="trading_engine",
    thresholds={
        "cpu_warning": float(os.getenv('CPU_WARNING_THRESHOLD', 70.0)),
        "cpu_critical": float(os.getenv('CPU_CRITICAL_THRESHOLD', 90.0)),
        "memory_warning": float(os.getenv('MEMORY_WARNING_THRESHOLD', 80.0)),
        "memory_critical": float(os.getenv('MEMORY_CRITICAL_THRESHOLD', 95.0)),
    }
)

# Alert manager
alert_manager = AlertManager(
    email_config={
        "smtp_host": os.getenv('SMTP_HOST'),
        "smtp_port": int(os.getenv('SMTP_PORT', 587)),
        "username": os.getenv('SMTP_USERNAME'),
        "password": os.getenv('SMTP_PASSWORD'),
        "from_email": os.getenv('ALERT_EMAIL_FROM'),
        "to_emails": os.getenv('ALERT_EMAIL_TO', '').split(',')
    } if os.getenv('SMTP_HOST') else None,
    slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
    slack_channel=os.getenv('SLACK_CHANNEL', '#trading-alerts')
)

# Report generator
report_generator = ReportGenerator(
    email_config=alert_manager.email_config,
    slack_webhook_url=alert_manager.slack_webhook_url,
    slack_channel=alert_manager.slack_channel
)


# ============================================================================
# 2. ADD MONITORING ENDPOINTS
# ============================================================================

app.include_router(create_health_router(health_check), prefix="/api/v1")
app.include_router(create_metrics_router(metrics), prefix="/api/v1")


# ============================================================================
# 3. STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize monitoring on startup"""
    logger.info(
        "Service starting",
        extra={
            "version": "1.0.0",
            "environment": os.getenv('ENVIRONMENT', 'development')
        }
    )

    # Start resource monitoring with alert callback
    async def resource_alert_callback(alerts, resources):
        """Send alerts for resource threshold breaches"""
        for alert_data in alerts:
            alert = create_resource_alert(
                resource_type=alert_data["resource"],
                usage_percent=alert_data["value"],
                threshold=alert_data["threshold"],
                context={
                    "service": "trading_engine",
                    "cpu_percent": resources.cpu_percent,
                    "memory_percent": resources.memory_percent,
                    "disk_percent": resources.disk_percent
                }
            )
            await alert_manager.send_alert(alert, cooldown_minutes=15)

            # Also record in metrics
            metrics.record_alert(
                alert_type="resource_threshold",
                channel="slack" if alert_manager.slack_webhook_url else "email"
            )

    # Start monitoring every 60 seconds
    await resource_monitor.start_monitoring(
        interval=60,
        callback=resource_alert_callback
    )

    logger.info("Resource monitoring started", extra={"interval_seconds": 60})


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Service shutting down")

    # Stop resource monitoring
    await resource_monitor.stop_monitoring()

    logger.info("Resource monitoring stopped")


# ============================================================================
# 4. REQUEST MIDDLEWARE - Add request tracing
# ============================================================================

@app.middleware("http")
async def monitoring_middleware(request, call_next):
    """Add monitoring to all requests"""
    import uuid

    # Generate request ID
    request_id = str(uuid.uuid4())

    # Set context for structured logging
    StructuredLogger.set_context(request_id=request_id)

    # Record start time
    start_time = time.time()

    try:
        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        metrics.record_request(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            duration=duration,
            request_size=int(request.headers.get('content-length', 0)),
            response_size=int(response.headers.get('content-length', 0))
        )

        # Log request
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration * 1000,
                "request_id": request_id
            }
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as e:
        duration = time.time() - start_time

        # Record error metrics
        metrics.record_error(type(e).__name__, severity="error")

        # Log error
        logger.error(
            f"Request failed: {str(e)}",
            exc_info=True,
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration * 1000,
                "request_id": request_id
            }
        )

        raise

    finally:
        # Clear context
        StructuredLogger.clear_context()


# ============================================================================
# 5. EXAMPLE API ENDPOINTS WITH MONITORING
# ============================================================================

class Order(BaseModel):
    """Order model"""
    symbol: str
    quantity: int
    price: float
    side: str  # 'buy' or 'sell'


@app.post("/api/v1/orders")
async def create_order(order: Order):
    """
    Create a new order with full monitoring

    This example shows:
    - Structured logging with context
    - Business metrics recording
    - Error handling with alerts
    - Performance tracking
    """
    start_time = time.time()

    try:
        logger.info(
            "Processing order",
            extra={
                "symbol": order.symbol,
                "quantity": order.quantity,
                "price": order.price,
                "side": order.side
            }
        )

        # Simulate order execution
        # In real implementation, this would call your trading service
        await simulate_order_execution(order)

        # Record business metrics
        volume = order.quantity * order.price
        metrics.record_trade(
            symbol=order.symbol,
            side=order.side,
            status="filled",
            volume=volume,
            pnl=None  # Will be calculated when position is closed
        )

        # Record signal execution
        metrics.record_signal(
            symbol=order.symbol,
            signal_type="manual_order",
            executed=True,
            status="filled"
        )

        # Log success
        duration = time.time() - start_time
        logger.info(
            "Order executed successfully",
            extra={
                "symbol": order.symbol,
                "volume": volume,
                "duration_ms": duration * 1000
            }
        )

        return {
            "status": "success",
            "order_id": "ORD-12345",
            "message": "Order executed successfully"
        }

    except Exception as e:
        # Record error metrics
        metrics.record_error(type(e).__name__, severity="error")
        health_check.error_count += 1

        # Log error with full context
        logger.error(
            f"Order execution failed: {str(e)}",
            exc_info=True,
            extra={
                "symbol": order.symbol,
                "quantity": order.quantity,
                "error_type": type(e).__name__
            }
        )

        # Send alert for critical errors
        alert = create_error_alert(
            source="trading_engine",
            error=e,
            context={
                "symbol": order.symbol,
                "order_type": "market",
                "side": order.side
            }
        )
        await alert_manager.send_alert(alert)

        # Record alert metrics
        metrics.record_alert(alert_type="order_execution_error", channel="slack")

        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/portfolio/risk")
async def get_risk_metrics():
    """
    Get portfolio risk metrics

    This example shows risk monitoring and alerting
    """
    try:
        # Simulate fetching risk metrics
        # In real implementation, this would query your risk manager
        risk_metrics = {
            "drawdown": 15.5,
            "max_drawdown": 20.0,
            "var_95": 500000,
            "portfolio_beta": 1.2,
            "sharpe_ratio": 1.8
        }

        # Update metrics
        metrics.update_drawdown(risk_metrics["drawdown"])
        metrics.update_var(risk_metrics["var_95"], confidence="95")

        # Check if risk thresholds are breached
        if risk_metrics["drawdown"] > 25.0:
            # Create and send risk alert
            alert = create_risk_alert(
                violation_type="drawdown",
                current_value=risk_metrics["drawdown"],
                threshold=25.0,
                context=risk_metrics
            )
            await alert_manager.send_alert(alert)

            # Record risk violation
            metrics.record_risk_violation("max_drawdown")

        # Log risk check
        logger.info(
            "Risk metrics checked",
            extra={
                "drawdown": risk_metrics["drawdown"],
                "var_95": risk_metrics["var_95"]
            }
        )

        return risk_metrics

    except Exception as e:
        logger.error(f"Failed to fetch risk metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/reports/daily")
async def generate_daily_report(db: Optional[AsyncSession] = None):
    """
    Generate and send daily report

    This endpoint can be called manually or via cron job
    """
    try:
        logger.info("Generating daily report")

        # Generate summary
        summary = await report_generator.generate_daily_summary(db)

        # Send report
        await report_generator.send_daily_report(
            summary,
            send_email=True,
            send_slack=True
        )

        logger.info("Daily report sent successfully")

        return {
            "status": "success",
            "message": "Daily report sent",
            "summary": summary.dict()
        }

    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 6. HELPER FUNCTIONS
# ============================================================================

async def simulate_order_execution(order: Order):
    """Simulate order execution"""
    import asyncio
    import random

    # Simulate processing time
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # Simulate occasional failures
    if random.random() < 0.05:  # 5% failure rate
        raise Exception("Order execution failed: Insufficient liquidity")

    return True


# ============================================================================
# 7. SCHEDULED TASKS (using APScheduler or Celery)
# ============================================================================

async def scheduled_daily_report():
    """
    Scheduled task to send daily report

    This should be called by a scheduler (APScheduler, Celery, cron)
    at a specific time each day (e.g., 6 PM after market close)
    """
    try:
        logger.info("Running scheduled daily report")

        # Get database session (implement based on your setup)
        db_session = None  # await get_db_session()

        # Generate and send report
        summary = await report_generator.generate_daily_summary(db_session)
        await report_generator.send_daily_report(summary)

        logger.info("Scheduled daily report completed")

    except Exception as e:
        logger.error(f"Scheduled daily report failed: {e}", exc_info=True)

        # Send alert about failed report
        alert = Alert(
            level=AlertLevel.ERROR,
            title="Daily Report Failed",
            message=f"Failed to generate daily report: {str(e)}",
            source="trading_engine",
            timestamp=datetime.now(),
            metadata={"error": str(e)},
            tags=["report", "scheduled_task"]
        )
        await alert_manager.send_alert(alert)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "example_integration:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )
