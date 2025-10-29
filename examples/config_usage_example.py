"""
Example: Configuration System Usage

This script demonstrates how to use the configuration management system
for the Korean Stock Trading System.

The configuration system uses:
- YAML files for non-sensitive parameters
- Environment variables for sensitive data (API keys, credentials)
- Pydantic for validation

Run this script to see how to load and use configurations.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.configs.loader import (
    load_trading_engine_config,
    load_risk_manager_config,
    load_stock_screener_config,
    load_indicator_calculator_config,
    load_data_collector_config,
    load_price_monitor_config,
    ConfigLoader,
    ConfigurationError
)


def example_1_basic_loading():
    """Example 1: Basic configuration loading."""
    print("=" * 80)
    print("Example 1: Basic Configuration Loading")
    print("=" * 80)

    try:
        # Load trading engine configuration
        trading_config = load_trading_engine_config()

        print("\nTrading Engine Configuration:")
        print(f"  Dry Run Mode: {trading_config.dry_run}")
        print(f"  Risk Tolerance: {trading_config.signal_generator.risk_tolerance}%")
        print(f"  Max Position Size: {trading_config.signal_generator.max_position_size_pct}%")
        print(f"  Min Conviction Score: {trading_config.signal_generator.min_conviction_score}")
        print(f"  Max Concurrent Positions: {trading_config.signal_validator.max_positions}")

        # Load risk manager configuration
        risk_config = load_risk_manager_config()

        print("\nRisk Manager Configuration:")
        print(f"  Position Sizing Method: {risk_config.position_sizing.method}")
        print(f"  Max Position Size: {risk_config.risk_parameters.max_position_size_pct}%")
        print(f"  Stop Loss: {risk_config.risk_parameters.stop_loss_pct}%")
        print(f"  Take Profit: {risk_config.risk_parameters.take_profit_pct}%")
        print(f"  Circuit Breaker Enabled: {risk_config.enable_circuit_breaker}")

    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        return False

    return True


def example_2_conviction_weights():
    """Example 2: Accessing nested configuration (conviction weights)."""
    print("\n" + "=" * 80)
    print("Example 2: Conviction Score Weights")
    print("=" * 80)

    try:
        trading_config = load_trading_engine_config()
        weights = trading_config.signal_generator.conviction_weights

        print("\nConviction Score Component Weights:")
        print(f"  Value Score:     {weights.weight_value:.2f} ({weights.weight_value * 100:.0f}%)")
        print(f"  Momentum Score:  {weights.weight_momentum:.2f} ({weights.weight_momentum * 100:.0f}%)")
        print(f"  Volume Score:    {weights.weight_volume:.2f} ({weights.weight_volume * 100:.0f}%)")
        print(f"  Quality Score:   {weights.weight_quality:.2f} ({weights.weight_quality * 100:.0f}%)")

        total = (weights.weight_value + weights.weight_momentum +
                weights.weight_volume + weights.weight_quality)
        print(f"  Total:           {total:.2f}")

    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        return False

    return True


def example_3_screening_thresholds():
    """Example 3: Stock screening thresholds."""
    print("\n" + "=" * 80)
    print("Example 3: Stock Screening Thresholds")
    print("=" * 80)

    try:
        screener_config = load_stock_screener_config()
        thresholds = screener_config.thresholds

        print("\nValuation Filters:")
        print(f"  Max P/E Ratio: {thresholds.max_per}")
        print(f"  Max P/B Ratio: {thresholds.max_pbr}")

        print("\nRisk Filters:")
        print(f"  Max Volatility: {thresholds.max_volatility_pct}%")
        print(f"  Max Debt Ratio: {thresholds.max_debt_ratio_pct}%")

        print("\nLiquidity Filters:")
        print(f"  Min Avg Volume: {thresholds.min_avg_volume:,}")
        print(f"  Min Trading Value: {thresholds.min_trading_value_krw:,.0f} KRW")

        print(f"\nMax Results: {screener_config.max_results}")

    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        return False

    return True


def example_4_technical_indicators():
    """Example 4: Technical indicator parameters."""
    print("\n" + "=" * 80)
    print("Example 4: Technical Indicator Parameters")
    print("=" * 80)

    try:
        indicator_config = load_indicator_calculator_config()
        indicators = indicator_config.indicators

        print("\nRSI Settings:")
        print(f"  Period: {indicators.rsi_period}")
        print(f"  Overbought: {indicators.rsi_overbought}")
        print(f"  Oversold: {indicators.rsi_oversold}")

        print("\nMACD Settings:")
        print(f"  Fast Period: {indicators.macd_fast_period}")
        print(f"  Slow Period: {indicators.macd_slow_period}")
        print(f"  Signal Period: {indicators.macd_signal_period}")

        print("\nMoving Averages:")
        print(f"  SMA Short: {indicators.sma_short_period}")
        print(f"  SMA Medium: {indicators.sma_medium_period}")
        print(f"  SMA Long: {indicators.sma_long_period}")

        print(f"\nCaching: {indicator_config.enable_caching}")
        print(f"Cache TTL: {indicator_config.cache_ttl_seconds} seconds")

    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        return False

    return True


def example_5_environment_override():
    """Example 5: Demonstrate environment variable override."""
    print("\n" + "=" * 80)
    print("Example 5: Environment Variable Override")
    print("=" * 80)

    print("\nDemonstrating environment variable override...")
    print("Set env var: TRADING_ENGINE_SIGNAL_GENERATOR_RISK_TOLERANCE=3.5")

    # Set environment variable
    os.environ['TRADING_ENGINE_SIGNAL_GENERATOR_RISK_TOLERANCE'] = '3.5'

    # Clear cache and reload
    from shared.configs.loader import get_config_loader
    get_config_loader.cache_clear()

    try:
        trading_config = load_trading_engine_config()
        print(f"Risk Tolerance: {trading_config.signal_generator.risk_tolerance}%")
        print("(Should be 3.5 if override worked)")

    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        return False
    finally:
        # Clean up
        del os.environ['TRADING_ENGINE_SIGNAL_GENERATOR_RISK_TOLERANCE']
        get_config_loader.cache_clear()

    return True


def example_6_commission_calculator():
    """Example 6: Commission and fee configuration."""
    print("\n" + "=" * 80)
    print("Example 6: Commission and Fee Configuration")
    print("=" * 80)

    try:
        trading_config = load_trading_engine_config()
        commission = trading_config.commission

        print("\nCommission Rates:")
        print(f"  Commission Rate: {commission.commission_rate * 100:.4f}%")
        print(f"  Transaction Tax: {commission.transaction_tax_rate * 100:.3f}%")
        print(f"  Agri/Fish Tax:   {commission.agri_fish_tax_rate * 100:.3f}%")
        print(f"  Min Commission:  {commission.min_commission:,.0f} KRW")

        # Calculate example fees for 10M KRW trade
        trade_value = 10_000_000
        total_commission = trade_value * commission.commission_rate
        total_tax = trade_value * (commission.transaction_tax_rate +
                                   commission.agri_fish_tax_rate)
        total_cost = total_commission + total_tax

        print(f"\nExample: 10,000,000 KRW Trade")
        print(f"  Commission: {total_commission:,.0f} KRW")
        print(f"  Taxes:      {total_tax:,.0f} KRW")
        print(f"  Total Cost: {total_cost:,.0f} KRW ({total_cost/trade_value*100:.3f}%)")

    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        return False

    return True


def example_7_data_collection_schedule():
    """Example 7: Data collection scheduler configuration."""
    print("\n" + "=" * 80)
    print("Example 7: Data Collection Schedule")
    print("=" * 80)

    try:
        collector_config = load_data_collector_config()
        scheduler = collector_config.scheduler

        print("\nScheduled Jobs (Cron Format):")
        print(f"  Market Data:      {scheduler.market_data_cron}")
        print(f"  Financial Data:   {scheduler.financial_data_cron}")
        print(f"  Fundamental Data: {scheduler.fundamental_data_cron}")

        print("\nRetry Policy:")
        print(f"  Max Retries: {scheduler.max_retries}")
        print(f"  Retry Delay: {scheduler.retry_delay_seconds} seconds")

        print(f"\nScheduler: {'Enabled' if collector_config.enable_scheduler else 'Disabled'}")
        print(f"Batch Size: {collector_config.batch_size}")

    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        return False

    return True


def example_8_validation_error():
    """Example 8: Demonstrate validation error handling."""
    print("\n" + "=" * 80)
    print("Example 8: Configuration Validation")
    print("=" * 80)

    print("\nAttempting to create invalid configuration...")
    print("(Setting conviction weights that don't sum to 1.0)")

    try:
        from shared.configs.models import ConvictionWeights

        # This should raise validation error
        invalid_weights = ConvictionWeights(
            weight_value=0.5,
            weight_momentum=0.5,
            weight_volume=0.5,
            weight_quality=0.5
        )

        # Try to validate
        invalid_weights.validate_weights_sum()

    except ValueError as e:
        print(f"\nValidation Error (Expected): {e}")
        print("This demonstrates the configuration validation in action!")
        return True
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return False

    print("ERROR: Should have raised validation error!")
    return False


def example_9_all_services():
    """Example 9: Load all service configurations."""
    print("\n" + "=" * 80)
    print("Example 9: Load All Service Configurations")
    print("=" * 80)

    services = [
        ("Trading Engine", load_trading_engine_config),
        ("Risk Manager", load_risk_manager_config),
        ("Stock Screener", load_stock_screener_config),
        ("Indicator Calculator", load_indicator_calculator_config),
        ("Data Collector", load_data_collector_config),
        ("Price Monitor", load_price_monitor_config),
    ]

    print("\nLoading all service configurations...")

    for service_name, loader_func in services:
        try:
            config = loader_func()
            print(f"  [{chr(10003)}] {service_name:<25} - OK")
        except ConfigurationError as e:
            print(f"  [X] {service_name:<25} - ERROR: {e}")
            return False
        except Exception as e:
            print(f"  [X] {service_name:<25} - UNEXPECTED ERROR: {e}")
            return False

    print("\nAll configurations loaded successfully!")
    return True


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print(" Configuration System Usage Examples")
    print(" Korean Stock Trading System")
    print("=" * 80)

    examples = [
        example_1_basic_loading,
        example_2_conviction_weights,
        example_3_screening_thresholds,
        example_4_technical_indicators,
        example_5_environment_override,
        example_6_commission_calculator,
        example_7_data_collection_schedule,
        example_8_validation_error,
        example_9_all_services,
    ]

    results = []
    for example_func in examples:
        try:
            result = example_func()
            results.append((example_func.__name__, result))
        except Exception as e:
            print(f"\nUnexpected error in {example_func.__name__}: {e}")
            results.append((example_func.__name__, False))

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = chr(10003) if result else "X"
        print(f"  [{symbol}] {name:<40} {status}")

    total = len(results)
    passed = sum(1 for _, result in results if result)
    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\nAll examples completed successfully!")
    else:
        print(f"\n{total - passed} example(s) failed.")


if __name__ == "__main__":
    main()
