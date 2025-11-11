"""
Stock code collector for Korean markets (KOSPI, KOSDAQ).
Fetches all stock codes and basic information.
"""
import sys
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Dict, Optional
import pandas as pd
from pykrx import stock as pykrx_stock
import FinanceDataReader as fdr

# Add shared directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database.models import Stock
from services.data_collector.db_session import get_db_session
from services.data_collector.utils import (
    retry_on_error,
    log_execution_time,
    RateLimiter,
    safe_int_conversion
)

logger = logging.getLogger(__name__)

# Rate limiter: 1 request per second to be respectful to data sources
rate_limiter = RateLimiter(requests_per_second=1.0)


class StockCodeCollector:
    """
    Collects stock codes and basic information for KOSPI and KOSDAQ markets.
    """

    def __init__(self):
        """Initialize the stock code collector."""
        self.rate_limiter = rate_limiter
        logger.info("StockCodeCollector initialized")

    @retry_on_error(max_attempts=3, min_wait=2, max_wait=10)
    def fetch_stock_codes(self, market: str) -> pd.DataFrame:
        """
        Fetch stock codes from a specific market.

        Args:
            market: Market name ('KOSPI', 'KOSDAQ', or 'KONEX')

        Returns:
            DataFrame with stock codes and names

        Raises:
            Exception: If data fetching fails
        """
        self.rate_limiter.wait()
        logger.info(f"Fetching stock codes from {market}")

        try:
            # Use FinanceDataReader to get stock listing
            df = fdr.StockListing(market)
            logger.info(f"Fetched {len(df)} stocks from {market}")
            return df
        except Exception as e:
            logger.error(f"Error fetching stock codes from {market}: {e}")
            raise

    @retry_on_error(max_attempts=3, min_wait=2, max_wait=10)
    def fetch_stock_details(self, ticker: str) -> Optional[Dict]:
        """
        Fetch detailed information for a specific stock using pykrx.

        Args:
            ticker: Stock ticker code

        Returns:
            Dictionary with stock details or None if not found

        Raises:
            Exception: If data fetching fails
        """
        self.rate_limiter.wait()

        try:
            # Get market cap and shares information
            today = datetime.now().strftime('%Y%m%d')

            # Try to get market cap data
            try:
                market_cap_data = pykrx_stock.get_market_cap_by_ticker(today, market="ALL")
                if ticker in market_cap_data.index:
                    stock_data = market_cap_data.loc[ticker]
                    return {
                        'market_cap': safe_int_conversion(stock_data.get('시가총액', 0)),
                        'listed_shares': safe_int_conversion(stock_data.get('상장주식수', 0))
                    }
            except Exception as e:
                logger.debug(f"Could not fetch market cap for {ticker}: {e}")

            return None

        except Exception as e:
            logger.debug(f"Error fetching details for {ticker}: {e}")
            return None

    @log_execution_time
    def collect_all_stock_codes(self) -> int:
        """
        Collect all stock codes from KOSPI, KOSDAQ, and KONEX markets
        and store them in the database.

        Returns:
            Number of stocks processed

        Raises:
            Exception: If collection fails
        """
        markets = ['KOSPI', 'KOSDAQ', 'KONEX']
        total_processed = 0

        for market in markets:
            try:
                logger.info(f"Processing {market} market")
                df = self.fetch_stock_codes(market)

                if df is None or df.empty:
                    logger.warning(f"No data received for {market}")
                    continue

                processed = self._save_stocks_to_db(df, market)
                total_processed += processed
                logger.info(f"Processed {processed} stocks from {market}")

            except Exception as e:
                logger.error(f"Error processing {market}: {e}")
                continue

        logger.info(f"Total stocks processed: {total_processed}")
        return total_processed

    def _save_stocks_to_db(self, df: pd.DataFrame, market: str) -> int:
        """
        Save stock data to database.

        Args:
            df: DataFrame with stock information
            market: Market name

        Returns:
            Number of stocks saved
        """
        count = 0

        with get_db_session() as db:
            for _, row in df.iterrows():
                try:
                    ticker = str(row.get('Code', row.get('Symbol', '')))
                    if not ticker:
                        continue

                    # Check if stock already exists
                    existing_stock = db.query(Stock).filter(Stock.ticker == ticker).first()

                    # Fetch additional details
                    details = self.fetch_stock_details(ticker)

                    if existing_stock:
                        # Update existing stock
                        existing_stock.name_kr = row.get('Name', existing_stock.name_kr)
                        existing_stock.name_en = row.get('Name', existing_stock.name_en)
                        existing_stock.market = market
                        existing_stock.sector = row.get('Sector', existing_stock.sector)
                        existing_stock.industry = row.get('Industry', existing_stock.industry)
                        existing_stock.is_active = True
                        existing_stock.updated_at = datetime.utcnow()

                        if details:
                            existing_stock.market_cap = details.get('market_cap')
                            existing_stock.listed_shares = details.get('listed_shares')

                        logger.debug(f"Updated stock: {ticker} - {existing_stock.name_kr}")
                    else:
                        # Create new stock
                        new_stock = Stock(
                            ticker=ticker,
                            name_kr=row.get('Name', ''),
                            name_en=row.get('Name', ''),
                            market=market,
                            sector=row.get('Sector', ''),
                            industry=row.get('Industry', ''),
                            is_active=True,
                            listed_date=row.get('ListingDate') if pd.notna(row.get('ListingDate')) else None,
                            market_cap=details.get('market_cap') if details else None,
                            listed_shares=details.get('listed_shares') if details else None
                        )
                        db.add(new_stock)
                        logger.debug(f"Added new stock: {ticker} - {new_stock.name_kr}")

                    count += 1

                    # Commit in batches of 50 to improve performance
                    if count % 50 == 0:
                        db.commit()
                        logger.info(f"Committed batch of 50 stocks (total: {count})")

                except Exception as e:
                    logger.error(f"Error saving stock {row.get('Code', 'unknown')}: {e}")
                    continue

            # Final commit
            db.commit()

        return count

    def collect_single_stock(self, ticker: str) -> bool:
        """
        Collect and save a single stock to the database.
        This method attempts to fetch stock information from all markets.

        Args:
            ticker: Stock ticker code to collect

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Collecting single stock: {ticker}")

            # Try to find the stock in each market
            markets = ['KOSPI', 'KOSDAQ', 'KONEX']
            stock_found = False

            for market in markets:
                try:
                    df = self.fetch_stock_codes(market)

                    if df is None or df.empty:
                        continue

                    # Check if ticker exists in this market
                    ticker_col = 'Code' if 'Code' in df.columns else 'Symbol'
                    stock_row = df[df[ticker_col] == ticker]

                    if not stock_row.empty:
                        # Found the stock, save it
                        with get_db_session() as db:
                            row = stock_row.iloc[0]

                            # Check if stock already exists
                            existing_stock = db.query(Stock).filter(Stock.ticker == ticker).first()

                            # Fetch additional details
                            details = self.fetch_stock_details(ticker)

                            if existing_stock:
                                # Update existing stock
                                existing_stock.name_kr = row.get('Name', existing_stock.name_kr)
                                existing_stock.name_en = row.get('Name', existing_stock.name_en)
                                existing_stock.market = market
                                existing_stock.sector = row.get('Sector', existing_stock.sector)
                                existing_stock.industry = row.get('Industry', existing_stock.industry)
                                existing_stock.is_active = True
                                existing_stock.updated_at = datetime.utcnow()

                                if details:
                                    existing_stock.market_cap = details.get('market_cap')
                                    existing_stock.listed_shares = details.get('listed_shares')

                                logger.info(f"Updated stock: {ticker} - {existing_stock.name_kr}")
                            else:
                                # Create new stock
                                new_stock = Stock(
                                    ticker=ticker,
                                    name_kr=row.get('Name', ''),
                                    name_en=row.get('Name', ''),
                                    market=market,
                                    sector=row.get('Sector', ''),
                                    industry=row.get('Industry', ''),
                                    is_active=True,
                                    listed_date=row.get('ListingDate') if pd.notna(row.get('ListingDate')) else None,
                                    market_cap=details.get('market_cap') if details else None,
                                    listed_shares=details.get('listed_shares') if details else None
                                )
                                db.add(new_stock)
                                logger.info(f"Added new stock: {ticker} - {new_stock.name_kr}")

                            db.commit()
                            stock_found = True
                            break

                except Exception as e:
                    logger.debug(f"Error checking {market} for ticker {ticker}: {e}")
                    continue

            if not stock_found:
                logger.warning(f"Stock {ticker} not found in any market")

            return stock_found

        except Exception as e:
            logger.error(f"Error collecting single stock {ticker}: {e}")
            return False

    @log_execution_time
    def update_stock_details(self, ticker: Optional[str] = None) -> int:
        """
        Update detailed information (market cap, shares) for stocks.

        Args:
            ticker: Specific ticker to update, or None to update all

        Returns:
            Number of stocks updated
        """
        count = 0

        with get_db_session() as db:
            if ticker:
                stocks = db.query(Stock).filter(
                    Stock.ticker == ticker,
                    Stock.is_active == True
                ).all()
            else:
                stocks = db.query(Stock).filter(Stock.is_active == True).all()

            logger.info(f"Updating details for {len(stocks)} stocks")

            for stock in stocks:
                try:
                    details = self.fetch_stock_details(stock.ticker)

                    if details:
                        stock.market_cap = details.get('market_cap')
                        stock.listed_shares = details.get('listed_shares')
                        stock.updated_at = datetime.utcnow()
                        count += 1

                        # Commit in batches
                        if count % 20 == 0:
                            db.commit()
                            logger.info(f"Updated {count} stocks so far")

                except Exception as e:
                    logger.error(f"Error updating details for {stock.ticker}: {e}")
                    continue

            db.commit()
            logger.info(f"Updated details for {count} stocks")

        return count
