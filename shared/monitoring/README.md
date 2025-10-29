# Monitoring and Alerting System

Comprehensive monitoring, alerting, and observability solution for the Korean Stock Trading System.

## Table of Contents

- [Overview](#overview)
- [Components](#components)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Dashboards](#dashboards)
- [Alerting](#alerting)
- [Troubleshooting](#troubleshooting)

## Overview

The monitoring system provides:

- **Health Checks**: HTTP endpoints for service health monitoring
- **Metrics Collection**: Prometheus-based metrics for system and business metrics
- **Structured Logging**: JSON-based centralized logging
- **Resource Monitoring**: CPU, memory, disk, and network monitoring
- **Alerting**: Multi-channel alerts (Email, Slack, Webhooks)
- **Daily Reports**: Automated daily summary reports
- **Dashboards**: Grafana dashboards for visualization

## Components

### 1. Health Check Module (`health_check.py`)

Provides standardized health check endpoints for all services.

**Features:**
- Service health status (healthy, degraded, unhealthy)
- Dependency health checks (database, Redis, external APIs)
- System resource metrics
- FastAPI integration with `/health`, `/ready`, `/liveness` endpoints

### 2. Structured Logger (`structured_logger.py`)

JSON-based structured logging for centralized log aggregation.

**Features:**
- JSON log format
- Request correlation IDs
- Contextual logging with user/session tracking
- Performance logging
- Error logging with full context

### 3. Resource Monitor (`resource_monitor.py`)

System resource monitoring with threshold-based alerting.

**Features:**
- CPU usage monitoring
- Memory usage monitoring
- Disk usage monitoring
- Network traffic monitoring
- Process monitoring
- Threshold-based alerts

### 4. Metrics Collector (`metrics.py`)

Prometheus metrics collection and export.

**Features:**
- HTTP request metrics (count, latency, size)
- Database query metrics
- Cache hit/miss rates
- Business metrics (trades, P&L, signals)
- Risk metrics (drawdown, VaR, violations)
- Custom metric support

### 5. Alert Manager (`alerts.py`)

Multi-channel alerting system.

**Features:**
- Multiple alert levels (INFO, WARNING, ERROR, CRITICAL)
- Email alerts
- Slack notifications
- Webhook integration
- Alert cooldown to prevent spam
- Alert statistics

### 6. Report Generator (`reports.py`)

Automated daily summary report generation.

**Features:**
- Trading statistics
- Portfolio performance
- Risk metrics
- System health
- Top performers
- Email and Slack delivery

## Quick Start

### 1. Start Monitoring Infrastructure

```bash
cd docker
docker-compose up -d prometheus grafana
```

This starts:
- Prometheus on http://localhost:9090
- Grafana on http://localhost:3000 (admin/admin)

### 2. Add Monitoring to Your Service

```python
from fastapi import FastAPI
from shared.monitoring import (
    HealthCheck,
    ServiceMetrics,
    StructuredLogger,
    ResourceMonitor,
    AlertManager,
    create_health_router,
    create_metrics_router
)

# Initialize monitoring components
app = FastAPI()

# Structured logger
logger = StructuredLogger.get_logger("trading_engine", json_format=True)

# Health check
health_check = HealthCheck(
    service_name="trading_engine",
    version="1.0.0"
)

# Metrics
metrics = ServiceMetrics(service_name="trading_engine")
metrics.set_service_info(version="1.0.0", environment="production")

# Resource monitor
resource_monitor = ResourceMonitor(
    service_name="trading_engine"
)

# Alert manager
alert_manager = AlertManager(
    slack_webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    email_config={
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "alerts@example.com",
        "password": "your-password",
        "from_email": "alerts@example.com",
        "to_emails": ["admin@example.com"]
    }
)

# Add health and metrics endpoints
app.include_router(create_health_router(health_check))
app.include_router(create_metrics_router(metrics))

# Startup event
@app.on_event("startup")
async def startup():
    logger.info("Service starting", extra={"version": "1.0.0"})

    # Start resource monitoring
    async def alert_callback(alerts, resources):
        for alert_data in alerts:
            from shared.monitoring.alerts import create_resource_alert
            alert = create_resource_alert(
                alert_data["resource"],
                alert_data["value"],
                alert_data["threshold"]
            )
            await alert_manager.send_alert(alert)

    await resource_monitor.start_monitoring(interval=60, callback=alert_callback)

# Example endpoint with monitoring
@app.post("/trade")
async def execute_trade(order: Order):
    # Record request
    start_time = time.time()

    try:
        # Execute trade
        result = await trading_service.execute(order)

        # Record metrics
        metrics.record_trade(
            symbol=order.symbol,
            side=order.side,
            status="success",
            volume=order.quantity * order.price
        )

        # Log event
        logger.info(
            "Trade executed",
            extra={
                "order_id": order.id,
                "symbol": order.symbol,
                "quantity": order.quantity,
                "price": order.price
            }
        )

        duration = time.time() - start_time
        metrics.record_request("POST", "/trade", 200, duration)

        return result

    except Exception as e:
        # Record error
        metrics.record_error(type(e).__name__)

        # Log error
        logger.error(f"Trade execution failed: {e}", exc_info=True)

        # Send alert if critical
        from shared.monitoring.alerts import create_error_alert
        alert = create_error_alert("trading_engine", e, {"order_id": order.id})
        await alert_manager.send_alert(alert)

        raise
```

## Usage Examples

### Health Check

```python
from shared.monitoring import HealthCheck

health = HealthCheck(service_name="my_service", version="1.0.0")

# Get health status
status = await health.get_health(db_session, redis_client)
print(f"Status: {status.status}")
print(f"Uptime: {status.uptime_seconds}s")
```

### Structured Logging

```python
from shared.monitoring import get_logger, StructuredLogger

# Get logger
logger = get_logger("my_service", json_format=True)

# Set request context
StructuredLogger.set_context(
    request_id="req-123",
    user_id="user-456"
)

# Log with context
logger.info("Processing request", extra={
    "endpoint": "/api/trade",
    "method": "POST"
})

# Log performance
from shared.monitoring.structured_logger import log_performance
log_performance(logger, "database_query", 150.5, table="trades")

# Log business event
from shared.monitoring.structured_logger import log_business_event
log_business_event(logger, "trade_executed", symbol="005930", quantity=10)
```

### Resource Monitoring

```python
from shared.monitoring import ResourceMonitor, ResourceThresholds

# Create monitor with custom thresholds
monitor = ResourceMonitor(
    service_name="my_service",
    thresholds=ResourceThresholds(
        cpu_warning=70.0,
        cpu_critical=90.0,
        memory_warning=80.0,
        memory_critical=95.0
    )
)

# Get current resources
resources = monitor.get_resources()
print(f"CPU: {resources.cpu_percent}%")
print(f"Memory: {resources.memory_percent}%")

# Check thresholds
alerts = monitor.check_thresholds()
for alert in alerts:
    print(f"{alert['level']}: {alert['message']}")

# Get statistics
stats = monitor.get_statistics(window_minutes=60)
print(f"Avg CPU: {stats['cpu']['avg']:.1f}%")
```

### Metrics Collection

```python
from shared.monitoring import ServiceMetrics

metrics = ServiceMetrics(service_name="trading_engine")

# Record HTTP request
metrics.record_request(
    method="POST",
    endpoint="/orders",
    status=200,
    duration=0.5,
    request_size=1024,
    response_size=512
)

# Record database query
metrics.record_db_query(
    operation="INSERT",
    table="trades",
    duration=0.05,
    status="success"
)

# Record trade
metrics.record_trade(
    symbol="005930",
    side="buy",
    status="filled",
    volume=750000,
    pnl=15000
)

# Update portfolio metrics
metrics.update_portfolio_value(10500000)
metrics.update_positions(5)
metrics.update_drawdown(3.5)

# Export metrics (called by Prometheus)
metrics_data = metrics.export_metrics()
```

### Alerting

```python
from shared.monitoring import AlertManager, Alert, AlertLevel
from datetime import datetime

alert_manager = AlertManager(
    slack_webhook_url="https://hooks.slack.com/...",
    email_config={...}
)

# Send custom alert
alert = Alert(
    level=AlertLevel.CRITICAL,
    title="Trading Halt",
    message="Portfolio drawdown exceeded 28%",
    source="risk_manager",
    timestamp=datetime.now(),
    metadata={"drawdown": 30.5, "portfolio_value": 7200000},
    tags=["trading_halt", "risk"]
)

await alert_manager.send_alert(alert)

# Use predefined alert templates
from shared.monitoring.alerts import (
    create_error_alert,
    create_risk_alert,
    create_trading_halt_alert
)

# Error alert
error_alert = create_error_alert(
    source="trading_engine",
    error=exception,
    context={"order_id": "12345"}
)

# Risk alert
risk_alert = create_risk_alert(
    violation_type="max_drawdown",
    current_value=30.5,
    threshold=28.0,
    context={"portfolio_id": "main"}
)

# Trading halt
halt_alert = create_trading_halt_alert(
    reason="max_drawdown_exceeded",
    drawdown=30.5
)
```

### Daily Reports

```python
from shared.monitoring import ReportGenerator

report_gen = ReportGenerator(
    email_config={...},
    slack_webhook_url="https://..."
)

# Generate daily summary
summary = await report_gen.generate_daily_summary(db_session)

# Send report
await report_gen.send_daily_report(
    summary,
    send_email=True,
    send_slack=True
)
```

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Service Configuration
SERVICE_NAME=trading_engine
ENVIRONMENT=production

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=8000

# Alerting - Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=alerts@example.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_FROM=alerts@example.com
ALERT_EMAIL_TO=admin@example.com,team@example.com

# Alerting - Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#trading-alerts

# Resource Thresholds
CPU_WARNING_THRESHOLD=70.0
CPU_CRITICAL_THRESHOLD=90.0
MEMORY_WARNING_THRESHOLD=80.0
MEMORY_CRITICAL_THRESHOLD=95.0
DISK_WARNING_THRESHOLD=85.0
DISK_CRITICAL_THRESHOLD=95.0

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=/var/log/stock-trading
```

### Prometheus Configuration

Edit `docker/prometheus/prometheus.yml` to add your services:

```yaml
scrape_configs:
  - job_name: 'my-service'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['my-service:8000']
        labels:
          service: 'my-service'
          team: 'trading'
```

## Dashboards

### Access Grafana

1. Open http://localhost:3000
2. Login with `admin` / `admin`
3. Navigate to Dashboards

### Available Dashboards

1. **System Overview**
   - CPU, Memory, Disk usage
   - HTTP request rates and latency
   - Error rates
   - Database query performance

2. **Trading Metrics**
   - Trade execution rates
   - Portfolio value and P&L
   - Active positions
   - Risk metrics (drawdown, VaR)
   - Signal generation vs execution

### Creating Custom Dashboards

1. Go to Dashboards → New Dashboard
2. Add Panel
3. Use PromQL queries:

```promql
# Request rate
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(errors_total[5m])

# Active trades
trades_executed_total

# Portfolio value
portfolio_value_krw
```

## Alerting

### Alert Rules

Configure alert rules in Prometheus or Grafana:

**High Error Rate:**
```yaml
- alert: HighErrorRate
  expr: rate(errors_total[5m]) > 10
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"
```

**High CPU Usage:**
```yaml
- alert: HighCPUUsage
  expr: system_cpu_percent > 90
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "CPU usage above 90%"
```

**Trading Halt:**
```yaml
- alert: TradingHalt
  expr: portfolio_drawdown_percent > 28
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Trading halt threshold exceeded"
```

### Alert Channels

Configure in your service initialization:

```python
alert_manager = AlertManager(
    # Email
    email_config={
        "smtp_host": os.getenv("SMTP_HOST"),
        "smtp_port": int(os.getenv("SMTP_PORT")),
        "username": os.getenv("SMTP_USERNAME"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from_email": os.getenv("ALERT_EMAIL_FROM"),
        "to_emails": os.getenv("ALERT_EMAIL_TO").split(",")
    },
    # Slack
    slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
    slack_channel=os.getenv("SLACK_CHANNEL"),
    # Webhooks
    webhook_urls=[
        "https://your-webhook-endpoint.com/alerts"
    ]
)
```

## Troubleshooting

### Metrics Not Showing in Prometheus

1. Check if service is exposing `/metrics` endpoint
2. Verify Prometheus can reach the service:
   ```bash
   docker exec prometheus wget -O- http://trading-engine:8000/metrics
   ```
3. Check Prometheus targets: http://localhost:9090/targets
4. Review Prometheus logs:
   ```bash
   docker logs prometheus
   ```

### Grafana Dashboard Empty

1. Verify Prometheus datasource is configured
2. Check if metrics are being collected in Prometheus
3. Verify dashboard queries are correct
4. Check time range in dashboard

### Alerts Not Being Sent

1. Check alert manager configuration
2. Verify SMTP/Slack credentials
3. Check alert cooldown settings
4. Review service logs for errors
5. Test alert manually:
   ```python
   from shared.monitoring import AlertManager, Alert, AlertLevel
   alert_manager = AlertManager(...)
   alert = Alert(...)
   await alert_manager.send_alert(alert)
   ```

### High Memory Usage

1. Check log rotation settings
2. Verify metric history limits
3. Monitor resource_monitor.max_history
4. Adjust Prometheus retention time

### JSON Logs Not Structured

1. Verify `json_format=True` in logger setup
2. Check `pythonjsonlogger` is installed
3. Ensure using `StructuredLogger` not standard logging

## Best Practices

1. **Always use structured logging** with contextual information
2. **Set request context** for request tracing
3. **Record both technical and business metrics**
4. **Configure alert cooldowns** to prevent spam
5. **Monitor resource usage** continuously
6. **Review dashboards regularly** for anomalies
7. **Test alerts** before production deployment
8. **Rotate logs** to prevent disk fill
9. **Set appropriate retention** for metrics and logs
10. **Document custom metrics** and their meaning

## Support

For issues or questions:
1. Check logs in `/var/log/stock-trading/`
2. Review Grafana dashboards for anomalies
3. Check Prometheus metrics collection
4. Review this documentation
5. Open an issue in the repository

## License

MIT License - See LICENSE file for details
