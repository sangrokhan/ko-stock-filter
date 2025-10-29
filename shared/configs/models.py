"""
Configuration models using Pydantic for validation.
"""
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class PositionSizingMethod(str, Enum):
    """Position sizing calculation methods."""
    FIXED_PERCENTAGE = "fixed_percentage"
    KELLY_CRITERION = "kelly_criterion"
    KELLY_HALF = "kelly_half"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    RISK_PARITY = "risk_parity"


class MarketType(str, Enum):
    """Korean stock market types."""
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"
    KONEX = "KONEX"


# =============================================================================
# Database Configuration
# =============================================================================

class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    url: str = Field(description="Database connection URL")
    pool_size: int = Field(default=5, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, le=100, description="Max overflow connections")
    pool_timeout: int = Field(default=30, ge=1, le=300, description="Pool timeout in seconds")
    echo: bool = Field(default=False, description="Echo SQL queries")


class RedisConfig(BaseModel):
    """Redis connection configuration."""
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    max_connections: int = Field(default=10, ge=1, le=100, description="Max connections")


# =============================================================================
# Trading Configuration
# =============================================================================

class ConvictionWeights(BaseModel):
    """Weights for conviction score calculation."""
    weight_value: float = Field(default=0.30, ge=0.0, le=1.0, description="Value score weight")
    weight_momentum: float = Field(default=0.30, ge=0.0, le=1.0, description="Momentum score weight")
    weight_volume: float = Field(default=0.20, ge=0.0, le=1.0, description="Volume score weight")
    weight_quality: float = Field(default=0.20, ge=0.0, le=1.0, description="Quality score weight")

    @field_validator('weight_value', 'weight_momentum', 'weight_volume', 'weight_quality')
    @classmethod
    def validate_weight_sum(cls, v, info):
        """Validate that all weights sum to 1.0."""
        # Note: This is a simplified validation. Full validation happens after all fields are set.
        return v

    def validate_weights_sum(self) -> None:
        """Validate that all weights sum to approximately 1.0."""
        total = self.weight_value + self.weight_momentum + self.weight_volume + self.weight_quality
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Conviction weights must sum to 1.0, got {total}")


class SignalGeneratorConfig(BaseModel):
    """Signal generator configuration."""
    risk_tolerance: float = Field(default=2.0, ge=0.1, le=10.0, description="Portfolio risk tolerance (%)")
    max_position_size_pct: float = Field(default=10.0, ge=1.0, le=50.0, description="Max position size (%)")
    min_conviction_score: float = Field(default=60.0, ge=0.0, le=100.0, description="Min conviction score")
    use_limit_orders: bool = Field(default=True, description="Use limit orders")
    limit_order_discount_pct: float = Field(default=1.0, ge=0.0, le=10.0, description="Limit order discount (%)")
    conviction_weights: ConvictionWeights = Field(default_factory=ConvictionWeights)


class SignalValidatorConfig(BaseModel):
    """Signal validator configuration."""
    max_positions: int = Field(default=20, ge=1, le=100, description="Max concurrent positions")
    max_concentration_pct: float = Field(default=30.0, ge=5.0, le=100.0, description="Max position concentration (%)")
    max_sector_concentration_pct: float = Field(default=40.0, ge=10.0, le=100.0, description="Max sector concentration (%)")
    require_recent_data_hours: int = Field(default=48, ge=1, le=168, description="Required data freshness (hours)")
    min_data_quality_score: float = Field(default=75.0, ge=0.0, le=100.0, description="Min data quality score")


class CommissionConfig(BaseModel):
    """Commission and fee configuration."""
    commission_rate: float = Field(default=0.00015, ge=0.0, le=0.01, description="Commission rate (0.015%)")
    transaction_tax_rate: float = Field(default=0.0023, ge=0.0, le=0.01, description="Transaction tax (0.23%)")
    agri_fish_tax_rate: float = Field(default=0.0015, ge=0.0, le=0.01, description="Agriculture/Fishery tax (0.15%)")
    min_commission: float = Field(default=0.0, ge=0.0, le=10000.0, description="Minimum commission (KRW)")


class TradingEngineConfig(BaseModel):
    """Trading engine configuration."""
    signal_generator: SignalGeneratorConfig = Field(default_factory=SignalGeneratorConfig)
    signal_validator: SignalValidatorConfig = Field(default_factory=SignalValidatorConfig)
    commission: CommissionConfig = Field(default_factory=CommissionConfig)
    dry_run: bool = Field(default=True, description="Dry run mode (paper trading)")
    enable_notifications: bool = Field(default=True, description="Enable trade notifications")


# =============================================================================
# Risk Management Configuration
# =============================================================================

class RiskParameters(BaseModel):
    """Risk management parameters."""
    max_position_size_pct: float = Field(default=10.0, ge=1.0, le=50.0, description="Max position size (%)")
    max_portfolio_risk_pct: float = Field(default=2.0, ge=0.1, le=10.0, description="Max portfolio risk (%)")
    max_drawdown_pct: float = Field(default=20.0, ge=5.0, le=50.0, description="Max drawdown (%)")
    stop_loss_pct: float = Field(default=5.0, ge=1.0, le=20.0, description="Stop loss (%)")
    take_profit_pct: float = Field(default=10.0, ge=1.0, le=50.0, description="Take profit (%)")
    max_leverage: float = Field(default=1.0, ge=1.0, le=3.0, description="Max leverage")
    max_total_loss_pct: float = Field(default=28.0, ge=10.0, le=50.0, description="Emergency liquidation threshold (%)")
    trailing_stop_enabled: bool = Field(default=False, description="Enable trailing stop loss")
    trailing_stop_distance_pct: float = Field(default=3.0, ge=1.0, le=10.0, description="Trailing stop distance (%)")


class PositionSizingConfig(BaseModel):
    """Position sizing configuration."""
    method: PositionSizingMethod = Field(default=PositionSizingMethod.KELLY_HALF)
    fixed_percentage: float = Field(default=5.0, ge=1.0, le=20.0, description="Fixed position size (%)")
    kelly_fraction: float = Field(default=0.5, ge=0.1, le=1.0, description="Kelly criterion fraction")
    min_position_size_krw: float = Field(default=100000.0, ge=10000.0, description="Min position size (KRW)")
    max_position_size_krw: Optional[float] = Field(default=None, description="Max position size (KRW)")


class RiskManagerConfig(BaseModel):
    """Risk manager configuration."""
    risk_parameters: RiskParameters = Field(default_factory=RiskParameters)
    position_sizing: PositionSizingConfig = Field(default_factory=PositionSizingConfig)
    enable_circuit_breaker: bool = Field(default=True, description="Enable circuit breaker")
    circuit_breaker_threshold_pct: float = Field(default=15.0, ge=5.0, le=30.0, description="Circuit breaker threshold (%)")


# =============================================================================
# Stock Screening Configuration
# =============================================================================

class ScreeningThresholds(BaseModel):
    """Stock screening threshold parameters."""
    # Volatility
    max_volatility_pct: float = Field(default=40.0, ge=0.0, le=200.0, description="Max annualized volatility (%)")

    # Valuation
    max_per: float = Field(default=50.0, ge=0.0, le=1000.0, description="Max P/E ratio")
    max_pbr: float = Field(default=5.0, ge=0.0, le=50.0, description="Max P/B ratio")
    undervalued_pbr_threshold: float = Field(default=1.0, ge=0.1, le=5.0, description="Undervalued PBR threshold")
    per_industry_avg_multiplier: float = Field(default=1.0, ge=0.1, le=5.0, description="PER vs industry avg multiplier")

    # Financial health
    max_debt_ratio_pct: float = Field(default=200.0, ge=0.0, le=1000.0, description="Max debt ratio (%)")
    min_current_ratio: float = Field(default=1.0, ge=0.0, le=10.0, description="Min current ratio")

    # Liquidity
    min_avg_volume: int = Field(default=100000, ge=1000, description="Min avg daily volume")
    min_trading_value_krw: float = Field(default=100000000.0, ge=1000000.0, description="Min avg trading value (KRW)")

    # Data requirements
    min_price_history_days: int = Field(default=60, ge=20, le=365, description="Min price history days")
    min_volume_history_days: int = Field(default=20, ge=5, le=365, description="Min volume history days")


class StockScreenerConfig(BaseModel):
    """Stock screener configuration."""
    thresholds: ScreeningThresholds = Field(default_factory=ScreeningThresholds)
    enable_sector_filter: bool = Field(default=True, description="Enable sector filtering")
    excluded_sectors: list[str] = Field(default_factory=list, description="Excluded sector codes")
    max_results: int = Field(default=100, ge=10, le=1000, description="Max screening results")


# =============================================================================
# Indicator Configuration
# =============================================================================

class TechnicalIndicatorConfig(BaseModel):
    """Technical indicator calculation parameters."""
    # RSI
    rsi_period: int = Field(default=14, ge=2, le=100, description="RSI period")
    rsi_overbought: float = Field(default=70.0, ge=50.0, le=90.0, description="RSI overbought threshold")
    rsi_oversold: float = Field(default=30.0, ge=10.0, le=50.0, description="RSI oversold threshold")

    # MACD
    macd_fast_period: int = Field(default=12, ge=2, le=50, description="MACD fast period")
    macd_slow_period: int = Field(default=26, ge=5, le=100, description="MACD slow period")
    macd_signal_period: int = Field(default=9, ge=2, le=50, description="MACD signal period")

    # Moving Averages
    sma_short_period: int = Field(default=20, ge=5, le=100, description="Short SMA period")
    sma_medium_period: int = Field(default=50, ge=20, le=200, description="Medium SMA period")
    sma_long_period: int = Field(default=200, ge=50, le=500, description="Long SMA period")

    ema_short_period: int = Field(default=12, ge=5, le=100, description="Short EMA period")
    ema_medium_period: int = Field(default=26, ge=10, le=200, description="Medium EMA period")

    # Bollinger Bands
    bb_period: int = Field(default=20, ge=5, le=100, description="Bollinger Bands period")
    bb_std_dev: float = Field(default=2.0, ge=1.0, le=5.0, description="Bollinger Bands std dev")

    # ATR
    atr_period: int = Field(default=14, ge=2, le=100, description="ATR period")


class IndicatorCalculatorConfig(BaseModel):
    """Indicator calculator configuration."""
    indicators: TechnicalIndicatorConfig = Field(default_factory=TechnicalIndicatorConfig)
    enable_caching: bool = Field(default=True, description="Enable result caching")
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400, description="Cache TTL in seconds")


# =============================================================================
# Data Collector Configuration
# =============================================================================

class SchedulerConfig(BaseModel):
    """Data collection scheduler configuration."""
    # Cron expressions for different jobs
    market_data_cron: str = Field(default="0 9-15 * * 1-5", description="Market data collection cron (weekdays 9am-3pm)")
    financial_data_cron: str = Field(default="0 18 * * 1-5", description="Financial data collection cron (weekdays 6pm)")
    fundamental_data_cron: str = Field(default="0 0 * * 0", description="Fundamental data collection cron (Sunday midnight)")

    # Retry settings
    max_retries: int = Field(default=3, ge=1, le=10, description="Max retry attempts")
    retry_delay_seconds: int = Field(default=60, ge=10, le=600, description="Retry delay in seconds")

    # Timezone
    timezone: str = Field(default="Asia/Seoul", description="Scheduler timezone")


class DataCollectorConfig(BaseModel):
    """Data collector configuration."""
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    enable_scheduler: bool = Field(default=True, description="Enable scheduled collection")
    batch_size: int = Field(default=100, ge=10, le=1000, description="Batch size for bulk operations")
    request_timeout_seconds: int = Field(default=30, ge=5, le=300, description="API request timeout")


# =============================================================================
# Price Monitor Configuration
# =============================================================================

class PriceMonitorConfig(BaseModel):
    """Price monitor configuration."""
    poll_interval_seconds: int = Field(default=60, ge=10, le=300, description="Polling interval")
    significant_change_threshold_pct: float = Field(default=5.0, ge=0.1, le=20.0, description="Significant price change (%)")
    market_open_hour: int = Field(default=9, ge=0, le=23, description="Market open hour")
    market_close_hour: int = Field(default=15, ge=0, le=23, description="Market close hour")
    max_concurrent_updates: int = Field(default=10, ge=1, le=100, description="Max concurrent price updates")
    alert_enabled: bool = Field(default=True, description="Enable price alerts")


# =============================================================================
# Logging Configuration
# =============================================================================

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json or text)")
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_file_size_mb: int = Field(default=100, ge=1, le=1000, description="Max log file size (MB)")
    backup_count: int = Field(default=5, ge=1, le=30, description="Number of backup log files")

    @field_validator('level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
