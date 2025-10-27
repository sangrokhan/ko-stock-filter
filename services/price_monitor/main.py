"""
Main entry point for Price Monitor Service.

Monitors stock prices in real-time during market hours,
detects significant changes, and publishes events.
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

from .config import get_settings
from .market_calendar import KoreanMarketCalendar
from .event_publisher import PriceEventPublisher
from .price_monitor import PriceMonitor


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class PriceMonitorService:
    """Price monitoring service orchestrator."""

    def __init__(self):
        """Initialize the price monitor service."""
        self.settings = get_settings()
        self.running = False
        self.market_calendar = KoreanMarketCalendar()
        self.event_publisher = None
        self.price_monitor = None

        # Configure logging level
        log_level = getattr(logging, self.settings.log_level.upper(), logging.INFO)
        logging.getLogger().setLevel(log_level)

        logger.info("Price Monitor Service initialized")

    def setup(self):
        """Set up service components."""
        try:
            # Initialize event publisher
            self.event_publisher = PriceEventPublisher(
                redis_host=self.settings.redis_host,
                redis_port=self.settings.redis_port,
                redis_db=self.settings.redis_db,
                redis_password=self.settings.redis_password
            )

            # Initialize price monitor
            self.price_monitor = PriceMonitor(
                event_publisher=self.event_publisher,
                market_calendar=self.market_calendar,
                significant_change_threshold=self.settings.significant_change_threshold
            )

            logger.info("Service components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to setup service: {e}", exc_info=True)
            raise

    async def wait_for_market_open(self):
        """Wait until market opens."""
        if self.market_calendar.is_market_open():
            logger.info("Market is currently open")
            return

        seconds = self.market_calendar.seconds_until_market_open()
        next_open = self.market_calendar.get_next_market_open()

        logger.info(
            f"Market is closed. Next opening at {next_open.strftime('%Y-%m-%d %H:%M:%S KST')} "
            f"({seconds} seconds)"
        )

        # Sleep in chunks to allow for graceful shutdown
        while seconds > 0 and self.running:
            sleep_time = min(60, seconds)  # Sleep for up to 1 minute at a time
            await asyncio.sleep(sleep_time)
            seconds -= sleep_time

    async def monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Starting monitoring loop")

        while self.running:
            try:
                # Wait for market to open if it's closed
                if not self.market_calendar.is_market_open():
                    await self.wait_for_market_open()
                    if not self.running:
                        break
                    continue

                # Monitor all stocks
                logger.info("Running price monitoring cycle...")
                stats = self.price_monitor.monitor_all_stocks()

                logger.info(
                    f"Monitoring cycle completed - "
                    f"Total: {stats['total']}, "
                    f"Success: {stats['success']}, "
                    f"Failed: {stats['failed']}, "
                    f"Skipped: {stats['skipped']}"
                )

                # Check if market is still open before sleeping
                if not self.market_calendar.is_market_open():
                    logger.info("Market closed during monitoring cycle")
                    continue

                # Sleep for poll interval
                logger.info(f"Sleeping for {self.settings.poll_interval_seconds} seconds...")
                await asyncio.sleep(self.settings.poll_interval_seconds)

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                # Sleep a bit before retrying
                await asyncio.sleep(self.settings.retry_delay_seconds)

    def start(self):
        """Start the price monitor service."""
        self.running = True
        logger.info("Price Monitor Service starting...")

        # Setup components
        self.setup()

        # Start monitoring loop
        try:
            asyncio.run(self.monitoring_loop())
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()

    def stop(self):
        """Stop the price monitor service."""
        logger.info("Stopping Price Monitor Service...")
        self.running = False

        # Cleanup
        if self.event_publisher:
            try:
                self.event_publisher.close()
            except Exception as e:
                logger.error(f"Error closing event publisher: {e}")

        logger.info("Price Monitor Service stopped")

    def handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.running = False


def main():
    """Main entry point."""
    service = PriceMonitorService()

    # Register signal handlers
    signal.signal(signal.SIGINT, service.handle_signal)
    signal.signal(signal.SIGTERM, service.handle_signal)

    # Start service
    service.start()


if __name__ == "__main__":
    main()
