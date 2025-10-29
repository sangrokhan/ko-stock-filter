"""
Structured Logging Module

Provides JSON-based structured logging for centralized log aggregation.
Includes request tracing, correlation IDs, and contextual information.
"""

import logging
import sys
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
from pathlib import Path
import os

from pythonjsonlogger import jsonlogger


# Context variables for request tracing
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


class ContextFilter(logging.Filter):
    """Filter that adds contextual information to log records"""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context variables to the log record"""
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.session_id = session_id_var.get()
        record.service_name = os.getenv('SERVICE_NAME', 'unknown')
        record.environment = os.getenv('ENVIRONMENT', 'development')
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """Add custom fields to the log record"""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat()

        # Add log level
        log_record['level'] = record.levelname

        # Add logger name
        log_record['logger'] = record.name

        # Add file location
        log_record['file'] = f"{record.filename}:{record.lineno}"

        # Add function name
        log_record['function'] = record.funcName

        # Add context from ContextFilter
        if hasattr(record, 'request_id') and record.request_id:
            log_record['request_id'] = record.request_id

        if hasattr(record, 'user_id') and record.user_id:
            log_record['user_id'] = record.user_id

        if hasattr(record, 'session_id') and record.session_id:
            log_record['session_id'] = record.session_id

        if hasattr(record, 'service_name'):
            log_record['service_name'] = record.service_name

        if hasattr(record, 'environment'):
            log_record['environment'] = record.environment

        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Add extra fields from the log call
        for key, value in message_dict.items():
            if key not in log_record:
                log_record[key] = value


class StructuredLogger:
    """
    Structured logger with JSON output and contextual information

    Usage:
        logger = StructuredLogger.get_logger("trading_engine")
        logger.info("Order executed", extra={
            "order_id": "12345",
            "symbol": "005930",
            "quantity": 10,
            "price": 75000
        })
    """

    _loggers: Dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(
        cls,
        name: str,
        level: int = logging.INFO,
        log_file: Optional[Path] = None,
        json_format: bool = True
    ) -> logging.Logger:
        """
        Get or create a structured logger

        Args:
            name: Logger name (typically service name)
            level: Logging level (default: INFO)
            log_file: Optional file path for file logging
            json_format: Use JSON format (default: True)

        Returns:
            Configured logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers = []  # Clear existing handlers

        # Add context filter
        context_filter = ContextFilter()
        logger.addFilter(context_filter)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        if json_format:
            # JSON formatter for structured logging
            json_formatter = CustomJsonFormatter(
                '%(timestamp)s %(level)s %(service_name)s %(logger)s %(message)s'
            )
            console_handler.setFormatter(json_formatter)
        else:
            # Human-readable formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)

            if json_format:
                file_handler.setFormatter(json_formatter)
            else:
                file_handler.setFormatter(formatter)

            logger.addHandler(file_handler)

        cls._loggers[name] = logger
        return logger

    @classmethod
    def set_context(
        cls,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Set context variables for request tracing"""
        if request_id:
            request_id_var.set(request_id)
        if user_id:
            user_id_var.set(user_id)
        if session_id:
            session_id_var.set(session_id)

    @classmethod
    def clear_context(cls):
        """Clear context variables"""
        request_id_var.set(None)
        user_id_var.set(None)
        session_id_var.set(None)


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    json_format: bool = True
) -> logging.Logger:
    """
    Convenience function to get a structured logger

    Args:
        name: Logger name (typically service name)
        level: Logging level (default: INFO)
        log_file: Optional file path for file logging
        json_format: Use JSON format (default: True)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger("trading_engine")
        logger.info("Trade executed", extra={
            "symbol": "005930",
            "quantity": 10,
            "price": 75000
        })
    """
    return StructuredLogger.get_logger(name, level, log_file, json_format)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds service-specific context

    Usage:
        adapter = LoggerAdapter(logger, {"service": "trading_engine"})
        adapter.info("Processing trade", extra={"order_id": "12345"})
    """

    def process(self, msg, kwargs):
        """Add extra context to log calls"""
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        # Merge adapter context with call-specific extra
        kwargs['extra'].update(self.extra)

        return msg, kwargs


def setup_service_logger(
    service_name: str,
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    json_format: bool = True
) -> logging.Logger:
    """
    Set up logger for a service with standard configuration

    Args:
        service_name: Name of the service
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        json_format: Use JSON format

    Returns:
        Configured logger

    Example:
        logger = setup_service_logger("trading_engine", level="INFO", json_format=True)
    """
    # Set SERVICE_NAME environment variable
    os.environ['SERVICE_NAME'] = service_name

    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create log file path if log_dir specified
    log_file = None
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{service_name}.log"

    return get_logger(service_name, log_level, log_file, json_format)


# Convenience functions for common log patterns

def log_performance(logger: logging.Logger, operation: str, duration_ms: float, **kwargs):
    """Log performance metrics"""
    logger.info(
        f"Performance: {operation}",
        extra={
            "operation": operation,
            "duration_ms": duration_ms,
            "metric_type": "performance",
            **kwargs
        }
    )


def log_business_event(logger: logging.Logger, event_type: str, **kwargs):
    """Log business events"""
    logger.info(
        f"Business Event: {event_type}",
        extra={
            "event_type": event_type,
            "metric_type": "business_event",
            **kwargs
        }
    )


def log_error(logger: logging.Logger, error: Exception, context: Dict[str, Any] = None):
    """Log errors with full context"""
    extra = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "metric_type": "error"
    }

    if context:
        extra.update(context)

    logger.error(
        f"Error occurred: {str(error)}",
        exc_info=True,
        extra=extra
    )


def log_alert(logger: logging.Logger, alert_type: str, message: str, severity: str = "warning", **kwargs):
    """Log alerts that should trigger notifications"""
    log_level = logging.WARNING if severity == "warning" else logging.ERROR

    logger.log(
        log_level,
        f"ALERT [{alert_type}]: {message}",
        extra={
            "alert_type": alert_type,
            "severity": severity,
            "metric_type": "alert",
            **kwargs
        }
    )
