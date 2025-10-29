"""
Monitoring and Alerting Module

This module provides comprehensive monitoring, alerting, and observability
for the Korean Stock Trading System.

Components:
- Health checks for all services
- Prometheus metrics collection
- Structured logging with JSON format
- System resource monitoring (CPU, memory, disk)
- Alert management for errors and threshold breaches
- Daily summary reports (email/Slack)
- Grafana dashboard integration
"""

from .health_check import HealthCheck, HealthStatus, DependencyHealth
from .metrics import MetricsCollector, ServiceMetrics
from .structured_logger import StructuredLogger, get_logger
from .resource_monitor import ResourceMonitor, SystemResources
from .alerts import AlertManager, AlertLevel, Alert
from .reports import ReportGenerator, DailySummary

__all__ = [
    "HealthCheck",
    "HealthStatus",
    "DependencyHealth",
    "MetricsCollector",
    "ServiceMetrics",
    "StructuredLogger",
    "get_logger",
    "ResourceMonitor",
    "SystemResources",
    "AlertManager",
    "AlertLevel",
    "Alert",
    "ReportGenerator",
    "DailySummary",
]
