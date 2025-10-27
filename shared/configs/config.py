"""
Application configuration using Pydantic settings.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "Korean Stock Trading System"
    debug: bool = False

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/stock_trading"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # API Keys (for Korean stock data providers)
    krx_api_key: Optional[str] = None
    koreainvestment_api_key: Optional[str] = None
    koreainvestment_api_secret: Optional[str] = None

    # Trading
    default_stop_loss_pct: float = 5.0
    default_take_profit_pct: float = 10.0
    max_position_size_pct: float = 10.0
    max_portfolio_risk_pct: float = 2.0

    # Service URLs
    data_collector_url: str = "http://localhost:8001"
    indicator_calculator_url: str = "http://localhost:8002"
    stock_screener_url: str = "http://localhost:8003"
    trading_engine_url: str = "http://localhost:8004"
    risk_manager_url: str = "http://localhost:8005"

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance
    """
    return Settings()
