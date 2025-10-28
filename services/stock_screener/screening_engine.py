"""
Stock Screening Engine.
Implements comprehensive filtering logic for Korean stocks.
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from shared.database.models import (
    Stock, StockPrice, TechnicalIndicator, FundamentalIndicator, StabilityScore
)
from shared.configs.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class ScreeningCriteria:
    """Comprehensive criteria for screening stocks."""

    # Volatility filters
    max_volatility_pct: Optional[float] = None

    # Valuation filters
    max_per: Optional[float] = None
    max_pbr: Optional[float] = None
    min_per: Optional[float] = None
    min_pbr: Optional[float] = None

    # Financial health filters
    max_debt_ratio_pct: Optional[float] = None
    min_debt_ratio_pct: Optional[float] = None

    # Liquidity filters
    min_avg_volume: Optional[int] = None
    min_trading_value: Optional[float] = None

    # Undervalued stock identification
    undervalued_pbr_threshold: Optional[float] = None
    per_below_industry_avg: bool = False

    # Market filters
    markets: Optional[List[str]] = None  # KOSPI, KOSDAQ, KONEX
    sectors: Optional[List[str]] = None
    industries: Optional[List[str]] = None

    # Price filters
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None

    # Data quality filters
    min_price_history_days: int = 60
    min_volume_history_days: int = 20

    # Stability filters
    min_stability_score: Optional[float] = None
    max_stability_score: Optional[float] = None


@dataclass
class ScreeningResult:
    """Result of stock screening."""
    ticker: str
    name_kr: str
    market: str
    sector: Optional[str]
    industry: Optional[str]

    # Current metrics
    current_price: Optional[float]
    market_cap: Optional[float]

    # Valuation
    per: Optional[float]
    pbr: Optional[float]

    # Financial health
    debt_ratio: Optional[float]
    roe: Optional[float]

    # Liquidity
    avg_volume: Optional[float]
    avg_trading_value: Optional[float]

    # Volatility & Stability
    volatility_pct: Optional[float]
    stability_score: Optional[float]

    # Undervalued flags
    is_undervalued: bool = False
    undervalued_reasons: List[str] = None

    def __post_init__(self):
        if self.undervalued_reasons is None:
            self.undervalued_reasons = []


class StockScreeningEngine:
    """
    Comprehensive stock screening engine.
    Filters stocks based on volatility, valuation, financial health, and liquidity.
    """

    def __init__(self, db_session: Session, settings: Settings):
        """
        Initialize the screening engine.

        Args:
            db_session: Database session
            settings: Application settings
        """
        self.db = db_session
        self.settings = settings
        logger.info("Stock Screening Engine initialized")

    def screen_stocks(self, criteria: Optional[ScreeningCriteria] = None) -> List[ScreeningResult]:
        """
        Screen stocks based on given criteria.

        Args:
            criteria: Screening criteria (uses defaults from settings if None)

        Returns:
            List of screening results for stocks that pass all filters
        """
        if criteria is None:
            criteria = self._get_default_criteria()

        logger.info(f"Starting stock screening with criteria: {criteria}")

        # Get all active stocks
        stocks = self._get_active_stocks(criteria)
        logger.info(f"Found {len(stocks)} active stocks matching market/sector filters")

        results = []
        for stock in stocks:
            result = self._screen_single_stock(stock, criteria)
            if result:
                results.append(result)

        logger.info(f"Screening complete: {len(results)} stocks passed all filters")
        return results

    def identify_undervalued_stocks(
        self,
        criteria: Optional[ScreeningCriteria] = None
    ) -> List[ScreeningResult]:
        """
        Identify undervalued stocks.

        Args:
            criteria: Screening criteria (with undervalued flags enabled)

        Returns:
            List of undervalued stocks
        """
        if criteria is None:
            criteria = ScreeningCriteria(
                undervalued_pbr_threshold=self.settings.undervalued_pbr_threshold,
                per_below_industry_avg=True
            )

        results = self.screen_stocks(criteria)
        undervalued = [r for r in results if r.is_undervalued]

        logger.info(f"Found {len(undervalued)} undervalued stocks out of {len(results)}")
        return undervalued

    def _get_default_criteria(self) -> ScreeningCriteria:
        """Get default screening criteria from settings."""
        return ScreeningCriteria(
            max_volatility_pct=self.settings.max_volatility_pct,
            max_per=self.settings.max_per,
            max_pbr=self.settings.max_pbr,
            max_debt_ratio_pct=self.settings.max_debt_ratio_pct,
            min_avg_volume=self.settings.min_avg_volume,
            min_trading_value=self.settings.min_trading_value,
            undervalued_pbr_threshold=self.settings.undervalued_pbr_threshold,
            min_price_history_days=self.settings.min_price_history_days,
            min_volume_history_days=self.settings.min_volume_history_days
        )

    def _get_active_stocks(self, criteria: ScreeningCriteria) -> List[Stock]:
        """Get active stocks matching market/sector filters."""
        query = self.db.query(Stock).filter(Stock.is_active == True)

        # Market filter
        if criteria.markets:
            query = query.filter(Stock.market.in_(criteria.markets))

        # Sector filter
        if criteria.sectors:
            query = query.filter(Stock.sector.in_(criteria.sectors))

        # Industry filter
        if criteria.industries:
            query = query.filter(Stock.industry.in_(criteria.industries))

        # Market cap filters
        if criteria.min_market_cap is not None:
            query = query.filter(Stock.market_cap >= criteria.min_market_cap)
        if criteria.max_market_cap is not None:
            query = query.filter(Stock.market_cap <= criteria.max_market_cap)

        return query.all()

    def _screen_single_stock(
        self,
        stock: Stock,
        criteria: ScreeningCriteria
    ) -> Optional[ScreeningResult]:
        """
        Screen a single stock against all criteria.

        Args:
            stock: Stock to screen
            criteria: Screening criteria

        Returns:
            ScreeningResult if stock passes all filters, None otherwise
        """
        # Get latest data
        latest_price = self._get_latest_price(stock.id)
        if not latest_price:
            logger.debug(f"No price data for {stock.ticker}")
            return None

        # Check price filters
        if not self._check_price_filters(latest_price.close, criteria):
            return None

        # Check data quality
        if not self._check_data_quality(stock.id, criteria):
            return None

        # Get latest indicators
        fundamental = self._get_latest_fundamental(stock.id)
        stability = self._get_latest_stability(stock.id)

        # Calculate liquidity metrics
        liquidity_metrics = self._calculate_liquidity_metrics(stock.id, criteria)
        if liquidity_metrics is None:
            return None

        avg_volume, avg_trading_value = liquidity_metrics

        # Apply filters
        if not self._check_volatility_filter(stability, criteria):
            return None

        if not self._check_valuation_filters(fundamental, criteria):
            return None

        if not self._check_financial_health_filters(fundamental, criteria):
            return None

        if not self._check_liquidity_filters(avg_volume, avg_trading_value, criteria):
            return None

        if not self._check_stability_filters(stability, criteria):
            return None

        # Check if undervalued
        is_undervalued, reasons = self._check_undervalued(
            stock, fundamental, criteria
        )

        # Build result
        result = ScreeningResult(
            ticker=stock.ticker,
            name_kr=stock.name_kr,
            market=stock.market,
            sector=stock.sector,
            industry=stock.industry,
            current_price=latest_price.close,
            market_cap=stock.market_cap,
            per=fundamental.per if fundamental else None,
            pbr=fundamental.pbr if fundamental else None,
            debt_ratio=fundamental.debt_ratio if fundamental else None,
            roe=fundamental.roe if fundamental else None,
            avg_volume=avg_volume,
            avg_trading_value=avg_trading_value,
            volatility_pct=stability.price_volatility * 100 if stability and stability.price_volatility else None,
            stability_score=stability.stability_score if stability else None,
            is_undervalued=is_undervalued,
            undervalued_reasons=reasons
        )

        return result

    def _get_latest_price(self, stock_id: int) -> Optional[StockPrice]:
        """Get the latest price for a stock."""
        return (
            self.db.query(StockPrice)
            .filter(StockPrice.stock_id == stock_id)
            .order_by(StockPrice.date.desc())
            .first()
        )

    def _get_latest_fundamental(self, stock_id: int) -> Optional[FundamentalIndicator]:
        """Get the latest fundamental indicators for a stock."""
        return (
            self.db.query(FundamentalIndicator)
            .filter(FundamentalIndicator.stock_id == stock_id)
            .order_by(FundamentalIndicator.date.desc())
            .first()
        )

    def _get_latest_stability(self, stock_id: int) -> Optional[StabilityScore]:
        """Get the latest stability score for a stock."""
        return (
            self.db.query(StabilityScore)
            .filter(StabilityScore.stock_id == stock_id)
            .order_by(StabilityScore.date.desc())
            .first()
        )

    def _check_data_quality(self, stock_id: int, criteria: ScreeningCriteria) -> bool:
        """Check if stock has sufficient historical data."""
        # Check price history
        min_price_date = datetime.now() - timedelta(days=criteria.min_price_history_days)
        price_count = (
            self.db.query(func.count(StockPrice.id))
            .filter(
                StockPrice.stock_id == stock_id,
                StockPrice.date >= min_price_date
            )
            .scalar()
        )

        if price_count < criteria.min_price_history_days * 0.8:  # Allow 20% tolerance
            return False

        # Check volume history
        min_volume_date = datetime.now() - timedelta(days=criteria.min_volume_history_days)
        volume_count = (
            self.db.query(func.count(StockPrice.id))
            .filter(
                StockPrice.stock_id == stock_id,
                StockPrice.date >= min_volume_date,
                StockPrice.volume > 0
            )
            .scalar()
        )

        if volume_count < criteria.min_volume_history_days * 0.8:  # Allow 20% tolerance
            return False

        return True

    def _calculate_liquidity_metrics(
        self,
        stock_id: int,
        criteria: ScreeningCriteria
    ) -> Optional[Tuple[float, float]]:
        """
        Calculate average volume and trading value.

        Returns:
            Tuple of (avg_volume, avg_trading_value) or None if insufficient data
        """
        lookback_date = datetime.now() - timedelta(days=criteria.min_volume_history_days)

        result = (
            self.db.query(
                func.avg(StockPrice.volume).label('avg_volume'),
                func.avg(StockPrice.trading_value).label('avg_trading_value')
            )
            .filter(
                StockPrice.stock_id == stock_id,
                StockPrice.date >= lookback_date
            )
            .first()
        )

        if result and result.avg_volume:
            return (float(result.avg_volume), float(result.avg_trading_value or 0))
        return None

    def _check_price_filters(self, price: float, criteria: ScreeningCriteria) -> bool:
        """Check if price is within specified range."""
        if criteria.min_price is not None and price < criteria.min_price:
            return False
        if criteria.max_price is not None and price > criteria.max_price:
            return False
        return True

    def _check_volatility_filter(
        self,
        stability: Optional[StabilityScore],
        criteria: ScreeningCriteria
    ) -> bool:
        """Filter out high volatility stocks."""
        if criteria.max_volatility_pct is None:
            return True

        if not stability or stability.price_volatility is None:
            # If no stability data, be conservative and filter out
            return False

        volatility_pct = stability.price_volatility * 100
        return volatility_pct <= criteria.max_volatility_pct

    def _check_valuation_filters(
        self,
        fundamental: Optional[FundamentalIndicator],
        criteria: ScreeningCriteria
    ) -> bool:
        """Filter out overvalued stocks."""
        if not fundamental:
            # If no fundamental data, filter out for safety
            return False

        # PER filter
        if criteria.max_per is not None:
            if fundamental.per is None or fundamental.per > criteria.max_per:
                return False

        if criteria.min_per is not None:
            if fundamental.per is None or fundamental.per < criteria.min_per:
                return False

        # PBR filter
        if criteria.max_pbr is not None:
            if fundamental.pbr is None or fundamental.pbr > criteria.max_pbr:
                return False

        if criteria.min_pbr is not None:
            if fundamental.pbr is None or fundamental.pbr < criteria.min_pbr:
                return False

        return True

    def _check_financial_health_filters(
        self,
        fundamental: Optional[FundamentalIndicator],
        criteria: ScreeningCriteria
    ) -> bool:
        """Filter out financially unstable companies."""
        if not fundamental:
            return False

        # Debt ratio filter
        if criteria.max_debt_ratio_pct is not None:
            if fundamental.debt_ratio is None:
                return False
            if fundamental.debt_ratio > criteria.max_debt_ratio_pct:
                return False

        if criteria.min_debt_ratio_pct is not None:
            if fundamental.debt_ratio is None:
                return False
            if fundamental.debt_ratio < criteria.min_debt_ratio_pct:
                return False

        return True

    def _check_liquidity_filters(
        self,
        avg_volume: float,
        avg_trading_value: float,
        criteria: ScreeningCriteria
    ) -> bool:
        """Filter out low liquidity stocks."""
        # Volume filter
        if criteria.min_avg_volume is not None:
            if avg_volume < criteria.min_avg_volume:
                return False

        # Trading value filter
        if criteria.min_trading_value is not None:
            if avg_trading_value < criteria.min_trading_value:
                return False

        return True

    def _check_stability_filters(
        self,
        stability: Optional[StabilityScore],
        criteria: ScreeningCriteria
    ) -> bool:
        """Filter by stability score range."""
        if criteria.min_stability_score is not None:
            if not stability or stability.stability_score is None:
                return False
            if stability.stability_score < criteria.min_stability_score:
                return False

        if criteria.max_stability_score is not None:
            if not stability or stability.stability_score is None:
                return False
            if stability.stability_score > criteria.max_stability_score:
                return False

        return True

    def _check_undervalued(
        self,
        stock: Stock,
        fundamental: Optional[FundamentalIndicator],
        criteria: ScreeningCriteria
    ) -> Tuple[bool, List[str]]:
        """
        Check if stock is undervalued.

        Returns:
            Tuple of (is_undervalued, reasons)
        """
        reasons = []

        if not fundamental:
            return False, reasons

        # Check PBR threshold
        if criteria.undervalued_pbr_threshold is not None:
            if fundamental.pbr is not None and fundamental.pbr < criteria.undervalued_pbr_threshold:
                reasons.append(f"PBR {fundamental.pbr:.2f} < {criteria.undervalued_pbr_threshold}")

        # Check PER vs industry average
        if criteria.per_below_industry_avg and fundamental.per is not None:
            industry_avg_per = self._get_industry_average_per(stock.industry)
            if industry_avg_per and fundamental.per < industry_avg_per * self.settings.per_industry_avg_multiplier:
                reasons.append(
                    f"PER {fundamental.per:.2f} < Industry Avg {industry_avg_per:.2f}"
                )

        return len(reasons) > 0, reasons

    def _get_industry_average_per(self, industry: Optional[str]) -> Optional[float]:
        """Calculate average PER for an industry."""
        if not industry:
            return None

        result = (
            self.db.query(func.avg(FundamentalIndicator.per))
            .join(Stock, FundamentalIndicator.stock_id == Stock.id)
            .filter(
                Stock.industry == industry,
                Stock.is_active == True,
                FundamentalIndicator.per.isnot(None),
                FundamentalIndicator.per > 0,
                FundamentalIndicator.per < 100  # Exclude outliers
            )
            .scalar()
        )

        return float(result) if result else None

    def get_screening_summary(self, results: List[ScreeningResult]) -> Dict:
        """
        Generate summary statistics for screening results.

        Args:
            results: List of screening results

        Returns:
            Dictionary with summary statistics
        """
        if not results:
            return {
                "total_stocks": 0,
                "undervalued_count": 0,
                "markets": {},
                "sectors": {}
            }

        markets = {}
        sectors = {}
        undervalued_count = 0

        for result in results:
            # Count by market
            markets[result.market] = markets.get(result.market, 0) + 1

            # Count by sector
            if result.sector:
                sectors[result.sector] = sectors.get(result.sector, 0) + 1

            # Count undervalued
            if result.is_undervalued:
                undervalued_count += 1

        return {
            "total_stocks": len(results),
            "undervalued_count": undervalued_count,
            "markets": markets,
            "sectors": sectors,
            "avg_per": sum(r.per for r in results if r.per) / len([r for r in results if r.per]) if any(r.per for r in results) else None,
            "avg_pbr": sum(r.pbr for r in results if r.pbr) / len([r for r in results if r.pbr]) if any(r.pbr for r in results) else None,
            "avg_debt_ratio": sum(r.debt_ratio for r in results if r.debt_ratio) / len([r for r in results if r.debt_ratio]) if any(r.debt_ratio for r in results) else None,
        }
