"""
Configuration for the Orchestrator Service.
"""
from typing import Optional
from pydantic import BaseModel, Field


class OrchestratorConfig(BaseModel):
    """Configuration for orchestrator scheduling."""

    # Timezone
    timezone: str = Field(
        default="Asia/Seoul",
        description="Timezone for all scheduled jobs"
    )

    # User ID for operations
    user_id: str = Field(
        default="default_user",
        description="User ID for trading operations"
    )

    # Schedule Times (24-hour format)
    data_collection_time: str = Field(
        default="16:00",
        description="Daily data collection time (after market close)"
    )

    indicator_calculation_time: str = Field(
        default="17:00",
        description="Daily indicator calculation time"
    )

    watchlist_update_time: str = Field(
        default="18:00",
        description="Daily watchlist update time"
    )

    signal_generation_time: str = Field(
        default="08:45",
        description="Daily signal generation time (before market open)"
    )

    # Market Hours (Korea Stock Market: 09:00 - 15:30)
    market_open_time: str = Field(
        default="09:00",
        description="Market opening time"
    )

    market_close_time: str = Field(
        default="15:30",
        description="Market closing time"
    )

    # Position monitoring interval during market hours (in minutes)
    position_monitor_interval: int = Field(
        default=15,
        description="Position monitoring interval in minutes during market hours"
    )

    # Risk check interval (in minutes)
    risk_check_interval: int = Field(
        default=30,
        description="Risk limit check interval in minutes"
    )

    # Dry run mode
    dry_run: bool = Field(
        default=True,
        description="If True, no actual trades are executed"
    )

    # Portfolio value (for paper trading)
    portfolio_value: Optional[float] = Field(
        default=100_000_000,
        description="Portfolio value in KRW (default: 100 million)"
    )

    # Risk parameters
    max_position_size_pct: float = Field(
        default=10.0,
        description="Maximum position size as percentage of portfolio"
    )

    max_positions: int = Field(
        default=20,
        description="Maximum number of positions"
    )

    # Enable/disable specific jobs
    enable_data_collection: bool = Field(
        default=True,
        description="Enable automatic data collection"
    )

    enable_indicator_calculation: bool = Field(
        default=True,
        description="Enable automatic indicator calculation"
    )

    enable_watchlist_update: bool = Field(
        default=True,
        description="Enable automatic watchlist updates"
    )

    enable_signal_generation: bool = Field(
        default=True,
        description="Enable automatic signal generation"
    )

    enable_position_monitoring: bool = Field(
        default=True,
        description="Enable position monitoring during market hours"
    )

    enable_risk_checks: bool = Field(
        default=True,
        description="Enable periodic risk limit checks"
    )

    class Config:
        env_prefix = "ORCHESTRATOR_"
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global config instance
config = OrchestratorConfig()
