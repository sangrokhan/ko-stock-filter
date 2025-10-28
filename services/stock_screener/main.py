"""
Main entry point for Stock Screener Service.
Filters stocks based on technical and fundamental criteria.
"""
import logging
from typing import List, Dict, Optional
from contextlib import contextmanager

from sqlalchemy.orm import Session

from shared.database.connection import get_engine, get_session
from shared.configs.config import get_settings
from services.stock_screener.screening_engine import (
    StockScreeningEngine,
    ScreeningCriteria,
    ScreeningResult
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StockScreenerService:
    """Service for screening and filtering stocks."""

    def __init__(self):
        """Initialize the stock screener service."""
        self.settings = get_settings()
        self.engine = get_engine(self.settings.database_url)
        self.running = False
        logger.info("Stock Screener Service initialized")

    @contextmanager
    def _get_db_session(self) -> Session:
        """Get database session context manager."""
        session = get_session(self.engine)
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def start(self):
        """Start the stock screener service."""
        self.running = True
        logger.info("Stock Screener Service started")

    def stop(self):
        """Stop the stock screener service."""
        self.running = False
        logger.info("Stock Screener Service stopped")

    def screen_stocks(
        self,
        criteria: Optional[ScreeningCriteria] = None
    ) -> List[ScreeningResult]:
        """
        Screen stocks based on given criteria.

        Args:
            criteria: Screening criteria (uses defaults if None)

        Returns:
            List of stocks matching the criteria
        """
        with self._get_db_session() as session:
            engine = StockScreeningEngine(session, self.settings)
            results = engine.screen_stocks(criteria)

            logger.info(f"Screened {len(results)} stocks matching criteria")
            return results

    def identify_undervalued_stocks(
        self,
        criteria: Optional[ScreeningCriteria] = None
    ) -> List[ScreeningResult]:
        """
        Identify undervalued stocks.

        Args:
            criteria: Screening criteria (with undervalued flags)

        Returns:
            List of undervalued stocks
        """
        with self._get_db_session() as session:
            engine = StockScreeningEngine(session, self.settings)
            results = engine.identify_undervalued_stocks(criteria)

            logger.info(f"Found {len(results)} undervalued stocks")
            return results

    def filter_high_volatility(
        self,
        max_volatility_pct: Optional[float] = None
    ) -> List[ScreeningResult]:
        """
        Filter out high volatility stocks.

        Args:
            max_volatility_pct: Maximum volatility percentage (uses default if None)

        Returns:
            List of low volatility stocks
        """
        criteria = ScreeningCriteria(
            max_volatility_pct=max_volatility_pct or self.settings.max_volatility_pct
        )
        return self.screen_stocks(criteria)

    def filter_overvalued(
        self,
        max_per: Optional[float] = None,
        max_pbr: Optional[float] = None
    ) -> List[ScreeningResult]:
        """
        Filter out overvalued stocks.

        Args:
            max_per: Maximum PER (uses default if None)
            max_pbr: Maximum PBR (uses default if None)

        Returns:
            List of reasonably valued stocks
        """
        criteria = ScreeningCriteria(
            max_per=max_per or self.settings.max_per,
            max_pbr=max_pbr or self.settings.max_pbr
        )
        return self.screen_stocks(criteria)

    def filter_unstable_companies(
        self,
        max_debt_ratio_pct: Optional[float] = None
    ) -> List[ScreeningResult]:
        """
        Filter out financially unstable companies.

        Args:
            max_debt_ratio_pct: Maximum debt ratio percentage (uses default if None)

        Returns:
            List of financially stable companies
        """
        criteria = ScreeningCriteria(
            max_debt_ratio_pct=max_debt_ratio_pct or self.settings.max_debt_ratio_pct
        )
        return self.screen_stocks(criteria)

    def filter_low_liquidity(
        self,
        min_avg_volume: Optional[int] = None,
        min_trading_value: Optional[float] = None
    ) -> List[ScreeningResult]:
        """
        Filter out low liquidity stocks.

        Args:
            min_avg_volume: Minimum average volume (uses default if None)
            min_trading_value: Minimum trading value (uses default if None)

        Returns:
            List of liquid stocks
        """
        criteria = ScreeningCriteria(
            min_avg_volume=min_avg_volume or self.settings.min_avg_volume,
            min_trading_value=min_trading_value or self.settings.min_trading_value
        )
        return self.screen_stocks(criteria)

    def apply_default_filters(self) -> List[ScreeningResult]:
        """
        Apply all default filters from configuration.

        Returns:
            List of stocks passing all default filters
        """
        logger.info("Applying default screening filters")
        criteria = ScreeningCriteria(
            max_volatility_pct=self.settings.max_volatility_pct,
            max_per=self.settings.max_per,
            max_pbr=self.settings.max_pbr,
            max_debt_ratio_pct=self.settings.max_debt_ratio_pct,
            min_avg_volume=self.settings.min_avg_volume,
            min_trading_value=self.settings.min_trading_value,
            min_price_history_days=self.settings.min_price_history_days,
            min_volume_history_days=self.settings.min_volume_history_days
        )
        return self.screen_stocks(criteria)

    def get_screening_summary(self, results: List[ScreeningResult]) -> Dict:
        """
        Get summary statistics for screening results.

        Args:
            results: List of screening results

        Returns:
            Dictionary with summary statistics
        """
        with self._get_db_session() as session:
            engine = StockScreeningEngine(session, self.settings)
            return engine.get_screening_summary(results)


def main():
    """Main entry point for command-line execution."""
    service = StockScreenerService()
    service.start()

    try:
        # Example: Apply default filters
        logger.info("Running default stock screening...")
        results = service.apply_default_filters()

        logger.info(f"\n{'='*60}")
        logger.info(f"SCREENING RESULTS: {len(results)} stocks passed all filters")
        logger.info(f"{'='*60}")

        # Show top 10 results
        for i, result in enumerate(results[:10], 1):
            logger.info(f"\n{i}. {result.ticker} ({result.name_kr})")
            logger.info(f"   Market: {result.market} | Sector: {result.sector}")
            logger.info(f"   Price: {result.current_price:,.0f} KRW | Market Cap: {result.market_cap:,.0f}")
            logger.info(f"   PER: {result.per:.2f} | PBR: {result.pbr:.2f}")
            logger.info(f"   Debt Ratio: {result.debt_ratio:.1f}%")
            logger.info(f"   Avg Volume: {result.avg_volume:,.0f}")
            logger.info(f"   Volatility: {result.volatility_pct:.1f}%")
            logger.info(f"   Stability Score: {result.stability_score:.1f}/100")
            if result.is_undervalued:
                logger.info(f"   UNDERVALUED: {', '.join(result.undervalued_reasons)}")

        # Show summary
        summary = service.get_screening_summary(results)
        logger.info(f"\n{'='*60}")
        logger.info("SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total stocks: {summary['total_stocks']}")
        logger.info(f"Undervalued: {summary['undervalued_count']}")
        logger.info(f"Markets: {summary['markets']}")
        logger.info(f"Top sectors: {dict(sorted(summary['sectors'].items(), key=lambda x: x[1], reverse=True)[:5])}")
        if summary['avg_per']:
            logger.info(f"Average PER: {summary['avg_per']:.2f}")
        if summary['avg_pbr']:
            logger.info(f"Average PBR: {summary['avg_pbr']:.2f}")
        if summary['avg_debt_ratio']:
            logger.info(f"Average Debt Ratio: {summary['avg_debt_ratio']:.1f}%")

        # Example: Find undervalued stocks
        logger.info(f"\n{'='*60}")
        logger.info("IDENTIFYING UNDERVALUED STOCKS")
        logger.info(f"{'='*60}")
        undervalued = service.identify_undervalued_stocks()
        logger.info(f"Found {len(undervalued)} undervalued stocks")

        for i, result in enumerate(undervalued[:5], 1):
            logger.info(f"\n{i}. {result.ticker} ({result.name_kr})")
            logger.info(f"   Reasons: {', '.join(result.undervalued_reasons)}")
            logger.info(f"   PER: {result.per:.2f} | PBR: {result.pbr:.2f}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error during screening: {e}", exc_info=True)
    finally:
        service.stop()


if __name__ == "__main__":
    main()
