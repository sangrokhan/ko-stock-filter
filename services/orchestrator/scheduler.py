"""
Trading System Orchestrator - Main Scheduler.

Coordinates all trading system operations with timezone-aware scheduling.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, time
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from pytz import timezone as pytz_timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database.connection import SessionLocal
from services.orchestrator.config import OrchestratorConfig

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    """
    Main orchestrator for the trading system.

    Schedules and coordinates all trading operations:
    - Data collection (16:00 daily)
    - Indicator calculation (17:00 daily)
    - Watchlist updates (18:00 daily)
    - Signal generation (08:45 daily)
    - Position monitoring (09:00-15:30, every 15 minutes)
    - Risk checks (every 30 minutes)
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """
        Initialize the trading orchestrator.

        Args:
            config: Orchestrator configuration (defaults to global config)
        """
        self.config = config or OrchestratorConfig()
        self.timezone = pytz_timezone(self.config.timezone)
        self.running = False

        # Configure scheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=10)
        }
        job_defaults = {
            'coalesce': True,  # Combine multiple pending executions into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 300  # 5 minutes grace time for missed jobs
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.timezone
        )

        logger.info(f"Trading Orchestrator initialized (timezone: {self.config.timezone})")

    def start(self):
        """Start the orchestrator and all scheduled jobs."""
        if self.running:
            logger.warning("Orchestrator is already running")
            return

        logger.info("=" * 80)
        logger.info("Starting Trading System Orchestrator")
        logger.info("=" * 80)

        # Schedule all jobs
        self._schedule_jobs()

        # Start the scheduler
        self.scheduler.start()
        self.running = True

        logger.info("Orchestrator started successfully")
        logger.info(f"Scheduled jobs: {len(self.scheduler.get_jobs())}")
        self._print_schedule()

    def stop(self):
        """Stop the orchestrator and all scheduled jobs."""
        if not self.running:
            logger.warning("Orchestrator is not running")
            return

        logger.info("Stopping Trading System Orchestrator...")
        self.scheduler.shutdown(wait=True)
        self.running = False
        logger.info("Orchestrator stopped")

    def _schedule_jobs(self):
        """Schedule all trading system jobs."""
        # 1. Data Collection (16:00 daily) - after market close
        if self.config.enable_data_collection:
            hour, minute = map(int, self.config.data_collection_time.split(':'))
            self.scheduler.add_job(
                func=self._run_data_collection,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=self.timezone),
                id='data_collection',
                name='Daily Data Collection',
                replace_existing=True
            )
            logger.info(f"Scheduled: Data Collection at {self.config.data_collection_time}")

        # 2. Indicator Calculation (17:00 daily)
        if self.config.enable_indicator_calculation:
            hour, minute = map(int, self.config.indicator_calculation_time.split(':'))
            self.scheduler.add_job(
                func=self._run_indicator_calculation,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=self.timezone),
                id='indicator_calculation',
                name='Daily Indicator Calculation',
                replace_existing=True
            )
            logger.info(f"Scheduled: Indicator Calculation at {self.config.indicator_calculation_time}")

        # 3. Watchlist Update (18:00 daily)
        if self.config.enable_watchlist_update:
            hour, minute = map(int, self.config.watchlist_update_time.split(':'))
            self.scheduler.add_job(
                func=self._run_watchlist_update,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=self.timezone),
                id='watchlist_update',
                name='Daily Watchlist Update',
                replace_existing=True
            )
            logger.info(f"Scheduled: Watchlist Update at {self.config.watchlist_update_time}")

        # 4. Signal Generation (08:45 daily) - before market open
        if self.config.enable_signal_generation:
            hour, minute = map(int, self.config.signal_generation_time.split(':'))
            self.scheduler.add_job(
                func=self._run_signal_generation,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=self.timezone),
                id='signal_generation',
                name='Daily Signal Generation',
                replace_existing=True
            )
            logger.info(f"Scheduled: Signal Generation at {self.config.signal_generation_time}")

        # 5. Position Monitoring (during market hours: 09:00-15:30, every 15 minutes)
        if self.config.enable_position_monitoring:
            market_open_hour, market_open_min = map(int, self.config.market_open_time.split(':'))
            market_close_hour, market_close_min = map(int, self.config.market_close_time.split(':'))

            # Schedule interval job that only runs during market hours
            self.scheduler.add_job(
                func=self._run_position_monitoring,
                trigger=IntervalTrigger(
                    minutes=self.config.position_monitor_interval,
                    timezone=self.timezone,
                    start_date=datetime.now(self.timezone).replace(
                        hour=market_open_hour,
                        minute=market_open_min,
                        second=0,
                        microsecond=0
                    )
                ),
                id='position_monitoring',
                name='Position Monitoring',
                replace_existing=True
            )
            logger.info(
                f"Scheduled: Position Monitoring every {self.config.position_monitor_interval} minutes "
                f"during market hours ({self.config.market_open_time}-{self.config.market_close_time})"
            )

        # 6. Risk Limit Checks (every 30 minutes)
        if self.config.enable_risk_checks:
            self.scheduler.add_job(
                func=self._run_risk_checks,
                trigger=IntervalTrigger(
                    minutes=self.config.risk_check_interval,
                    timezone=self.timezone
                ),
                id='risk_checks',
                name='Risk Limit Checks',
                replace_existing=True
            )
            logger.info(f"Scheduled: Risk Checks every {self.config.risk_check_interval} minutes")

    def _is_market_hours(self) -> bool:
        """
        Check if current time is within market hours.

        Returns:
            True if within market hours, False otherwise
        """
        now = datetime.now(self.timezone)
        current_time = now.time()

        market_open = time(*map(int, self.config.market_open_time.split(':')))
        market_close = time(*map(int, self.config.market_close_time.split(':')))

        # Check if it's a weekday (Monday=0, Sunday=6)
        is_weekday = now.weekday() < 5

        return is_weekday and market_open <= current_time <= market_close

    # Job execution methods

    def _run_data_collection(self):
        """Execute daily data collection."""
        logger.info("=" * 80)
        logger.info("STARTING: Data Collection Job")
        logger.info("=" * 80)

        try:
            from services.data_collector.main import DataCollectorService

            service = DataCollectorService(enable_scheduler=False)

            # Collect stock codes
            logger.info("Step 1/3: Collecting stock codes...")
            stock_count = service.collect_all_stock_codes()
            logger.info(f"Collected {stock_count} stock codes")

            # Collect price data for today
            logger.info("Step 2/3: Collecting price data...")
            price_stats = service.collect_prices_for_all_stocks()
            logger.info(
                f"Collected prices: {price_stats['successful']}/{price_stats['total_stocks']} stocks, "
                f"{price_stats['total_records']} records"
            )

            # Collect fundamental data
            logger.info("Step 3/3: Collecting fundamental data...")
            fund_stats = service.collect_fundamentals_for_all_stocks()
            logger.info(
                f"Collected fundamentals: {fund_stats['successful']}/{fund_stats['total_stocks']} stocks"
            )

            logger.info("Data Collection Job completed successfully")

        except Exception as e:
            logger.error(f"Error in data collection job: {e}", exc_info=True)

        logger.info("=" * 80)

    def _run_indicator_calculation(self):
        """Execute daily indicator calculation."""
        logger.info("=" * 80)
        logger.info("STARTING: Indicator Calculation Job")
        logger.info("=" * 80)

        try:
            from services.indicator_calculator.run_technical_calculation import main as run_technical
            from services.indicator_calculator.run_financial_calculation import main as run_financial

            # Calculate technical indicators
            logger.info("Step 1/2: Calculating technical indicators...")
            run_technical()
            logger.info("Technical indicators calculated")

            # Calculate financial indicators
            logger.info("Step 2/2: Calculating financial indicators...")
            run_financial()
            logger.info("Financial indicators calculated")

            logger.info("Indicator Calculation Job completed successfully")

        except Exception as e:
            logger.error(f"Error in indicator calculation job: {e}", exc_info=True)

        logger.info("=" * 80)

    def _run_watchlist_update(self):
        """Execute daily watchlist update."""
        logger.info("=" * 80)
        logger.info("STARTING: Watchlist Update Job")
        logger.info("=" * 80)

        try:
            from services.watchlist_manager.watchlist_manager import WatchlistManager

            db = SessionLocal()
            try:
                manager = WatchlistManager(db, user_id=self.config.user_id)

                # Update watchlist with latest scores and prices
                logger.info("Updating watchlist...")
                stats = manager.update_watchlist_daily()

                logger.info(f"Watchlist updated:")
                logger.info(f"  Total entries: {stats['total_entries']}")
                logger.info(f"  Updated: {stats['updated']}")
                logger.info(f"  Failed: {stats['failed']}")
                logger.info(f"  Removed: {stats['removed']}")

                if stats['errors']:
                    logger.warning(f"Encountered {len(stats['errors'])} errors during update")

                logger.info("Watchlist Update Job completed successfully")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in watchlist update job: {e}", exc_info=True)

        logger.info("=" * 80)

    def _run_signal_generation(self):
        """Execute daily signal generation."""
        logger.info("=" * 80)
        logger.info("STARTING: Signal Generation Job")
        logger.info("=" * 80)

        try:
            from services.trading_engine.main import TradingEngineService

            db = SessionLocal()
            try:
                engine = TradingEngineService(
                    user_id=self.config.user_id,
                    db=db,
                    dry_run=self.config.dry_run,
                    portfolio_value=self.config.portfolio_value
                )

                # Run complete trading cycle
                logger.info("Running trading cycle...")
                results = engine.run_trading_cycle()

                logger.info("Trading cycle completed:")
                logger.info(f"  Exit signals: {len(results['exit_signals'])}")
                logger.info(f"  Entry signals: {len(results['entry_signals'])}")
                logger.info(f"  Executed exits: {len(results['executed_exits'])}")
                logger.info(f"  Executed entries: {len(results['executed_entries'])}")

                if results['errors']:
                    logger.warning(f"Encountered {len(results['errors'])} errors during trading cycle")

                logger.info("Signal Generation Job completed successfully")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in signal generation job: {e}", exc_info=True)

        logger.info("=" * 80)

    def _run_position_monitoring(self):
        """Execute position monitoring (only during market hours)."""
        # Check if within market hours
        if not self._is_market_hours():
            logger.debug("Skipping position monitoring - outside market hours")
            return

        logger.info("-" * 80)
        logger.info("STARTING: Position Monitoring")
        logger.info("-" * 80)

        try:
            from services.trading_engine.main import TradingEngineService

            db = SessionLocal()
            try:
                engine = TradingEngineService(
                    user_id=self.config.user_id,
                    db=db,
                    dry_run=self.config.dry_run,
                    portfolio_value=self.config.portfolio_value
                )

                # Monitor positions
                results = engine.monitor_positions()

                logger.info(f"Monitored {len(results['positions'])} positions")

                if results['alerts']:
                    logger.warning(f"ALERTS: {len(results['alerts'])} position alerts!")
                    for alert in results['alerts']:
                        logger.warning(f"  - {alert}")
                else:
                    logger.info("No position alerts")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in position monitoring: {e}", exc_info=True)

        logger.info("-" * 80)

    def _run_risk_checks(self):
        """Execute periodic risk limit checks."""
        logger.info("-" * 80)
        logger.info("STARTING: Risk Limit Checks")
        logger.info("-" * 80)

        try:
            from services.risk_manager.main import RiskManagerService, RiskParameters

            db = SessionLocal()
            try:
                # Initialize risk manager
                risk_params = RiskParameters(
                    max_position_size=self.config.max_position_size_pct,
                    max_portfolio_risk=2.0,
                    max_drawdown=20.0,
                    stop_loss_pct=5.0,
                    max_leverage=1.0,
                    max_total_loss=28.0
                )

                service = RiskManagerService(risk_params=risk_params)

                # Calculate and update risk metrics
                logger.info("Calculating portfolio metrics...")
                metrics = service.calculate_portfolio_metrics(self.config.user_id, db)

                logger.info(f"Portfolio Status:")
                logger.info(f"  Total Value: {metrics.total_value:,} KRW")
                logger.info(f"  Total P&L: {metrics.total_pnl:,} KRW ({metrics.total_pnl_pct:.2f}%)")
                logger.info(f"  Positions: {metrics.position_count}")
                logger.info(f"  Current Drawdown: {metrics.current_drawdown:.2f}%")
                logger.info(f"  Loss from Initial: {metrics.total_loss_from_initial_pct:.2f}%")
                logger.info(f"  Trading Halted: {metrics.is_trading_halted}")

                # Update risk metrics in database
                service.update_risk_metrics(metrics, db)

                # Check for risk violations
                risk_status = service.check_portfolio_risk(self.config.user_id, db)

                if risk_status['status'] == 'HALTED':
                    logger.critical("TRADING IS HALTED!")
                    for violation in risk_status['violations']:
                        logger.critical(f"  - {violation}")
                elif risk_status['status'] == 'WARNING':
                    logger.warning("Risk violations detected:")
                    for violation in risk_status['violations']:
                        logger.warning(f"  - {violation}")
                else:
                    logger.info("All risk checks passed")

                if risk_status['warnings']:
                    logger.warning("Risk warnings:")
                    for warning in risk_status['warnings']:
                        logger.warning(f"  - {warning}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in risk checks: {e}", exc_info=True)

        logger.info("-" * 80)

    def _print_schedule(self):
        """Print all scheduled jobs."""
        logger.info("\nScheduled Jobs:")
        logger.info("-" * 80)

        jobs = self.scheduler.get_jobs()
        if not jobs:
            logger.info("No jobs scheduled")
            return

        for job in jobs:
            next_run = job.next_run_time
            if next_run:
                next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S %Z')
            else:
                next_run_str = "Not scheduled"

            logger.info(f"  [{job.id}] {job.name}")
            logger.info(f"    Next run: {next_run_str}")

        logger.info("-" * 80)

    def get_status(self) -> dict:
        """
        Get orchestrator status.

        Returns:
            Dictionary with status information
        """
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })

        return {
            'running': self.running,
            'timezone': self.config.timezone,
            'user_id': self.config.user_id,
            'dry_run': self.config.dry_run,
            'jobs': jobs_info
        }

    def run_job_now(self, job_id: str):
        """
        Manually trigger a scheduled job.

        Args:
            job_id: ID of the job to run
        """
        job = self.scheduler.get_job(job_id)
        if not job:
            logger.error(f"Job '{job_id}' not found")
            return

        logger.info(f"Manually triggering job: {job.name}")
        job.func()
