"""
OHLCV price data collector for Korean stocks.
Fetches daily price data (Open, High, Low, Close, Volume).
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
import logging
import pandas as pd
from decimal import Decimal
from sqlalchemy import and_
import FinanceDataReader as fdr
from pykrx import stock as pykrx_stock

# Add shared directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database.models import Stock, StockPrice
from services.data_collector.db_session import get_db_session
from services.data_collector.utils import (
    retry_on_error,
    log_execution_time,
    RateLimiter,
    safe_float_conversion,
    safe_int_conversion
)

logger = logging.getLogger(__name__)

# Rate limiter: 1 request per second
rate_limiter = RateLimiter(requests_per_second=1.0)


class PriceCollector:
    """
    Collects OHLCV price data for Korean stocks.
    """

    def __init__(self):
        """Initialize the price collector."""
        self.rate_limiter = rate_limiter
        logger.info("PriceCollector initialized")

    @retry_on_error(max_attempts=3, min_wait=2, max_wait=10)
    def fetch_price_data(
        self,
        ticker: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV price data for a specific stock.

        Args:
            ticker: Stock ticker code
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (default: today)

        Returns:
            DataFrame with OHLCV data or None if not found

        Raises:
            Exception: If data fetching fails
        """
        self.rate_limiter.wait()

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        logger.debug(f"Fetching price data for {ticker} from {start_date} to {end_date}")

        try:
            # Try FinanceDataReader first
            df = fdr.DataReader(ticker, start_date, end_date)

            if df is not None and not df.empty:
                # Reset index to make Date a column
                df = df.reset_index()
                logger.debug(f"Fetched {len(df)} price records for {ticker}")
                return df
            else:
                logger.debug(f"No price data found for {ticker}")
                return None

        except Exception as e:
            logger.warning(f"FinanceDataReader failed for {ticker}: {e}, trying pykrx")

            try:
                # Fallback to pykrx
                start_date_fmt = start_date.replace('-', '')
                end_date_fmt = end_date.replace('-', '')

                df = pykrx_stock.get_market_ohlcv_by_date(
                    start_date_fmt,
                    end_date_fmt,
                    ticker
                )

                if df is not None and not df.empty:
                    df = df.reset_index()
                    # Rename columns to match FinanceDataReader format
                    df = df.rename(columns={
                        '날짜': 'Date',
                        '시가': 'Open',
                        '고가': 'High',
                        '저가': 'Low',
                        '종가': 'Close',
                        '거래량': 'Volume',
                        '거래대금': 'Value'
                    })
                    logger.debug(f"Fetched {len(df)} price records for {ticker} using pykrx")
                    return df
                else:
                    logger.debug(f"No price data found for {ticker} using pykrx")
                    return None

            except Exception as e2:
                logger.error(f"Both FinanceDataReader and pykrx failed for {ticker}: {e2}")
                return None

    @log_execution_time
    def collect_prices_for_stock(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        Collect and save price data for a specific stock.

        Args:
            ticker: Stock ticker code
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)

        Returns:
            Number of price records saved

        Raises:
            Exception: If collection fails
        """
        # Default to last 30 days if not specified
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"Collecting prices for {ticker} from {start_date} to {end_date}")

        # Fetch price data
        df = self.fetch_price_data(ticker, start_date, end_date)

        if df is None or df.empty:
            logger.warning(f"No price data available for {ticker}")
            return 0

        # Save to database
        count = self._save_prices_to_db(ticker, df)
        logger.info(f"Saved {count} price records for {ticker}")

        return count

    @log_execution_time
    def collect_prices_for_all_stocks(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        batch_size: int = 100
    ) -> dict:
        """
        Collect price data for all active stocks.

        Args:
            start_date: Start date (default: 1 day ago)
            end_date: End date (default: today)
            batch_size: Number of stocks to process before committing

        Returns:
            Dictionary with statistics (total_stocks, successful, failed)
        """
        # Default to yesterday if not specified
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"Collecting prices for all stocks from {start_date} to {end_date}")

        stats = {
            'total_stocks': 0,
            'successful': 0,
            'failed': 0,
            'total_records': 0
        }

        with get_db_session() as db:
            # Get all active stocks
            stocks = db.query(Stock).filter(Stock.is_active == True).all()
            stats['total_stocks'] = len(stocks)

            logger.info(f"Processing {len(stocks)} stocks")

            for i, stock in enumerate(stocks):
                try:
                    count = self.collect_prices_for_stock(
                        stock.ticker,
                        start_date,
                        end_date
                    )

                    if count > 0:
                        stats['successful'] += 1
                        stats['total_records'] += count
                    else:
                        stats['failed'] += 1

                    # Log progress
                    if (i + 1) % batch_size == 0:
                        logger.info(
                            f"Progress: {i + 1}/{len(stocks)} stocks processed "
                            f"({stats['successful']} successful, {stats['failed']} failed)"
                        )

                except Exception as e:
                    logger.error(f"Error collecting prices for {stock.ticker}: {e}")
                    stats['failed'] += 1
                    continue

        logger.info(
            f"Price collection complete: {stats['successful']}/{stats['total_stocks']} stocks, "
            f"{stats['total_records']} total records"
        )

        return stats

    def _save_prices_to_db(self, ticker: str, df: pd.DataFrame) -> int:
        """
        Save price data to database.

        Args:
            ticker: Stock ticker code
            df: DataFrame with price data

        Returns:
            Number of records saved
        """
        count = 0

        with get_db_session() as db:
            # Get stock_id
            stock = db.query(Stock).filter(Stock.ticker == ticker).first()

            if not stock:
                logger.error(f"Stock {ticker} not found in database")
                return 0

            for _, row in df.iterrows():
                try:
                    # Parse date
                    if isinstance(row['Date'], str):
                        price_date = datetime.strptime(row['Date'], '%Y-%m-%d')
                    else:
                        price_date = pd.to_datetime(row['Date'])

                    # Check if price record already exists
                    existing = db.query(StockPrice).filter(
                        and_(
                            StockPrice.stock_id == stock.id,
                            StockPrice.date == price_date
                        )
                    ).first()

                    # Extract price values
                    open_price = safe_float_conversion(row.get('Open', 0))
                    high_price = safe_float_conversion(row.get('High', 0))
                    low_price = safe_float_conversion(row.get('Low', 0))
                    close_price = safe_float_conversion(row.get('Close', 0))
                    volume = safe_int_conversion(row.get('Volume', 0))
                    trading_value = safe_int_conversion(row.get('Value', 0))

                    # Skip if all prices are zero
                    if open_price == 0 and close_price == 0:
                        continue

                    # Calculate change percentage
                    change_pct = row.get('Change', None)
                    if change_pct is None and open_price > 0:
                        change_pct = ((close_price - open_price) / open_price) * 100

                    if existing:
                        # Update existing record
                        existing.open = Decimal(str(open_price))
                        existing.high = Decimal(str(high_price))
                        existing.low = Decimal(str(low_price))
                        existing.close = Decimal(str(close_price))
                        existing.volume = volume
                        existing.trading_value = trading_value
                        existing.change_pct = safe_float_conversion(change_pct)
                        existing.adjusted_close = Decimal(str(row.get('Adj Close', close_price)))
                    else:
                        # Create new record
                        new_price = StockPrice(
                            stock_id=stock.id,
                            date=price_date,
                            open=Decimal(str(open_price)),
                            high=Decimal(str(high_price)),
                            low=Decimal(str(low_price)),
                            close=Decimal(str(close_price)),
                            volume=volume,
                            trading_value=trading_value,
                            change_pct=safe_float_conversion(change_pct),
                            adjusted_close=Decimal(str(row.get('Adj Close', close_price)))
                        )
                        db.add(new_price)

                    count += 1

                    # Commit in batches
                    if count % 100 == 0:
                        db.commit()

                except Exception as e:
                    logger.error(f"Error saving price record for {ticker} on {row.get('Date')}: {e}")
                    continue

            # Final commit
            db.commit()

        return count

    def get_last_price_date(self, ticker: str) -> Optional[datetime]:
        """
        Get the last date for which we have price data for a stock.

        Args:
            ticker: Stock ticker code

        Returns:
            Last price date or None if no data exists
        """
        with get_db_session() as db:
            stock = db.query(Stock).filter(Stock.ticker == ticker).first()

            if not stock:
                return None

            last_price = db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id
            ).order_by(StockPrice.date.desc()).first()

            return last_price.date if last_price else None
