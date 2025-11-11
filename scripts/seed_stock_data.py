#!/usr/bin/env python3
"""
Data seeding script for Korean Stock Trading System.

This script seeds the database with a predefined list of representative Korean stocks
and collects sufficient historical data for technical indicator calculations.

Features:
- Seeds stocks from major Korean indices (KOSPI, KOSDAQ)
- Collects historical price data (configurable period, default 1 year)
- Collects fundamental data for each stock
- Ensures minimum data requirements for technical indicators:
  - SMA 200: requires at least 200 days of price data
  - MACD: requires at least 26 days of price data
  - RSI: requires at least 14 days of price data

Usage:
    python scripts/seed_stock_data.py [options]

Options:
    --days DAYS          Number of days of historical data to collect (default: 365)
    --tickers TICKERS    Comma-separated list of tickers to seed (overrides default list)
    --dry-run           Show what would be done without actually doing it
    --skip-prices       Skip price data collection
    --skip-fundamentals Skip fundamental data collection
"""
import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from shared.database.models import Stock, StockPrice, FundamentalIndicator
from shared.database.connection import get_database_url, get_db_session
from services.data_collector.stock_code_collector import StockCodeCollector
from services.data_collector.price_collector import PriceCollector
from services.data_collector.fundamental_collector import FundamentalCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# Default list of representative Korean stocks to seed
# These stocks are chosen for their high liquidity, market cap, and representativeness
DEFAULT_STOCK_TICKERS = [
    # KOSPI - Large Cap Blue Chips
    "005930",  # Samsung Electronics
    "000660",  # SK Hynix
    "035420",  # NAVER
    "051910",  # LG Chem
    "035720",  # Kakao
    "005380",  # Hyundai Motor
    "068270",  # Celltrion
    "006400",  # Samsung SDI
    "012330",  # Hyundai Mobis
    "207940",  # Samsung Biologics
    "105560",  # KB Financial Group
    "055550",  # Shinhan Financial Group
    "086790",  # Hana Financial Group
    "015760",  # Korea Electric Power
    "096770",  # SK Innovation
    "017670",  # SK Telecom
    "032830",  # Samsung Life Insurance
    "033780",  # KT&G
    "003550",  # LG
    "028260",  # Samsung C&T

    # KOSPI - Mid Cap
    "018260",  # Samsung SDS
    "271560",  # Orion
    "034730",  # SK
    "011170",  # Lotte Chemical
    "028050",  # Samsung Engineering

    # KOSDAQ - Growth Stocks
    "247540",  # Ecopro BM
    "086520",  # Ecopro
    "357780",  # Solus Advanced Materials
    "196170",  # Alteogen
    "293490",  # Kakao Games
    "095340",  # ISC
    "112040",  # Wemade
    "263750",  # Pearl Abyss
    "328130",  # Luchen Systems
    "214150",  # Classys
]


class DataSeeder:
    """Data seeder for Korean stock trading system."""

    def __init__(
        self,
        days: int = 365,
        dry_run: bool = False,
        skip_prices: bool = False,
        skip_fundamentals: bool = False
    ):
        """
        Initialize the data seeder.

        Args:
            days: Number of days of historical data to collect
            dry_run: If True, show what would be done without doing it
            skip_prices: If True, skip price data collection
            skip_fundamentals: If True, skip fundamental data collection
        """
        self.days = days
        self.dry_run = dry_run
        self.skip_prices = skip_prices
        self.skip_fundamentals = skip_fundamentals

        # Initialize collectors
        if not dry_run:
            self.stock_code_collector = StockCodeCollector()
            self.price_collector = PriceCollector()
            self.fundamental_collector = FundamentalCollector()

        # Calculate date range
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=days)

        logger.info(f"DataSeeder initialized")
        logger.info(f"  Data collection period: {self.start_date.date()} to {self.end_date.date()}")
        logger.info(f"  Days: {self.days}")
        logger.info(f"  Dry run: {self.dry_run}")
        logger.info(f"  Skip prices: {self.skip_prices}")
        logger.info(f"  Skip fundamentals: {self.skip_fundamentals}")

    def check_stock_exists(self, ticker: str, session: Session) -> Optional[Stock]:
        """
        Check if a stock exists in the database.

        Args:
            ticker: Stock ticker code
            session: Database session

        Returns:
            Stock object if found, None otherwise
        """
        stmt = select(Stock).where(Stock.ticker == ticker)
        result = session.execute(stmt)
        return result.scalar_one_or_none()

    def check_price_data_count(self, ticker: str, session: Session) -> int:
        """
        Check how many price records exist for a stock.

        Args:
            ticker: Stock ticker code
            session: Database session

        Returns:
            Number of price records
        """
        stock = self.check_stock_exists(ticker, session)
        if not stock:
            return 0

        stmt = select(StockPrice).where(StockPrice.stock_id == stock.id)
        result = session.execute(stmt)
        return len(result.scalars().all())

    def check_fundamental_data_exists(self, ticker: str, session: Session) -> bool:
        """
        Check if fundamental data exists for a stock.

        Args:
            ticker: Stock ticker code
            session: Database session

        Returns:
            True if fundamental data exists, False otherwise
        """
        stock = self.check_stock_exists(ticker, session)
        if not stock:
            return False

        stmt = select(FundamentalIndicator).where(FundamentalIndicator.stock_id == stock.id)
        result = session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def seed_stock_metadata(self, tickers: List[str]) -> Dict[str, bool]:
        """
        Ensure stock metadata exists in the database.

        Args:
            tickers: List of stock tickers to seed

        Returns:
            Dictionary mapping ticker to success status
        """
        logger.info(f"Seeding stock metadata for {len(tickers)} tickers")

        if self.dry_run:
            logger.info("[DRY RUN] Would seed stock metadata")
            return {ticker: True for ticker in tickers}

        results = {}
        with get_db_session() as session:
            for ticker in tickers:
                try:
                    # Check if stock already exists
                    stock = self.check_stock_exists(ticker, session)

                    if stock:
                        logger.info(f"  {ticker}: Already exists (id={stock.id}, name={stock.name_kr})")
                        results[ticker] = True
                    else:
                        # Stock doesn't exist, need to collect it
                        logger.info(f"  {ticker}: Not found, collecting from data source...")

                        # Use stock code collector to fetch and save the stock
                        # This will query the external API and save to database
                        success = self.stock_code_collector.collect_single_stock(ticker)

                        if success:
                            logger.info(f"  {ticker}: Successfully collected and saved")
                            results[ticker] = True
                        else:
                            logger.warning(f"  {ticker}: Failed to collect")
                            results[ticker] = False

                    # Small delay to avoid rate limiting
                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"  {ticker}: Error - {e}")
                    results[ticker] = False

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Stock metadata seeding completed: {success_count}/{len(tickers)} successful")

        return results

    def seed_price_data(self, tickers: List[str]) -> Dict[str, int]:
        """
        Seed price data for the given tickers.

        Args:
            tickers: List of stock tickers to seed

        Returns:
            Dictionary mapping ticker to number of records collected
        """
        logger.info(f"Seeding price data for {len(tickers)} tickers")
        logger.info(f"  Period: {self.start_date.date()} to {self.end_date.date()}")

        if self.dry_run:
            logger.info("[DRY RUN] Would collect price data")
            return {ticker: 0 for ticker in tickers}

        results = {}
        start_date_str = self.start_date.strftime('%Y-%m-%d')
        end_date_str = self.end_date.strftime('%Y-%m-%d')

        for i, ticker in enumerate(tickers, 1):
            try:
                # Check existing data count
                with get_db_session() as session:
                    existing_count = self.check_price_data_count(ticker, session)

                logger.info(f"  [{i}/{len(tickers)}] {ticker}: Existing records: {existing_count}")

                if existing_count >= self.days * 0.8:  # If we have at least 80% of requested data
                    logger.info(f"  {ticker}: Sufficient data already exists, skipping")
                    results[ticker] = existing_count
                    continue

                # Collect price data
                logger.info(f"  {ticker}: Collecting price data...")
                count = self.price_collector.collect_prices_for_stock(
                    ticker, start_date_str, end_date_str
                )

                if count > 0:
                    logger.info(f"  {ticker}: Collected {count} price records")
                    results[ticker] = count
                else:
                    logger.warning(f"  {ticker}: No price data collected")
                    results[ticker] = 0

                # Rate limiting: small delay between requests
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"  {ticker}: Error collecting price data - {e}")
                results[ticker] = 0

        total_records = sum(results.values())
        success_count = sum(1 for v in results.values() if v > 0)
        logger.info(f"Price data seeding completed: {success_count}/{len(tickers)} stocks, {total_records} total records")

        return results

    def seed_fundamental_data(self, tickers: List[str]) -> Dict[str, bool]:
        """
        Seed fundamental data for the given tickers.

        Args:
            tickers: List of stock tickers to seed

        Returns:
            Dictionary mapping ticker to success status
        """
        logger.info(f"Seeding fundamental data for {len(tickers)} tickers")

        if self.dry_run:
            logger.info("[DRY RUN] Would collect fundamental data")
            return {ticker: True for ticker in tickers}

        results = {}

        for i, ticker in enumerate(tickers, 1):
            try:
                # Check if fundamental data already exists
                with get_db_session() as session:
                    exists = self.check_fundamental_data_exists(ticker, session)

                if exists:
                    logger.info(f"  [{i}/{len(tickers)}] {ticker}: Fundamental data already exists, skipping")
                    results[ticker] = True
                    continue

                # Collect fundamental data
                logger.info(f"  [{i}/{len(tickers)}] {ticker}: Collecting fundamental data...")
                success = self.fundamental_collector.collect_fundamentals_for_stock(ticker)

                if success:
                    logger.info(f"  {ticker}: Successfully collected fundamental data")
                    results[ticker] = True
                else:
                    logger.warning(f"  {ticker}: Failed to collect fundamental data")
                    results[ticker] = False

                # Rate limiting: small delay between requests
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"  {ticker}: Error collecting fundamental data - {e}")
                results[ticker] = False

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Fundamental data seeding completed: {success_count}/{len(tickers)} successful")

        return results

    def seed(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Seed all data for the given tickers.

        Args:
            tickers: List of stock tickers to seed

        Returns:
            Dictionary with seeding results
        """
        logger.info("=" * 80)
        logger.info("Starting data seeding")
        logger.info("=" * 80)
        logger.info(f"Tickers to seed: {', '.join(tickers)}")
        logger.info(f"Total: {len(tickers)} stocks")
        logger.info("")

        results = {
            "stock_metadata": {},
            "price_data": {},
            "fundamental_data": {}
        }

        # Step 1: Seed stock metadata
        logger.info("Step 1/3: Seeding stock metadata")
        logger.info("-" * 80)
        results["stock_metadata"] = self.seed_stock_metadata(tickers)
        logger.info("")

        # Filter to only successfully seeded stocks
        successful_tickers = [
            ticker for ticker, success in results["stock_metadata"].items()
            if success
        ]

        if not successful_tickers:
            logger.error("No stocks were successfully seeded. Aborting.")
            return results

        # Step 2: Seed price data
        if not self.skip_prices:
            logger.info("Step 2/3: Seeding price data")
            logger.info("-" * 80)
            results["price_data"] = self.seed_price_data(successful_tickers)
            logger.info("")
        else:
            logger.info("Step 2/3: Skipping price data collection (--skip-prices)")
            logger.info("")

        # Step 3: Seed fundamental data
        if not self.skip_fundamentals:
            logger.info("Step 3/3: Seeding fundamental data")
            logger.info("-" * 80)
            results["fundamental_data"] = self.seed_fundamental_data(successful_tickers)
            logger.info("")
        else:
            logger.info("Step 3/3: Skipping fundamental data collection (--skip-fundamentals)")
            logger.info("")

        # Print summary
        logger.info("=" * 80)
        logger.info("Data seeding completed")
        logger.info("=" * 80)
        logger.info(f"Stock metadata: {sum(1 for v in results['stock_metadata'].values() if v)}/{len(tickers)} successful")

        if not self.skip_prices:
            total_price_records = sum(results["price_data"].values())
            successful_price_stocks = sum(1 for v in results["price_data"].values() if v > 0)
            logger.info(f"Price data: {successful_price_stocks}/{len(successful_tickers)} stocks, {total_price_records} total records")

        if not self.skip_fundamentals:
            logger.info(f"Fundamental data: {sum(1 for v in results['fundamental_data'].values() if v)}/{len(successful_tickers)} successful")

        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Run indicator calculator service to compute technical indicators")
        logger.info("  2. Run stock scorer service to compute composite scores")
        logger.info("  3. Run stability calculator service to compute stability scores")

        return results


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Seed stock data for Korean Stock Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days of historical data to collect (default: 365)"
    )

    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers to seed (overrides default list)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )

    parser.add_argument(
        "--skip-prices",
        action="store_true",
        help="Skip price data collection"
    )

    parser.add_argument(
        "--skip-fundamentals",
        action="store_true",
        help="Skip fundamental data collection"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Determine which tickers to seed
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",")]
        logger.info(f"Using custom ticker list: {tickers}")
    else:
        tickers = DEFAULT_STOCK_TICKERS
        logger.info(f"Using default ticker list ({len(tickers)} stocks)")

    # Create seeder and run
    seeder = DataSeeder(
        days=args.days,
        dry_run=args.dry_run,
        skip_prices=args.skip_prices,
        skip_fundamentals=args.skip_fundamentals
    )

    try:
        results = seeder.seed(tickers)

        # Exit with appropriate code
        if all(results["stock_metadata"].values()):
            logger.info("All stocks seeded successfully!")
            sys.exit(0)
        else:
            logger.warning("Some stocks failed to seed")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nSeeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during seeding: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
