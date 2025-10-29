"""
Prometheus Metrics Module

Provides Prometheus metrics collection and export for monitoring and alerting.
Includes business metrics, technical metrics, and SLA tracking.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from fastapi import APIRouter, Response


@dataclass
class ServiceMetrics:
    """
    Service-specific Prometheus metrics

    Usage:
        metrics = ServiceMetrics(service_name="trading_engine")

        # Record request
        metrics.requests_total.labels(method="POST", endpoint="/orders").inc()

        # Record latency
        metrics.request_duration.labels(method="POST", endpoint="/orders").observe(0.5)

        # Record business metric
        metrics.record_business_metric("trades_executed", 1, {"symbol": "005930"})
    """

    service_name: str
    registry: Optional[CollectorRegistry] = None

    def __post_init__(self):
        """Initialize Prometheus metrics"""
        if self.registry is None:
            self.registry = CollectorRegistry()

        # Service info
        self.service_info = Info(
            'service',
            'Service information',
            registry=self.registry
        )

        # HTTP Request metrics
        self.requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request latency',
            ['method', 'endpoint'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )

        self.request_size = Summary(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )

        self.response_size = Summary(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )

        # Database metrics
        self.db_queries_total = Counter(
            'database_queries_total',
            'Total database queries',
            ['operation', 'table', 'status'],
            registry=self.registry
        )

        self.db_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration',
            ['operation', 'table'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=self.registry
        )

        self.db_connections = Gauge(
            'database_connections',
            'Active database connections',
            ['state'],
            registry=self.registry
        )

        # Cache metrics
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_name'],
            registry=self.registry
        )

        self.cache_misses = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_name'],
            registry=self.registry
        )

        # Business metrics - Trading
        self.trades_executed = Counter(
            'trades_executed_total',
            'Total trades executed',
            ['symbol', 'side', 'status'],
            registry=self.registry
        )

        self.trade_volume = Counter(
            'trade_volume_krw',
            'Total trade volume in KRW',
            ['symbol', 'side'],
            registry=self.registry
        )

        self.trade_pnl = Counter(
            'trade_pnl_krw',
            'Trade profit/loss in KRW',
            ['symbol'],
            registry=self.registry
        )

        self.positions_active = Gauge(
            'positions_active',
            'Number of active positions',
            registry=self.registry
        )

        self.portfolio_value = Gauge(
            'portfolio_value_krw',
            'Portfolio value in KRW',
            registry=self.registry
        )

        # Risk metrics
        self.risk_violations = Counter(
            'risk_violations_total',
            'Total risk violations',
            ['violation_type'],
            registry=self.registry
        )

        self.portfolio_drawdown = Gauge(
            'portfolio_drawdown_percent',
            'Portfolio drawdown percentage',
            registry=self.registry
        )

        self.var_risk = Gauge(
            'value_at_risk_krw',
            'Value at Risk in KRW',
            ['confidence'],
            registry=self.registry
        )

        # Signal metrics
        self.signals_generated = Counter(
            'signals_generated_total',
            'Total signals generated',
            ['symbol', 'signal_type'],
            registry=self.registry
        )

        self.signals_executed = Counter(
            'signals_executed_total',
            'Total signals executed',
            ['symbol', 'signal_type', 'status'],
            registry=self.registry
        )

        # Data collection metrics
        self.stocks_collected = Counter(
            'stocks_collected_total',
            'Total stocks collected',
            ['market'],
            registry=self.registry
        )

        self.data_collection_errors = Counter(
            'data_collection_errors_total',
            'Data collection errors',
            ['source', 'error_type'],
            registry=self.registry
        )

        # System metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'severity'],
            registry=self.registry
        )

        self.alerts_sent = Counter(
            'alerts_sent_total',
            'Total alerts sent',
            ['alert_type', 'channel'],
            registry=self.registry
        )

        # Custom business metrics
        self.custom_counters: Dict[str, Counter] = {}
        self.custom_gauges: Dict[str, Gauge] = {}

    def set_service_info(self, version: str, environment: str = "production"):
        """Set service information"""
        self.service_info.info({
            'service_name': self.service_name,
            'version': version,
            'environment': environment
        })

    def record_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None
    ):
        """Record HTTP request metrics"""
        self.requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()

        self.request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        if request_size:
            self.request_size.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)

        if response_size:
            self.response_size.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)

    def record_db_query(
        self,
        operation: str,
        table: str,
        duration: float,
        status: str = "success"
    ):
        """Record database query metrics"""
        self.db_queries_total.labels(
            operation=operation,
            table=table,
            status=status
        ).inc()

        self.db_query_duration.labels(
            operation=operation,
            table=table
        ).observe(duration)

    def update_db_connections(self, active: int, idle: int):
        """Update database connection metrics"""
        self.db_connections.labels(state='active').set(active)
        self.db_connections.labels(state='idle').set(idle)

    def record_cache_operation(self, cache_name: str, hit: bool):
        """Record cache hit or miss"""
        if hit:
            self.cache_hits.labels(cache_name=cache_name).inc()
        else:
            self.cache_misses.labels(cache_name=cache_name).inc()

    def record_trade(
        self,
        symbol: str,
        side: str,
        status: str,
        volume: float,
        pnl: Optional[float] = None
    ):
        """Record trade execution"""
        self.trades_executed.labels(
            symbol=symbol,
            side=side,
            status=status
        ).inc()

        self.trade_volume.labels(
            symbol=symbol,
            side=side
        ).inc(volume)

        if pnl is not None:
            self.trade_pnl.labels(symbol=symbol).inc(pnl)

    def update_positions(self, count: int):
        """Update active positions count"""
        self.positions_active.set(count)

    def update_portfolio_value(self, value: float):
        """Update portfolio value"""
        self.portfolio_value.set(value)

    def record_risk_violation(self, violation_type: str):
        """Record risk violation"""
        self.risk_violations.labels(violation_type=violation_type).inc()

    def update_drawdown(self, percent: float):
        """Update portfolio drawdown"""
        self.portfolio_drawdown.set(percent)

    def update_var(self, var_value: float, confidence: str = "95"):
        """Update Value at Risk"""
        self.var_risk.labels(confidence=confidence).set(var_value)

    def record_signal(
        self,
        symbol: str,
        signal_type: str,
        executed: bool = False,
        status: Optional[str] = None
    ):
        """Record signal generation and execution"""
        self.signals_generated.labels(
            symbol=symbol,
            signal_type=signal_type
        ).inc()

        if executed and status:
            self.signals_executed.labels(
                symbol=symbol,
                signal_type=signal_type,
                status=status
            ).inc()

    def record_data_collection(
        self,
        market: str,
        count: int,
        error: Optional[str] = None,
        source: Optional[str] = None
    ):
        """Record data collection"""
        if not error:
            self.stocks_collected.labels(market=market).inc(count)
        else:
            self.data_collection_errors.labels(
                source=source or "unknown",
                error_type=error
            ).inc()

    def record_error(self, error_type: str, severity: str = "error"):
        """Record error"""
        self.errors_total.labels(
            error_type=error_type,
            severity=severity
        ).inc()

    def record_alert(self, alert_type: str, channel: str):
        """Record alert sent"""
        self.alerts_sent.labels(
            alert_type=alert_type,
            channel=channel
        ).inc()

    def record_business_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        metric_type: str = "counter"
    ):
        """Record custom business metric"""
        if metric_type == "counter":
            if metric_name not in self.custom_counters:
                label_names = list(labels.keys()) if labels else []
                self.custom_counters[metric_name] = Counter(
                    metric_name,
                    f'Custom counter: {metric_name}',
                    label_names,
                    registry=self.registry
                )

            counter = self.custom_counters[metric_name]
            if labels:
                counter.labels(**labels).inc(value)
            else:
                counter.inc(value)

        elif metric_type == "gauge":
            if metric_name not in self.custom_gauges:
                label_names = list(labels.keys()) if labels else []
                self.custom_gauges[metric_name] = Gauge(
                    metric_name,
                    f'Custom gauge: {metric_name}',
                    label_names,
                    registry=self.registry
                )

            gauge = self.custom_gauges[metric_name]
            if labels:
                gauge.labels(**labels).set(value)
            else:
                gauge.set(value)

    def export_metrics(self) -> bytes:
        """Export metrics in Prometheus format"""
        return generate_latest(self.registry)


class MetricsCollector:
    """
    Global metrics collector singleton

    Usage:
        collector = MetricsCollector.get_instance()
        metrics = collector.get_service_metrics("trading_engine")
    """

    _instance = None
    _metrics: Dict[str, ServiceMetrics] = {}

    @classmethod
    def get_instance(cls) -> "MetricsCollector":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_service_metrics(self, service_name: str) -> ServiceMetrics:
        """Get or create metrics for a service"""
        if service_name not in self._metrics:
            self._metrics[service_name] = ServiceMetrics(service_name=service_name)
        return self._metrics[service_name]

    def export_all_metrics(self) -> bytes:
        """Export all metrics"""
        # For now, just export the first service's metrics
        # In production, you'd want a global registry
        if self._metrics:
            first_service = next(iter(self._metrics.values()))
            return first_service.export_metrics()
        return b""


def create_metrics_router(metrics: ServiceMetrics) -> APIRouter:
    """
    Create FastAPI router with metrics endpoint

    Args:
        metrics: ServiceMetrics instance

    Returns:
        APIRouter with /metrics endpoint
    """
    router = APIRouter(tags=["metrics"])

    @router.get("/metrics")
    async def get_metrics():
        """
        Prometheus metrics endpoint

        Returns metrics in Prometheus text format for scraping.
        """
        metrics_data = metrics.export_metrics()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

    return router


def measure_time(metrics: ServiceMetrics, operation: str, labels: Optional[Dict[str, str]] = None):
    """
    Decorator to measure execution time

    Usage:
        @measure_time(metrics, "calculate_indicators", {"symbol": "005930"})
        async def calculate_indicators(symbol):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                metrics.record_business_metric(
                    f"{operation}_duration_seconds",
                    duration,
                    labels,
                    metric_type="gauge"
                )
                return result
            except Exception as e:
                duration = time.time() - start
                metrics.record_error(type(e).__name__)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                metrics.record_business_metric(
                    f"{operation}_duration_seconds",
                    duration,
                    labels,
                    metric_type="gauge"
                )
                return result
            except Exception as e:
                duration = time.time() - start
                metrics.record_error(type(e).__name__)
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
