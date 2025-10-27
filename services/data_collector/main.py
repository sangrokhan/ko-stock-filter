"""
Main entry point for Data Collector Service.
Collects stock data from KRX (Korea Exchange) and other sources.

Features:
- Fetches KOSPI, KOSDAQ, and KONEX stock codes
- Collects daily OHLCV price data
- Collects fundamental data (PER, PBR, market cap, etc.)
- Rate limiting and error handling with retry mechanisms
- Scheduled continuous operation with APScheduler
"""
import sys
from pathlib import Path
import logging
import signal
import time
from typing import Optional, Dict
from datetime import datetime, timedelta
from pythonjsonlogger import jsonlogger

# Add shared directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.data_collector.stock_code_collector import StockCodeCollector
from services.data_collector.price_collector import PriceCollector
from services.data_collector.fundamental_collector import FundamentalCollector
from services.data_collector.scheduler import DataCollectionScheduler

# Configure logging
logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO", json_format: bool = False):
    """
    Set up logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON format for logs
    """
    log_handler = logging.StreamHandler()

    if json_format:
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    log_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(log_handler)

    logger.info(f"Logging configured with level: {log_level}")


class DataCollectorService:
    """
    Service for collecting Korean stock market data.

    This service orchestrates multiple collectors and provides both
    scheduled and on-demand data collection capabilities.
    """

    def __init__(self, enable_scheduler: bool = True):
        """
        Initialize the data collector service.

        Args:
            enable_scheduler: Whether to enable scheduled data collection
        """
        self.running = False
        self.enable_scheduler = enable_scheduler

        # Initialize collectors
        self.stock_code_collector = StockCodeCollector()
        self.price_collector = PriceCollector()
        self.fundamental_collector = FundamentalCollector()

        # Initialize scheduler if enabled
        self.scheduler = None
        if enable_scheduler:
            self.scheduler = DataCollectionScheduler()

        logger.info("Data Collector Service initialized")

    def start(self):
        """Start the data collection service."""
        self.running = True

        if self.scheduler and self.enable_scheduler:
            logger.info("Starting scheduler for continuous data collection")
            self.scheduler.start()

        logger.info("Data Collector Service started")

    def stop(self):
        """Stop the data collection service."""
        self.running = False

        if self.scheduler and self.scheduler.is_running():
            logger.info("Stopping scheduler")
            self.scheduler.stop()

        logger.info("Data Collector Service stopped")

    def collect_all_stock_codes(self) -> int:
        """
        Collect all stock codes from KOSPI, KOSDAQ, and KONEX.

        Returns:
            Number of stocks collected
        """
        logger.info("Collecting all stock codes")
        return self.stock_code_collector.collect_all_stock_codes()

    def collect_prices_for_stock(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        Collect price data for a specific stock.

        Args:
            ticker: Stock ticker code
            start_date: Start date in YYYY-MM-DD format (default: 30 days ago)
            end_date: End date in YYYY-MM-DD format (default: today)

        Returns:
            Number of price records collected
        """
        logger.info(f"Collecting prices for stock {ticker}")
        return self.price_collector.collect_prices_for_stock(
            ticker, start_date, end_date
        )

    def collect_prices_for_all_stocks(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Collect price data for all active stocks.

        Args:
            start_date: Start date in YYYY-MM-DD format (default: yesterday)
            end_date: End date in YYYY-MM-DD format (default: today)

        Returns:
            Dictionary with collection statistics
        """
        logger.info("Collecting prices for all stocks")
        return self.price_collector.collect_prices_for_all_stocks(
            start_date, end_date
        )

    def collect_fundamentals_for_stock(
        self,
        ticker: str,
        date: Optional[str] = None
    ) -> bool:
        """
        Collect fundamental data for a specific stock.

        Args:
            ticker: Stock ticker code
            date: Date in YYYYMMDD format (default: today)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Collecting fundamentals for stock {ticker}")
        return self.fundamental_collector.collect_fundamentals_for_stock(
            ticker, date
        )

    def collect_fundamentals_for_all_stocks(
        self,
        date: Optional[str] = None
    ) -> Dict:
        """
        Collect fundamental data for all active stocks.

        Args:
            date: Date in YYYYMMDD format (default: today)

        Returns:
            Dictionary with collection statistics
        """
        logger.info("Collecting fundamentals for all stocks")
        return self.fundamental_collector.collect_fundamentals_for_all_stocks(date)

    def run_initial_collection(self):
        """
        Run initial data collection for new setup.
        This will:
        1. Collect all stock codes
        2. Collect last 30 days of price data
        3. Collect current fundamental data
        """
        logger.info("Starting initial data collection")

        try:
            # Step 1: Collect stock codes
            logger.info("Step 1/3: Collecting stock codes")
            stock_count = self.collect_all_stock_codes()
            logger.info(f"Collected {stock_count} stocks")

            # Step 2: Collect historical price data (last 30 days)
            logger.info("Step 2/3: Collecting historical price data (last 30 days)")
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            price_stats = self.collect_prices_for_all_stocks(start_date, end_date)
            logger.info(
                f"Collected prices: {price_stats['successful']}/{price_stats['total_stocks']} stocks, "
                f"{price_stats['total_records']} total records"
            )

            # Step 3: Collect fundamental data
            logger.info("Step 3/3: Collecting fundamental data")
            fund_stats = self.collect_fundamentals_for_all_stocks()
            logger.info(
                f"Collected fundamentals: {fund_stats['successful']}/{fund_stats['total_stocks']} stocks"
            )

            logger.info("Initial data collection completed successfully")

        except Exception as e:
            logger.error(f"Error during initial data collection: {e}")
            raise

    def get_scheduler_status(self) -> Dict:
        """
        Get status of scheduled jobs.

        Returns:
            Dictionary with scheduler status
        """
        if not self.scheduler:
            return {"enabled": False, "running": False, "jobs": []}

        return {
            "enabled": True,
            "running": self.scheduler.is_running(),
            "jobs": self.scheduler.get_job_status()
        }

    def run_scheduled_job(self, job_id: str):
        """
        Manually trigger a scheduled job.

        Args:
            job_id: ID of the job to run
        """
        if not self.scheduler:
            logger.error("Scheduler not enabled")
            return

        self.scheduler.run_job_now(job_id)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    if 'service' in globals():
        service.stop()
    sys.exit(0)


def main():
    """Main entry point for the data collector service."""
    # Set up logging
    setup_logging(log_level="INFO", json_format=False)

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and start service
    global service
    service = DataCollectorService(enable_scheduler=True)

    try:
        logger.info("=" * 60)
        logger.info("Korean Stock Data Collector Service")
        logger.info("=" * 60)

        # Start the service
        service.start()

        # Check if this is the first run (no data in DB)
        # You might want to run initial collection
        # Uncomment the following line if you want to run initial collection on startup
        # service.run_initial_collection()

        # Keep the service running
        logger.info("Service is running. Press Ctrl+C to stop.")
        logger.info("\nScheduled jobs:")
        for job_info in service.get_scheduler_status()['jobs']:
            logger.info(f"  - {job_info['name']}: Next run at {job_info['next_run_time']}")

        # Keep the main thread alive
        while service.running:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Error in main service: {e}", exc_info=True)
    finally:
        service.stop()
        logger.info("Service shutdown complete")


if __name__ == "__main__":
    main()
