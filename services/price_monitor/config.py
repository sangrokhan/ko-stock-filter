"""
Configuration for Price Monitor Service.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class PriceMonitorSettings(BaseSettings):
    """Price Monitor service settings."""

    # Service
    service_name: str = "price_monitor"
    debug: bool = False

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/stock_trading"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Monitoring
    poll_interval_seconds: int = 60  # Poll every 1 minute (60 seconds)
    significant_change_threshold: float = 5.0  # 5% change threshold

    # Market Hours (KST)
    market_open_hour: int = 9
    market_open_minute: int = 0
    market_close_hour: int = 15
    market_close_minute: int = 30

    # Performance
    max_concurrent_updates: int = 10  # Maximum concurrent stock updates
    request_timeout_seconds: int = 30  # API request timeout

    # Retry Settings
    max_retries: int = 3
    retry_delay_seconds: int = 5

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # API Keys for Korean stock data providers
    koreainvestment_api_key: Optional[str] = None
    koreainvestment_api_secret: Optional[str] = None
    koreainvestment_app_key: Optional[str] = None
    koreainvestment_app_secret: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "PRICE_MONITOR_"


@lru_cache()
def get_settings() -> PriceMonitorSettings:
    """
    Get cached settings instance.

    Returns:
        PriceMonitorSettings instance
    """
    return PriceMonitorSettings()
