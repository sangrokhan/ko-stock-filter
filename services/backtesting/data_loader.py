"""
Historical Data Loader for Backtesting

Efficiently loads historical price data, technical indicators, and fundamental
indicators from the database for backtesting purposes.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from shared.database.models import (
    Stock,
    StockPrice,
    TechnicalIndicator,
    FundamentalIndicator,
    CompositeScore,
)
from shared.database.connection import get_db_session


class BacktestDataLoader:
    """Load and prepare historical data for backtesting"""

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize data loader

        Args:
            db_session: Database session (optional, will create if not provided)
        """
        self.db_session = db_session or next(get_db_session())
        self._cache: Dict[str, pd.DataFrame] = {}

    def load_stock_universe(
        self, markets: Optional[List[str]] = None, sectors: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Load stock universe for backtesting

        Args:
            markets: List of markets to include (e.g., ['KOSPI', 'KOSDAQ'])
            sectors: List of sectors to include

        Returns:
            DataFrame with stock information
        """
        query = select(Stock).where(Stock.is_active == True)

        if markets:
            query = query.where(Stock.market.in_(markets))
        if sectors:
            query = query.where(Stock.sector.in_(sectors))

        result = self.db_session.execute(query)
        stocks = result.scalars().all()

        df = pd.DataFrame(
            [
                {
                    "stock_id": s.stock_id,
                    "ticker": s.ticker,
                    "name": s.name_kr,
                    "market": s.market,
                    "sector": s.sector,
                    "industry": s.industry,
                }
                for s in stocks
            ]
        )

        return df

    def load_price_data(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime,
        cache: bool = True,
    ) -> pd.DataFrame:
        """
        Load historical price data for multiple tickers

        Uses vectorized operations for efficient data loading and processing.

        Args:
            tickers: List of stock tickers
            start_date: Start date for historical data
            end_date: End date for historical data
            cache: Whether to cache the loaded data

        Returns:
            DataFrame with multi-index (date, ticker) and OHLCV columns
        """
        cache_key = f"prices_{','.join(sorted(tickers))}_{start_date}_{end_date}"
        if cache and cache_key in self._cache:
            return self._cache[cache_key].copy()

        # Get stock IDs
        stock_query = select(Stock).where(Stock.ticker.in_(tickers))
        stocks = self.db_session.execute(stock_query).scalars().all()
        stock_map = {s.ticker: s.stock_id for s in stocks}

        if not stock_map:
            return pd.DataFrame()

        # Load price data
        price_query = (
            select(StockPrice)
            .where(
                and_(
                    StockPrice.stock_id.in_(stock_map.values()),
                    StockPrice.date >= start_date,
                    StockPrice.date <= end_date,
                )
            )
            .order_by(StockPrice.date, StockPrice.stock_id)
        )

        result = self.db_session.execute(price_query)
        prices = result.scalars().all()

        # Convert to DataFrame using vectorized operations
        data = []
        ticker_reverse_map = {v: k for k, v in stock_map.items()}

        for p in prices:
            ticker = ticker_reverse_map.get(p.stock_id)
            if ticker:
                data.append(
                    {
                        "date": p.date,
                        "ticker": ticker,
                        "open": p.open,
                        "high": p.high,
                        "low": p.low,
                        "close": p.close,
                        "volume": p.volume,
                        "adjusted_close": p.adjusted_close or p.close,
                        "change_pct": p.change_pct or 0.0,
                    }
                )

        df = pd.DataFrame(data)

        if df.empty:
            return df

        # Set multi-index for efficient lookups
        df = df.set_index(["date", "ticker"]).sort_index()

        if cache:
            self._cache[cache_key] = df.copy()

        return df

    def load_technical_indicators(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime,
        cache: bool = True,
    ) -> pd.DataFrame:
        """
        Load technical indicators for multiple tickers

        Args:
            tickers: List of stock tickers
            start_date: Start date
            end_date: End date
            cache: Whether to cache the data

        Returns:
            DataFrame with multi-index (date, ticker) and technical indicator columns
        """
        cache_key = f"tech_{','.join(sorted(tickers))}_{start_date}_{end_date}"
        if cache and cache_key in self._cache:
            return self._cache[cache_key].copy()

        # Get stock IDs
        stock_query = select(Stock).where(Stock.ticker.in_(tickers))
        stocks = self.db_session.execute(stock_query).scalars().all()
        stock_map = {s.ticker: s.stock_id for s in stocks}

        if not stock_map:
            return pd.DataFrame()

        # Load technical indicators
        tech_query = (
            select(TechnicalIndicator)
            .where(
                and_(
                    TechnicalIndicator.stock_id.in_(stock_map.values()),
                    TechnicalIndicator.date >= start_date,
                    TechnicalIndicator.date <= end_date,
                )
            )
            .order_by(TechnicalIndicator.date, TechnicalIndicator.stock_id)
        )

        result = self.db_session.execute(tech_query)
        indicators = result.scalars().all()

        # Convert to DataFrame
        data = []
        ticker_reverse_map = {v: k for k, v in stock_map.items()}

        for ind in indicators:
            ticker = ticker_reverse_map.get(ind.stock_id)
            if ticker:
                data.append(
                    {
                        "date": ind.date,
                        "ticker": ticker,
                        "rsi_14": ind.rsi_14,
                        "macd": ind.macd,
                        "macd_signal": ind.macd_signal,
                        "macd_histogram": ind.macd_histogram,
                        "sma_20": ind.sma_20,
                        "sma_50": ind.sma_50,
                        "sma_200": ind.sma_200,
                        "ema_12": ind.ema_12,
                        "ema_26": ind.ema_26,
                        "bollinger_upper": ind.bollinger_upper,
                        "bollinger_middle": ind.bollinger_middle,
                        "bollinger_lower": ind.bollinger_lower,
                        "atr": ind.atr,
                        "adx": ind.adx,
                        "obv": ind.obv,
                        "volume_ma_20": ind.volume_ma_20,
                    }
                )

        df = pd.DataFrame(data)

        if df.empty:
            return df

        df = df.set_index(["date", "ticker"]).sort_index()

        if cache:
            self._cache[cache_key] = df.copy()

        return df

    def load_fundamental_indicators(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime,
        cache: bool = True,
    ) -> pd.DataFrame:
        """
        Load fundamental indicators for multiple tickers

        Args:
            tickers: List of stock tickers
            start_date: Start date
            end_date: End date
            cache: Whether to cache the data

        Returns:
            DataFrame with ticker as index and fundamental indicator columns
        """
        cache_key = f"fund_{','.join(sorted(tickers))}_{start_date}_{end_date}"
        if cache and cache_key in self._cache:
            return self._cache[cache_key].copy()

        # Get stock IDs
        stock_query = select(Stock).where(Stock.ticker.in_(tickers))
        stocks = self.db_session.execute(stock_query).scalars().all()
        stock_map = {s.ticker: s.stock_id for s in stocks}

        if not stock_map:
            return pd.DataFrame()

        # Load fundamental indicators
        fund_query = (
            select(FundamentalIndicator)
            .where(
                and_(
                    FundamentalIndicator.stock_id.in_(stock_map.values()),
                    FundamentalIndicator.report_date >= start_date,
                    FundamentalIndicator.report_date <= end_date,
                )
            )
            .order_by(FundamentalIndicator.report_date, FundamentalIndicator.stock_id)
        )

        result = self.db_session.execute(fund_query)
        fundamentals = result.scalars().all()

        # Convert to DataFrame
        data = []
        ticker_reverse_map = {v: k for k, v in stock_map.items()}

        for fund in fundamentals:
            ticker = ticker_reverse_map.get(fund.stock_id)
            if ticker:
                data.append(
                    {
                        "report_date": fund.report_date,
                        "ticker": ticker,
                        "per": fund.per,
                        "pbr": fund.pbr,
                        "psr": fund.psr,
                        "roe": fund.roe,
                        "roa": fund.roa,
                        "operating_margin": fund.operating_margin,
                        "net_margin": fund.net_margin,
                        "debt_ratio": fund.debt_ratio,
                        "debt_to_equity": fund.debt_to_equity,
                        "current_ratio": fund.current_ratio,
                        "revenue_growth": fund.revenue_growth,
                        "earnings_growth": fund.earnings_growth,
                        "dividend_yield": fund.dividend_yield,
                        "eps": fund.eps,
                        "bps": fund.bps,
                    }
                )

        df = pd.DataFrame(data)

        if df.empty:
            return df

        # Forward-fill fundamentals for each ticker (they update quarterly)
        df = df.set_index(["report_date", "ticker"]).sort_index()

        if cache:
            self._cache[cache_key] = df.copy()

        return df

    def load_composite_scores(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime,
        cache: bool = True,
    ) -> pd.DataFrame:
        """
        Load composite scores for multiple tickers

        Args:
            tickers: List of stock tickers
            start_date: Start date
            end_date: End date
            cache: Whether to cache the data

        Returns:
            DataFrame with multi-index (date, ticker) and score columns
        """
        cache_key = f"scores_{','.join(sorted(tickers))}_{start_date}_{end_date}"
        if cache and cache_key in self._cache:
            return self._cache[cache_key].copy()

        # Get stock IDs
        stock_query = select(Stock).where(Stock.ticker.in_(tickers))
        stocks = self.db_session.execute(stock_query).scalars().all()
        stock_map = {s.ticker: s.stock_id for s in stocks}

        if not stock_map:
            return pd.DataFrame()

        # Load composite scores
        score_query = (
            select(CompositeScore)
            .where(
                and_(
                    CompositeScore.stock_id.in_(stock_map.values()),
                    CompositeScore.date >= start_date,
                    CompositeScore.date <= end_date,
                )
            )
            .order_by(CompositeScore.date, CompositeScore.stock_id)
        )

        result = self.db_session.execute(score_query)
        scores = result.scalars().all()

        # Convert to DataFrame
        data = []
        ticker_reverse_map = {v: k for k, v in stock_map.items()}

        for score in scores:
            ticker = ticker_reverse_map.get(score.stock_id)
            if ticker:
                data.append(
                    {
                        "date": score.date,
                        "ticker": ticker,
                        "value_score": score.value_score,
                        "growth_score": score.growth_score,
                        "quality_score": score.quality_score,
                        "momentum_score": score.momentum_score,
                        "composite_score": score.composite_score,
                    }
                )

        df = pd.DataFrame(data)

        if df.empty:
            return df

        df = df.set_index(["date", "ticker"]).sort_index()

        if cache:
            self._cache[cache_key] = df.copy()

        return df

    def load_complete_dataset(
        self, tickers: List[str], start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """
        Load complete dataset with prices, indicators, and scores

        This method combines all data sources into a single DataFrame for efficient
        backtesting using vectorized operations.

        Args:
            tickers: List of stock tickers
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with multi-index (date, ticker) and all columns
        """
        # Load all data components
        prices = self.load_price_data(tickers, start_date, end_date)
        tech_ind = self.load_technical_indicators(tickers, start_date, end_date)
        scores = self.load_composite_scores(tickers, start_date, end_date)

        # Merge all dataframes
        if prices.empty:
            return pd.DataFrame()

        df = prices

        if not tech_ind.empty:
            df = df.join(tech_ind, how="left")

        if not scores.empty:
            df = df.join(scores, how="left")

        # Fill missing values with forward fill, then backward fill
        df = df.groupby(level="ticker").fillna(method="ffill").fillna(method="bfill")

        return df

    def get_trading_days(
        self, start_date: datetime, end_date: datetime
    ) -> List[datetime]:
        """
        Get list of trading days in the date range

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of trading days
        """
        query = (
            select(StockPrice.date)
            .where(and_(StockPrice.date >= start_date, StockPrice.date <= end_date))
            .distinct()
            .order_by(StockPrice.date)
        )

        result = self.db_session.execute(query)
        dates = [row[0] for row in result.all()]

        return dates

    def clear_cache(self):
        """Clear the data cache"""
        self._cache.clear()
