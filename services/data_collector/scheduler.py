"""
Scheduler for continuous data collection using APScheduler.
Schedules periodic tasks for collecting stock codes, prices, and fundamental data.
"""
import sys
from pathlib import Path
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import pytz

# Add shared directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.data_collector.stock_code_collector import StockCodeCollector
from services.data_collector.price_collector import PriceCollector
from services.data_collector.fundamental_collector import FundamentalCollector

logger = logging.getLogger(__name__)


class DataCollectionScheduler:
    """
    Manages scheduled data collection tasks.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler(
            timezone=pytz.timezone('Asia/Seoul'),
            job_defaults={
                'coalesce': True,  # Combine missed runs into one
                'max_instances': 1,  # Only one instance of each job at a time
                'misfire_grace_time': 300  # Allow 5 minutes grace for missed jobs
            }
        )

        # Initialize collectors
        self.stock_code_collector = StockCodeCollector()
        self.price_collector = PriceCollector()
        self.fundamental_collector = FundamentalCollector()

        # Add event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )

        logger.info("DataCollectionScheduler initialized")

    def _job_executed_listener(self, event):
        """Log successful job execution."""
        logger.info(f"Job {event.job_id} executed successfully")

    def _job_error_listener(self, event):
        """Log job execution errors."""
        logger.error(f"Job {event.job_id} failed with exception: {event.exception}")

    def collect_stock_codes_job(self):
        """
        Job to collect all stock codes.
        Run weekly to update the stock list.
        """
        try:
            logger.info("Starting scheduled stock code collection")
            count = self.stock_code_collector.collect_all_stock_codes()
            logger.info(f"Scheduled stock code collection completed: {count} stocks processed")
        except Exception as e:
            logger.error(f"Error in scheduled stock code collection: {e}")
            raise

    def collect_daily_prices_job(self):
        """
        Job to collect daily price data for all stocks.
        Run daily after market close.
        """
        try:
            logger.info("Starting scheduled daily price collection")
            stats = self.price_collector.collect_prices_for_all_stocks()
            logger.info(
                f"Scheduled price collection completed: "
                f"{stats['successful']}/{stats['total_stocks']} stocks, "
                f"{stats['total_records']} records"
            )
        except Exception as e:
            logger.error(f"Error in scheduled price collection: {e}")
            raise

    def collect_fundamentals_job(self):
        """
        Job to collect fundamental data for all stocks.
        Run daily after market close.
        """
        try:
            logger.info("Starting scheduled fundamental data collection")
            stats = self.fundamental_collector.collect_fundamentals_for_all_stocks()
            logger.info(
                f"Scheduled fundamental collection completed: "
                f"{stats['successful']}/{stats['total_stocks']} stocks"
            )
        except Exception as e:
            logger.error(f"Error in scheduled fundamental collection: {e}")
            raise

    def update_stock_details_job(self):
        """
        Job to update stock details (market cap, shares).
        Run weekly to keep data fresh.
        """
        try:
            logger.info("Starting scheduled stock details update")
            count = self.stock_code_collector.update_stock_details()
            logger.info(f"Scheduled stock details update completed: {count} stocks updated")
        except Exception as e:
            logger.error(f"Error in scheduled stock details update: {e}")
            raise

    def setup_schedules(self):
        """
        Set up all scheduled jobs.

        Schedule:
        - Stock codes: Weekly on Sunday at 1:00 AM
        - Daily prices: Monday-Friday at 4:00 PM (after market close)
        - Fundamentals: Monday-Friday at 4:30 PM
        - Stock details: Weekly on Sunday at 2:00 AM
        """
        # Stock code collection - Weekly on Sunday at 1:00 AM KST
        self.scheduler.add_job(
            self.collect_stock_codes_job,
            trigger=CronTrigger(
                day_of_week='sun',
                hour=1,
                minute=0,
                timezone='Asia/Seoul'
            ),
            id='collect_stock_codes',
            name='Collect Stock Codes',
            replace_existing=True
        )
        logger.info("Scheduled: Stock code collection (Sunday 1:00 AM)")

        # Daily price collection - Monday-Friday at 4:00 PM KST (after market close)
        # Korean stock market closes at 3:30 PM, so 4:00 PM should have all data
        self.scheduler.add_job(
            self.collect_daily_prices_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=16,
                minute=0,
                timezone='Asia/Seoul'
            ),
            id='collect_daily_prices',
            name='Collect Daily Prices',
            replace_existing=True
        )
        logger.info("Scheduled: Daily price collection (Mon-Fri 4:00 PM)")

        # Fundamental data collection - Monday-Friday at 4:30 PM KST
        self.scheduler.add_job(
            self.collect_fundamentals_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=16,
                minute=30,
                timezone='Asia/Seoul'
            ),
            id='collect_fundamentals',
            name='Collect Fundamental Data',
            replace_existing=True
        )
        logger.info("Scheduled: Fundamental data collection (Mon-Fri 4:30 PM)")

        # Stock details update - Weekly on Sunday at 2:00 AM KST
        self.scheduler.add_job(
            self.update_stock_details_job,
            trigger=CronTrigger(
                day_of_week='sun',
                hour=2,
                minute=0,
                timezone='Asia/Seoul'
            ),
            id='update_stock_details',
            name='Update Stock Details',
            replace_existing=True
        )
        logger.info("Scheduled: Stock details update (Sunday 2:00 AM)")

        logger.info("All scheduled jobs configured")

    def start(self):
        """Start the scheduler."""
        try:
            self.setup_schedules()
            self.scheduler.start()
            logger.info("Scheduler started successfully")
            logger.info(f"Next job run times:")
            for job in self.scheduler.get_jobs():
                logger.info(f"  - {job.name}: {job.next_run_time}")
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            raise

    def stop(self):
        """Stop the scheduler."""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            raise

    def run_job_now(self, job_id: str):
        """
        Manually trigger a job to run immediately.

        Args:
            job_id: ID of the job to run
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                logger.info(f"Manually triggering job: {job.name}")
                job.modify(next_run_time=datetime.now())
            else:
                logger.error(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Error running job {job_id}: {e}")
            raise

    def get_job_status(self):
        """
        Get status of all scheduled jobs.

        Returns:
            List of job information dictionaries
        """
        jobs_info = []

        for job in self.scheduler.get_jobs():
            jobs_info.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })

        return jobs_info

    def is_running(self) -> bool:
        """
        Check if scheduler is running.

        Returns:
            True if running, False otherwise
        """
        return self.scheduler.running
