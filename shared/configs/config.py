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

    # Stock Screening Thresholds
    # Volatility filter
    max_volatility_pct: float = 40.0  # Maximum annualized volatility percentage

    # Valuation filters
    max_per: float = 50.0  # Maximum Price-to-Earnings Ratio
    max_pbr: float = 5.0   # Maximum Price-to-Book Ratio

    # Financial health filters
    max_debt_ratio_pct: float = 200.0  # Maximum debt ratio percentage

    # Liquidity filters
    min_avg_volume: int = 100000  # Minimum average daily volume
    min_trading_value: float = 100000000.0  # Minimum average trading value (KRW)

    # Undervalued stock identification
    undervalued_pbr_threshold: float = 1.0  # PBR threshold for undervalued stocks
    per_industry_avg_multiplier: float = 1.0  # PER relative to industry average

    # Minimum data requirements
    min_price_history_days: int = 60  # Minimum days of price history required
    min_volume_history_days: int = 20  # Minimum days of volume history required

    # Service URLs
    data_collector_url: str = "http://localhost:8001"
    indicator_calculator_url: str = "http://localhost:8002"
    stock_screener_url: str = "http://localhost:8003"
    trading_engine_url: str = "http://localhost:8004"
    risk_manager_url: str = "http://localhost:8005"

    # Logging
    log_level: str = "INFO"
    log_format: str = "text"
    log_file: Optional[str] = None

    # Price Monitor
    price_monitor_url: str = "http://localhost:8006"

    # General
    environment: str = "development"

    # SMTP
    smtp_port: int = 587

    # Metrics
    enable_metrics: bool = False
    metrics_port: int = 9090

    # Trading
    force_paper_trading: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"  # Allow extra fields from .env file
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance
    """
    return Settings()
