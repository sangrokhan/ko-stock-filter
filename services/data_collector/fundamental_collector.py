"""
Fundamental data collector for Korean stocks.
Fetches company fundamental data (PER, PBR, ROE, etc.).
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
import pandas as pd
from pykrx import stock as pykrx_stock
from sqlalchemy import and_

# Add shared directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database.models import Stock, FundamentalIndicator
from services.data_collector.db_session import get_db_session
from services.data_collector.utils import (
    retry_on_error,
    log_execution_time,
    RateLimiter,
    safe_float_conversion,
    safe_int_conversion
)

logger = logging.getLogger(__name__)

# Rate limiter: 0.5 requests per second (slower to avoid rate limiting)
rate_limiter = RateLimiter(requests_per_second=0.5)


class FundamentalCollector:
    """
    Collects fundamental data for Korean stocks.
    """

    def __init__(self):
        """Initialize the fundamental collector."""
        self.rate_limiter = rate_limiter
        logger.info("FundamentalCollector initialized")

    @retry_on_error(max_attempts=3, min_wait=2, max_wait=10)
    def fetch_fundamental_data(
        self,
        ticker: str,
        date: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Fetch fundamental data for a specific stock.

        Args:
            ticker: Stock ticker code
            date: Date in YYYYMMDD format (default: today)

        Returns:
            Dictionary with fundamental data or None if not found

        Raises:
            Exception: If data fetching fails
        """
        self.rate_limiter.wait()

        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        logger.debug(f"Fetching fundamental data for {ticker} on {date}")

        fundamental_data = {}

        try:
            # Get fundamental data (PER, PBR, EPS, BPS, etc.)
            try:
                fund_df = pykrx_stock.get_market_fundamental_by_ticker(date, market="ALL")

                if ticker in fund_df.index:
                    stock_data = fund_df.loc[ticker]
                    fundamental_data.update({
                        'bps': safe_float_conversion(stock_data.get('BPS', 0)),
                        'per': safe_float_conversion(stock_data.get('PER', 0)),
                        'pbr': safe_float_conversion(stock_data.get('PBR', 0)),
                        'eps': safe_float_conversion(stock_data.get('EPS', 0)),
                        'div_yield': safe_float_conversion(stock_data.get('DIV', 0)),
                        'dps': safe_float_conversion(stock_data.get('DPS', 0))
                    })
                    logger.debug(f"Fetched fundamental data for {ticker}")
            except Exception as e:
                logger.debug(f"Could not fetch fundamental data for {ticker}: {e}")

            # Get market cap and shares
            try:
                cap_df = pykrx_stock.get_market_cap_by_ticker(date, market="ALL")

                if ticker in cap_df.index:
                    cap_data = cap_df.loc[ticker]
                    fundamental_data.update({
                        'market_cap': safe_int_conversion(cap_data.get('시가총액', 0)),
                        'listed_shares': safe_int_conversion(cap_data.get('상장주식수', 0))
                    })
            except Exception as e:
                logger.debug(f"Could not fetch market cap for {ticker}: {e}")

            return fundamental_data if fundamental_data else None

        except Exception as e:
            logger.error(f"Error fetching fundamental data for {ticker}: {e}")
            return None

    @retry_on_error(max_attempts=3, min_wait=2, max_wait=10)
    def fetch_all_fundamentals_bulk(
        self,
        date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch fundamental data for all stocks in bulk (more efficient).

        Args:
            date: Date in YYYYMMDD format (default: today)

        Returns:
            DataFrame with fundamental data for all stocks

        Raises:
            Exception: If data fetching fails
        """
        self.rate_limiter.wait()

        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        logger.info(f"Fetching bulk fundamental data for date {date}")

        try:
            # Get all fundamental data at once
            fund_df = pykrx_stock.get_market_fundamental_by_ticker(date, market="ALL")
            cap_df = pykrx_stock.get_market_cap_by_ticker(date, market="ALL")

            # Merge the dataframes
            combined_df = fund_df.join(cap_df, how='outer')

            logger.info(f"Fetched fundamental data for {len(combined_df)} stocks")
            return combined_df

        except Exception as e:
            logger.error(f"Error fetching bulk fundamental data: {e}")
            return None

    @log_execution_time
    def collect_fundamentals_for_stock(
        self,
        ticker: str,
        date: Optional[str] = None
    ) -> bool:
        """
        Collect and save fundamental data for a specific stock.

        Args:
            ticker: Stock ticker code
            date: Date in YYYYMMDD format (default: today)

        Returns:
            True if successful, False otherwise
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        logger.info(f"Collecting fundamentals for {ticker} on {date}")

        # Fetch fundamental data
        fund_data = self.fetch_fundamental_data(ticker, date)

        if not fund_data:
            logger.warning(f"No fundamental data available for {ticker}")
            return False

        # Save to database
        success = self._save_fundamentals_to_db(ticker, date, fund_data)

        if success:
            logger.info(f"Successfully saved fundamental data for {ticker}")
        else:
            logger.warning(f"Failed to save fundamental data for {ticker}")

        return success

    @log_execution_time
    def collect_fundamentals_for_all_stocks(
        self,
        date: Optional[str] = None
    ) -> dict:
        """
        Collect fundamental data for all active stocks using bulk fetch.

        Args:
            date: Date in YYYYMMDD format (default: today)

        Returns:
            Dictionary with statistics
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        logger.info(f"Collecting fundamentals for all stocks on {date}")

        stats = {
            'total_stocks': 0,
            'successful': 0,
            'failed': 0
        }

        # Fetch all fundamentals in bulk (more efficient)
        fund_df = self.fetch_all_fundamentals_bulk(date)

        if fund_df is None or fund_df.empty:
            logger.error("Failed to fetch bulk fundamental data")
            return stats

        with get_db_session() as db:
            # Get all active stocks
            stocks = db.query(Stock).filter(Stock.is_active == True).all()
            stats['total_stocks'] = len(stocks)

            logger.info(f"Processing {len(stocks)} stocks")

            for stock in stocks:
                try:
                    # Check if data exists in the bulk fetch
                    if stock.ticker not in fund_df.index:
                        logger.debug(f"No fundamental data for {stock.ticker}")
                        stats['failed'] += 1
                        continue

                    row = fund_df.loc[stock.ticker]

                    # Extract data
                    fund_data = {
                        'bps': safe_float_conversion(row.get('BPS', 0)),
                        'per': safe_float_conversion(row.get('PER', 0)),
                        'pbr': safe_float_conversion(row.get('PBR', 0)),
                        'eps': safe_float_conversion(row.get('EPS', 0)),
                        'div_yield': safe_float_conversion(row.get('DIV', 0)),
                        'dps': safe_float_conversion(row.get('DPS', 0)),
                        'market_cap': safe_int_conversion(row.get('시가총액', 0)),
                        'listed_shares': safe_int_conversion(row.get('상장주식수', 0))
                    }

                    # Save to database
                    success = self._save_fundamentals_to_db(stock.ticker, date, fund_data)

                    if success:
                        stats['successful'] += 1

                        # Also update the stock table with market cap and shares
                        stock.market_cap = fund_data.get('market_cap')
                        stock.listed_shares = fund_data.get('listed_shares')
                        stock.updated_at = datetime.utcnow()
                    else:
                        stats['failed'] += 1

                    # Commit in batches
                    if stats['successful'] % 50 == 0:
                        db.commit()
                        logger.info(f"Committed batch: {stats['successful']} successful so far")

                except Exception as e:
                    logger.error(f"Error processing fundamentals for {stock.ticker}: {e}")
                    stats['failed'] += 1
                    continue

            # Final commit
            db.commit()

        logger.info(
            f"Fundamental collection complete: {stats['successful']}/{stats['total_stocks']} stocks"
        )

        return stats

    def _save_fundamentals_to_db(
        self,
        ticker: str,
        date_str: str,
        fund_data: Dict
    ) -> bool:
        """
        Save fundamental data to database.

        Args:
            ticker: Stock ticker code
            date_str: Date in YYYYMMDD format
            fund_data: Dictionary with fundamental data

        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse date
            fund_date = datetime.strptime(date_str, '%Y%m%d')

            with get_db_session() as db:
                # Get stock
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()

                if not stock:
                    logger.error(f"Stock {ticker} not found in database")
                    return False

                # Check if fundamental record already exists
                existing = db.query(FundamentalIndicator).filter(
                    and_(
                        FundamentalIndicator.stock_id == stock.id,
                        FundamentalIndicator.date == fund_date
                    )
                ).first()

                if existing:
                    # Update existing record
                    existing.per = fund_data.get('per')
                    existing.pbr = fund_data.get('pbr')
                    existing.eps = fund_data.get('eps')
                    existing.bps = fund_data.get('bps')
                    existing.dividend_yield = fund_data.get('div_yield')
                    existing.dps = fund_data.get('dps')
                    existing.updated_at = datetime.utcnow()
                    logger.debug(f"Updated fundamental data for {ticker}")
                else:
                    # Create new record
                    new_fund = FundamentalIndicator(
                        stock_id=stock.id,
                        date=fund_date,
                        per=fund_data.get('per'),
                        pbr=fund_data.get('pbr'),
                        eps=fund_data.get('eps'),
                        bps=fund_data.get('bps'),
                        dividend_yield=fund_data.get('div_yield'),
                        dps=fund_data.get('dps')
                    )
                    db.add(new_fund)
                    logger.debug(f"Added fundamental data for {ticker}")

                db.commit()
                return True

        except Exception as e:
            logger.error(f"Error saving fundamental data for {ticker}: {e}")
            return False
