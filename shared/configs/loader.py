"""
Configuration loader that combines YAML files with environment variables.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar
from functools import lru_cache
from pydantic import BaseModel, ValidationError

T = TypeVar('T', bound=BaseModel)


class ConfigurationError(Exception):
    """Configuration loading or validation error."""
    pass


class ConfigLoader:
    """
    Load and validate configuration from YAML files and environment variables.

    Environment variables take precedence over YAML values.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration loader.

        Args:
            config_dir: Directory containing YAML config files.
                       Defaults to /config relative to project root.
        """
        if config_dir is None:
            # Default to /config directory at project root
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config"

        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            raise ConfigurationError(f"Config directory not found: {self.config_dir}")

    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        Load YAML configuration file.

        Args:
            filename: Name of YAML file (e.g., 'trading_engine.yaml')

        Returns:
            Dictionary with configuration values

        Raises:
            ConfigurationError: If file not found or invalid YAML
        """
        filepath = self.config_dir / filename

        if not filepath.exists():
            raise ConfigurationError(f"Config file not found: {filepath}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {filepath}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error reading {filepath}: {e}")

    def merge_with_env(
        self,
        config: Dict[str, Any],
        env_prefix: str = "",
        current_path: str = ""
    ) -> Dict[str, Any]:
        """
        Merge configuration with environment variables.

        Environment variables override YAML values.
        Uses nested path for env var names (e.g., RISK_PARAMETERS_MAX_POSITION_SIZE_PCT)

        Args:
            config: Configuration dictionary from YAML
            env_prefix: Prefix for environment variables
            current_path: Current path in nested config (internal use)

        Returns:
            Merged configuration dictionary
        """
        result = config.copy()

        for key, value in config.items():
            # Build environment variable name
            env_path = f"{current_path}_{key}".upper() if current_path else key.upper()
            full_env_name = f"{env_prefix}{env_path}".replace(".", "_")

            # Check if environment variable exists
            env_value = os.getenv(full_env_name)

            if env_value is not None:
                # Parse environment variable value
                result[key] = self._parse_env_value(env_value)
            elif isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self.merge_with_env(value, env_prefix, env_path)

        return result

    def _parse_env_value(self, value: str) -> Any:
        """
        Parse environment variable value to appropriate type.

        Args:
            value: String value from environment variable

        Returns:
            Parsed value (bool, int, float, or string)
        """
        # Boolean
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        if value.lower() in ('false', 'no', '0', 'off'):
            return False

        # Integer
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return int(value)

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # String (default)
        return value

    def load_and_validate(
        self,
        filename: str,
        model_class: Type[T],
        env_prefix: str = ""
    ) -> T:
        """
        Load YAML config, merge with environment variables, and validate.

        Args:
            filename: YAML config filename
            model_class: Pydantic model class for validation
            env_prefix: Prefix for environment variables (e.g., "TRADING_ENGINE_")

        Returns:
            Validated configuration model instance

        Raises:
            ConfigurationError: If validation fails
        """
        try:
            # Load YAML config
            yaml_config = self.load_yaml(filename)

            # Merge with environment variables
            merged_config = self.merge_with_env(yaml_config, env_prefix)

            # Validate with Pydantic model
            validated_config = model_class(**merged_config)

            # Run any additional validation methods
            if hasattr(validated_config, 'validate_weights_sum'):
                validated_config.validate_weights_sum()

            return validated_config

        except ValidationError as e:
            raise ConfigurationError(
                f"Configuration validation failed for {filename}:\n{e}"
            )
        except Exception as e:
            raise ConfigurationError(
                f"Error loading configuration from {filename}: {e}"
            )

    def load_config_dict(
        self,
        filename: str,
        env_prefix: str = ""
    ) -> Dict[str, Any]:
        """
        Load configuration as dictionary without validation.

        Args:
            filename: YAML config filename
            env_prefix: Prefix for environment variables

        Returns:
            Merged configuration dictionary
        """
        yaml_config = self.load_yaml(filename)
        return self.merge_with_env(yaml_config, env_prefix)


# =============================================================================
# Cached loader instances
# =============================================================================

@lru_cache()
def get_config_loader(config_dir: Optional[str] = None) -> ConfigLoader:
    """
    Get cached configuration loader instance.

    Args:
        config_dir: Optional custom config directory path

    Returns:
        ConfigLoader instance
    """
    path = Path(config_dir) if config_dir else None
    return ConfigLoader(config_dir=path)


# =============================================================================
# Convenience functions for loading service configs
# =============================================================================

def load_trading_engine_config():
    """Load and validate trading engine configuration."""
    from .models import TradingEngineConfig

    loader = get_config_loader()
    return loader.load_and_validate(
        'trading_engine.yaml',
        TradingEngineConfig,
        env_prefix='TRADING_ENGINE_'
    )


def load_risk_manager_config():
    """Load and validate risk manager configuration."""
    from .models import RiskManagerConfig

    loader = get_config_loader()
    return loader.load_and_validate(
        'risk_manager.yaml',
        RiskManagerConfig,
        env_prefix='RISK_MANAGER_'
    )


def load_stock_screener_config():
    """Load and validate stock screener configuration."""
    from .models import StockScreenerConfig

    loader = get_config_loader()
    return loader.load_and_validate(
        'stock_screener.yaml',
        StockScreenerConfig,
        env_prefix='STOCK_SCREENER_'
    )


def load_indicator_calculator_config():
    """Load and validate indicator calculator configuration."""
    from .models import IndicatorCalculatorConfig

    loader = get_config_loader()
    return loader.load_and_validate(
        'indicator_calculator.yaml',
        IndicatorCalculatorConfig,
        env_prefix='INDICATOR_CALCULATOR_'
    )


def load_data_collector_config():
    """Load and validate data collector configuration."""
    from .models import DataCollectorConfig

    loader = get_config_loader()
    return loader.load_and_validate(
        'data_collector.yaml',
        DataCollectorConfig,
        env_prefix='DATA_COLLECTOR_'
    )


def load_price_monitor_config():
    """Load and validate price monitor configuration."""
    from .models import PriceMonitorConfig

    loader = get_config_loader()
    return loader.load_and_validate(
        'price_monitor.yaml',
        PriceMonitorConfig,
        env_prefix='PRICE_MONITOR_'
    )
