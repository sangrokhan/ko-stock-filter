"""
Trading System Orchestrator - Main Entry Point.

Command-line interface for the trading system orchestrator.
Schedules and coordinates all trading operations with timezone awareness.
"""
import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.orchestrator.scheduler import TradingOrchestrator
from services.orchestrator.config import OrchestratorConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global orchestrator instance for signal handling
orchestrator: Optional[TradingOrchestrator] = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    if orchestrator:
        orchestrator.stop()
    sys.exit(0)


def print_banner():
    """Print startup banner."""
    print("\n" + "=" * 80)
    print(" " * 20 + "KOREAN STOCK TRADING SYSTEM")
    print(" " * 25 + "Orchestrator Service")
    print("=" * 80)
    print()


def print_config(config: OrchestratorConfig):
    """Print configuration summary."""
    print("Configuration:")
    print(f"  Timezone: {config.timezone}")
    print(f"  User ID: {config.user_id}")
    print(f"  Dry Run Mode: {config.dry_run}")
    print(f"  Portfolio Value: {config.portfolio_value:,.0f} KRW")
    print()
    print("Schedule:")
    if config.enable_data_collection:
        print(f"  Data Collection:       {config.data_collection_time} daily")
    if config.enable_indicator_calculation:
        print(f"  Indicator Calculation: {config.indicator_calculation_time} daily")
    if config.enable_watchlist_update:
        print(f"  Watchlist Update:      {config.watchlist_update_time} daily")
    if config.enable_signal_generation:
        print(f"  Signal Generation:     {config.signal_generation_time} daily")
    if config.enable_position_monitoring:
        print(f"  Position Monitoring:   Every {config.position_monitor_interval} minutes "
              f"({config.market_open_time}-{config.market_close_time})")
    if config.enable_risk_checks:
        print(f"  Risk Checks:           Every {config.risk_check_interval} minutes")
    print()


def cmd_start(args):
    """Start the orchestrator service."""
    global orchestrator

    # Create configuration
    config = OrchestratorConfig(
        user_id=args.user_id,
        dry_run=args.dry_run,
        portfolio_value=args.portfolio_value,
        timezone=args.timezone,
        enable_data_collection=not args.disable_data_collection,
        enable_indicator_calculation=not args.disable_indicator_calculation,
        enable_watchlist_update=not args.disable_watchlist_update,
        enable_signal_generation=not args.disable_signal_generation,
        enable_position_monitoring=not args.disable_position_monitoring,
        enable_risk_checks=not args.disable_risk_checks
    )

    # Print banner and config
    print_banner()
    print_config(config)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and start orchestrator
    orchestrator = TradingOrchestrator(config)

    try:
        orchestrator.start()

        # Keep the main thread alive
        logger.info("Orchestrator is running. Press Ctrl+C to stop.")
        print("\nPress Ctrl+C to stop the orchestrator\n")

        while orchestrator.running:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Error running orchestrator: {e}", exc_info=True)
    finally:
        if orchestrator:
            orchestrator.stop()
        logger.info("Orchestrator shutdown complete")


def cmd_status(args):
    """Show orchestrator status."""
    # This would typically connect to a running instance
    # For now, just show what would be scheduled
    config = OrchestratorConfig(user_id=args.user_id)
    print_banner()
    print_config(config)
    print("Note: This shows the default configuration.")
    print("To see actual running status, implement a status endpoint or file.")


def cmd_run_job(args):
    """Run a specific job immediately."""
    config = OrchestratorConfig(user_id=args.user_id)
    orchestrator = TradingOrchestrator(config)

    logger.info(f"Running job: {args.job_id}")

    try:
        orchestrator.run_job_now(args.job_id)
        logger.info(f"Job '{args.job_id}' completed")
    except Exception as e:
        logger.error(f"Error running job: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point for orchestrator CLI."""
    parser = argparse.ArgumentParser(
        description='Trading System Orchestrator - Coordinate all trading operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start orchestrator with default settings
  python -m services.orchestrator.main start

  # Start with custom user and portfolio value
  python -m services.orchestrator.main start --user-id trader1 --portfolio-value 50000000

  # Start in live trading mode (not dry-run)
  python -m services.orchestrator.main start --no-dry-run

  # Disable specific jobs
  python -m services.orchestrator.main start --disable-signal-generation --disable-position-monitoring

  # Show status
  python -m services.orchestrator.main status

  # Run a specific job immediately
  python -m services.orchestrator.main run-job data_collection
        """
    )

    # Global options
    parser.add_argument(
        '--user-id',
        type=str,
        default='default_user',
        help='User ID for trading operations (default: default_user)'
    )

    parser.add_argument(
        '--timezone',
        type=str,
        default='Asia/Seoul',
        help='Timezone for scheduling (default: Asia/Seoul)'
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Start command
    start_parser = subparsers.add_parser('start', help='Start the orchestrator service')
    start_parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Run in dry-run mode (no actual trades)'
    )
    start_parser.add_argument(
        '--no-dry-run',
        dest='dry_run',
        action='store_false',
        help='Disable dry-run mode (CAUTION: executes real trades!)'
    )
    start_parser.add_argument(
        '--portfolio-value',
        type=float,
        default=100_000_000,
        help='Portfolio value in KRW (default: 100,000,000)'
    )
    start_parser.add_argument(
        '--disable-data-collection',
        action='store_true',
        help='Disable automatic data collection'
    )
    start_parser.add_argument(
        '--disable-indicator-calculation',
        action='store_true',
        help='Disable automatic indicator calculation'
    )
    start_parser.add_argument(
        '--disable-watchlist-update',
        action='store_true',
        help='Disable automatic watchlist updates'
    )
    start_parser.add_argument(
        '--disable-signal-generation',
        action='store_true',
        help='Disable automatic signal generation'
    )
    start_parser.add_argument(
        '--disable-position-monitoring',
        action='store_true',
        help='Disable position monitoring'
    )
    start_parser.add_argument(
        '--disable-risk-checks',
        action='store_true',
        help='Disable risk limit checks'
    )
    start_parser.set_defaults(func=cmd_start)

    # Status command
    status_parser = subparsers.add_parser('status', help='Show orchestrator status')
    status_parser.set_defaults(func=cmd_status)

    # Run job command
    run_parser = subparsers.add_parser('run-job', help='Run a specific job immediately')
    run_parser.add_argument(
        'job_id',
        type=str,
        choices=[
            'data_collection',
            'indicator_calculation',
            'watchlist_update',
            'signal_generation',
            'position_monitoring',
            'risk_checks'
        ],
        help='Job ID to run'
    )
    run_parser.set_defaults(func=cmd_run_job)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    try:
        args.func(args)
    except Exception as e:
        logger.error(f"Error executing command: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
