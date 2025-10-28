"""
Watchlist Manager for tracking and managing stock watchlists.

This module provides comprehensive watchlist management functionality including:
- Adding stocks to watchlist with automatic reason generation
- Daily updates of scores and metrics
- Auto-removal of stocks not meeting criteria
- Historical performance tracking
- Export to CSV/JSON formats
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import json
import csv
import logging
from pathlib import Path

from shared.database.models import (
    Stock, Watchlist, WatchlistHistory, StockPrice, CompositeScore,
    StabilityScore, FundamentalIndicator, TechnicalIndicator
)
from services.stock_screener.screening_engine import StockScreeningEngine, ScreeningCriteria

logger = logging.getLogger(__name__)


class WatchlistManager:
    """
    Manages stock watchlists with comprehensive tracking and analysis.
    """

    def __init__(self, db_session: Session, user_id: str = "default"):
        """
        Initialize the watchlist manager.

        Args:
            db_session: SQLAlchemy database session
            user_id: User identifier for watchlist isolation
        """
        self.db = db_session
        self.user_id = user_id
        self.screening_engine = StockScreeningEngine(db_session)

    def add_to_watchlist(
        self,
        ticker: str,
        target_price: Optional[float] = None,
        custom_reason: Optional[str] = None,
        tags: Optional[str] = None,
        notes: Optional[str] = None,
        alert_enabled: bool = False,
        alert_price_upper: Optional[float] = None,
        alert_price_lower: Optional[float] = None
    ) -> Optional[Watchlist]:
        """
        Add a stock to the watchlist with automatic reason generation.

        Args:
            ticker: Stock ticker code
            target_price: Optional target price for the stock
            custom_reason: Custom reason (if not provided, auto-generated)
            tags: Comma-separated tags
            notes: Additional notes
            alert_enabled: Enable price alerts
            alert_price_upper: Alert if price exceeds this
            alert_price_lower: Alert if price falls below this

        Returns:
            Watchlist entry or None if stock not found
        """
        # Get stock information
        stock = self.db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            logger.error(f"Stock {ticker} not found in database")
            return None

        # Check if already in watchlist
        existing = self.db.query(Watchlist).filter(
            and_(
                Watchlist.user_id == self.user_id,
                Watchlist.ticker == ticker,
                Watchlist.is_active == True
            )
        ).first()

        if existing:
            logger.warning(f"Stock {ticker} already in watchlist")
            return existing

        # Get latest data for reason generation
        latest_price = self.db.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).order_by(desc(StockPrice.date)).first()

        latest_score = self.db.query(CompositeScore).filter(
            CompositeScore.stock_id == stock.id
        ).order_by(desc(CompositeScore.date)).first()

        latest_stability = self.db.query(StabilityScore).filter(
            StabilityScore.stock_id == stock.id
        ).order_by(desc(StabilityScore.date)).first()

        latest_fundamental = self.db.query(FundamentalIndicator).filter(
            FundamentalIndicator.stock_id == stock.id
        ).order_by(desc(FundamentalIndicator.date)).first()

        # Generate reason if not provided
        reason = custom_reason
        if not reason:
            reason = self._generate_reason(
                stock, latest_price, latest_score,
                latest_stability, latest_fundamental
            )

        # Calculate score (use composite score if available)
        score = latest_score.composite_score if latest_score else None

        # Create watchlist entry
        watchlist_entry = Watchlist(
            stock_id=stock.id,
            user_id=self.user_id,
            ticker=ticker,
            reason=reason,
            score=score,
            target_price=Decimal(str(target_price)) if target_price else None,
            notes=notes,
            tags=tags,
            alert_enabled=alert_enabled,
            alert_price_upper=Decimal(str(alert_price_upper)) if alert_price_upper else None,
            alert_price_lower=Decimal(str(alert_price_lower)) if alert_price_lower else None,
            is_active=True,
            added_date=datetime.utcnow()
        )

        self.db.add(watchlist_entry)
        self.db.commit()
        self.db.refresh(watchlist_entry)

        # Create initial history snapshot
        self._create_history_snapshot(
            watchlist_entry,
            latest_price,
            latest_score,
            latest_stability,
            latest_fundamental,
            snapshot_reason="added"
        )

        logger.info(f"Added {ticker} to watchlist (ID: {watchlist_entry.id})")
        return watchlist_entry

    def _generate_reason(
        self,
        stock: Stock,
        price: Optional[StockPrice],
        score: Optional[CompositeScore],
        stability: Optional[StabilityScore],
        fundamental: Optional[FundamentalIndicator]
    ) -> str:
        """
        Generate automatic reason for adding stock to watchlist.

        Args:
            stock: Stock model
            price: Latest price data
            score: Latest composite score
            stability: Latest stability score
            fundamental: Latest fundamental data

        Returns:
            Generated reason string
        """
        reasons = []

        # Score-based reasons
        if score:
            if score.composite_score >= 80:
                reasons.append(f"Excellent composite score ({score.composite_score:.1f}/100)")
            elif score.composite_score >= 70:
                reasons.append(f"Strong composite score ({score.composite_score:.1f}/100)")

            if score.value_score and score.value_score >= 75:
                reasons.append(f"Undervalued (Value Score: {score.value_score:.1f})")

            if score.growth_score and score.growth_score >= 75:
                reasons.append(f"High growth potential (Growth Score: {score.growth_score:.1f})")

            if score.quality_score and score.quality_score >= 75:
                reasons.append(f"High quality fundamentals (Quality Score: {score.quality_score:.1f})")

            if score.momentum_score and score.momentum_score >= 75:
                reasons.append(f"Strong momentum (Momentum Score: {score.momentum_score:.1f})")

        # Stability-based reasons
        if stability and stability.stability_score >= 70:
            reasons.append(f"Stable investment (Stability Score: {stability.stability_score:.1f})")

        # Fundamental-based reasons
        if fundamental:
            if fundamental.per and 0 < fundamental.per < 10:
                reasons.append(f"Low PER ({fundamental.per:.1f})")

            if fundamental.pbr and 0 < fundamental.pbr < 1.0:
                reasons.append(f"Trading below book value (PBR: {fundamental.pbr:.2f})")

            if fundamental.roe and fundamental.roe > 20:
                reasons.append(f"High ROE ({fundamental.roe:.1f}%)")

            if fundamental.dividend_yield and fundamental.dividend_yield > 4:
                reasons.append(f"High dividend yield ({fundamental.dividend_yield:.1f}%)")

        # If no specific reasons found, provide generic one
        if not reasons:
            reasons.append(f"Added for monitoring {stock.market} stock in {stock.sector or 'general'} sector")

        return "; ".join(reasons)

    def update_watchlist_daily(self) -> Dict[str, Any]:
        """
        Update all watchlist entries with new scores and create history snapshots.

        Returns:
            Dictionary with update statistics
        """
        active_entries = self.db.query(Watchlist).filter(
            and_(
                Watchlist.user_id == self.user_id,
                Watchlist.is_active == True
            )
        ).all()

        stats = {
            'total_entries': len(active_entries),
            'updated': 0,
            'failed': 0,
            'removed': 0,
            'errors': []
        }

        for entry in active_entries:
            try:
                # Get latest data
                latest_price = self.db.query(StockPrice).filter(
                    StockPrice.stock_id == entry.stock_id
                ).order_by(desc(StockPrice.date)).first()

                latest_score = self.db.query(CompositeScore).filter(
                    CompositeScore.stock_id == entry.stock_id
                ).order_by(desc(CompositeScore.date)).first()

                latest_stability = self.db.query(StabilityScore).filter(
                    StabilityScore.stock_id == entry.stock_id
                ).order_by(desc(StabilityScore.date)).first()

                latest_fundamental = self.db.query(FundamentalIndicator).filter(
                    FundamentalIndicator.stock_id == entry.stock_id
                ).order_by(desc(FundamentalIndicator.date)).first()

                # Update score
                if latest_score:
                    entry.score = latest_score.composite_score
                    entry.updated_at = datetime.utcnow()

                # Create history snapshot
                self._create_history_snapshot(
                    entry,
                    latest_price,
                    latest_score,
                    latest_stability,
                    latest_fundamental,
                    snapshot_reason="daily_update"
                )

                stats['updated'] += 1

            except Exception as e:
                logger.error(f"Failed to update watchlist entry {entry.id}: {str(e)}")
                stats['failed'] += 1
                stats['errors'].append({
                    'ticker': entry.ticker,
                    'error': str(e)
                })

        self.db.commit()
        logger.info(f"Daily watchlist update completed: {stats}")
        return stats

    def remove_stocks_not_meeting_criteria(
        self,
        criteria: ScreeningCriteria
    ) -> Dict[str, Any]:
        """
        Remove stocks from watchlist that no longer meet specified criteria.

        Args:
            criteria: Screening criteria to check against

        Returns:
            Dictionary with removal statistics
        """
        active_entries = self.db.query(Watchlist).filter(
            and_(
                Watchlist.user_id == self.user_id,
                Watchlist.is_active == True
            )
        ).all()

        stats = {
            'total_checked': len(active_entries),
            'removed': 0,
            'kept': 0,
            'details': []
        }

        for entry in active_entries:
            try:
                # Check if stock meets criteria
                violations = self._check_criteria_violations(entry.stock_id, criteria)

                if violations:
                    # Mark as inactive instead of deleting
                    entry.is_active = False
                    entry.notes = (entry.notes or "") + f"\n[Auto-removed {datetime.utcnow().date()}]: " + "; ".join(violations)
                    entry.updated_at = datetime.utcnow()

                    stats['removed'] += 1
                    stats['details'].append({
                        'ticker': entry.ticker,
                        'reason': violations
                    })

                    logger.info(f"Removed {entry.ticker} from watchlist: {violations}")
                else:
                    stats['kept'] += 1

            except Exception as e:
                logger.error(f"Failed to check criteria for {entry.ticker}: {str(e)}")

        self.db.commit()
        logger.info(f"Criteria check completed: {stats}")
        return stats

    def _check_criteria_violations(
        self,
        stock_id: int,
        criteria: ScreeningCriteria
    ) -> List[str]:
        """
        Check if a stock violates any screening criteria.

        Args:
            stock_id: Stock ID to check
            criteria: Screening criteria

        Returns:
            List of violation messages (empty if no violations)
        """
        violations = []

        # Get latest data
        latest_price = self.db.query(StockPrice).filter(
            StockPrice.stock_id == stock_id
        ).order_by(desc(StockPrice.date)).first()

        latest_fundamental = self.db.query(FundamentalIndicator).filter(
            FundamentalIndicator.stock_id == stock_id
        ).order_by(desc(FundamentalIndicator.date)).first()

        latest_stability = self.db.query(StabilityScore).filter(
            StabilityScore.stock_id == stock_id
        ).order_by(desc(StabilityScore.date)).first()

        # Check volatility
        if criteria.max_volatility_pct and latest_stability:
            if latest_stability.price_volatility and latest_stability.price_volatility > criteria.max_volatility_pct:
                violations.append(f"Volatility too high: {latest_stability.price_volatility:.1f}% > {criteria.max_volatility_pct}%")

        # Check valuation
        if latest_fundamental:
            if criteria.max_per and latest_fundamental.per:
                if latest_fundamental.per > criteria.max_per:
                    violations.append(f"PER too high: {latest_fundamental.per:.1f} > {criteria.max_per}")

            if criteria.max_pbr and latest_fundamental.pbr:
                if latest_fundamental.pbr > criteria.max_pbr:
                    violations.append(f"PBR too high: {latest_fundamental.pbr:.2f} > {criteria.max_pbr}")

            if criteria.max_debt_ratio_pct and latest_fundamental.debt_ratio:
                if latest_fundamental.debt_ratio > criteria.max_debt_ratio_pct:
                    violations.append(f"Debt ratio too high: {latest_fundamental.debt_ratio:.1f}% > {criteria.max_debt_ratio_pct}%")

        # Check liquidity
        if latest_price:
            if criteria.min_avg_volume:
                avg_volume = self._get_average_volume(stock_id, days=20)
                if avg_volume and avg_volume < criteria.min_avg_volume:
                    violations.append(f"Volume too low: {avg_volume:,.0f} < {criteria.min_avg_volume:,.0f}")

        return violations

    def _get_average_volume(self, stock_id: int, days: int = 20) -> Optional[float]:
        """Get average trading volume for a stock."""
        result = self.db.query(func.avg(StockPrice.volume)).filter(
            and_(
                StockPrice.stock_id == stock_id,
                StockPrice.date >= datetime.utcnow() - timedelta(days=days)
            )
        ).scalar()

        return float(result) if result else None

    def _create_history_snapshot(
        self,
        watchlist_entry: Watchlist,
        price: Optional[StockPrice],
        score: Optional[CompositeScore],
        stability: Optional[StabilityScore],
        fundamental: Optional[FundamentalIndicator],
        snapshot_reason: str = "daily_update"
    ) -> Optional[WatchlistHistory]:
        """
        Create a historical snapshot of watchlist stock performance.

        Args:
            watchlist_entry: Watchlist entry to snapshot
            price: Latest price data
            score: Latest composite score
            stability: Latest stability score
            fundamental: Latest fundamental data
            snapshot_reason: Reason for snapshot

        Returns:
            Created history entry or None
        """
        if not price:
            logger.warning(f"No price data available for snapshot of {watchlist_entry.ticker}")
            return None

        # Get price when added to watchlist
        added_price = self.db.query(StockPrice).filter(
            and_(
                StockPrice.stock_id == watchlist_entry.stock_id,
                StockPrice.date <= watchlist_entry.added_date
            )
        ).order_by(desc(StockPrice.date)).first()

        # Calculate price changes
        price_change_pct = None
        price_change_amount = None
        if added_price and added_price.close:
            price_change_amount = float(price.close - added_price.close)
            price_change_pct = (price_change_amount / float(added_price.close)) * 100

        # Calculate target price distance
        target_price_distance_pct = None
        if watchlist_entry.target_price and price.close:
            target_price_distance_pct = (
                (float(watchlist_entry.target_price - price.close) / float(price.close)) * 100
            )

        # Get previous snapshot for score changes
        previous_snapshot = self.db.query(WatchlistHistory).filter(
            WatchlistHistory.watchlist_id == watchlist_entry.id
        ).order_by(desc(WatchlistHistory.date)).first()

        # Calculate score changes
        composite_score_change = None
        value_score_change = None
        growth_score_change = None
        quality_score_change = None
        momentum_score_change = None

        if score and previous_snapshot:
            if previous_snapshot.composite_score:
                composite_score_change = score.composite_score - previous_snapshot.composite_score
            if score.value_score and previous_snapshot.value_score:
                value_score_change = score.value_score - previous_snapshot.value_score
            if score.growth_score and previous_snapshot.growth_score:
                growth_score_change = score.growth_score - previous_snapshot.growth_score
            if score.quality_score and previous_snapshot.quality_score:
                quality_score_change = score.quality_score - previous_snapshot.quality_score
            if score.momentum_score and previous_snapshot.momentum_score:
                momentum_score_change = score.momentum_score - previous_snapshot.momentum_score

        # Calculate performance metrics
        days_on_watchlist = (datetime.utcnow() - watchlist_entry.added_date).days
        total_return_pct = price_change_pct
        annualized_return_pct = None
        if total_return_pct and days_on_watchlist > 0:
            annualized_return_pct = (total_return_pct / days_on_watchlist) * 365

        # Get technical indicators
        latest_technical = self.db.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_id == watchlist_entry.stock_id
        ).order_by(desc(TechnicalIndicator.date)).first()

        # Create history entry
        history = WatchlistHistory(
            watchlist_id=watchlist_entry.id,
            stock_id=watchlist_entry.stock_id,
            date=datetime.utcnow(),

            # Price information
            price=price.close,
            price_change_pct=price_change_pct,
            price_change_amount=Decimal(str(price_change_amount)) if price_change_amount else None,
            target_price=watchlist_entry.target_price,
            target_price_distance_pct=target_price_distance_pct,

            # Volume
            volume=price.volume,
            trading_value=price.trading_value,

            # Scores
            composite_score=score.composite_score if score else None,
            value_score=score.value_score if score else None,
            growth_score=score.growth_score if score else None,
            quality_score=score.quality_score if score else None,
            momentum_score=score.momentum_score if score else None,
            percentile_rank=score.percentile_rank if score else None,

            # Score changes
            composite_score_change=composite_score_change,
            value_score_change=value_score_change,
            growth_score_change=growth_score_change,
            quality_score_change=quality_score_change,
            momentum_score_change=momentum_score_change,

            # Stability
            stability_score=stability.stability_score if stability else None,
            price_volatility=stability.price_volatility if stability else None,
            beta=stability.beta if stability else None,

            # Fundamentals
            per=fundamental.per if fundamental else None,
            pbr=fundamental.pbr if fundamental else None,
            roe=fundamental.roe if fundamental else None,
            debt_ratio=fundamental.debt_ratio if fundamental else None,
            dividend_yield=fundamental.dividend_yield if fundamental else None,

            # Technical indicators
            rsi_14=latest_technical.rsi_14 if latest_technical else None,
            macd=latest_technical.macd if latest_technical else None,
            macd_histogram=latest_technical.macd_histogram if latest_technical else None,

            # Performance metrics
            days_on_watchlist=days_on_watchlist,
            total_return_pct=total_return_pct,
            annualized_return_pct=annualized_return_pct,

            # Metadata
            snapshot_reason=snapshot_reason,
            meets_criteria=True  # Will be updated by criteria check
        )

        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)

        return history

    def get_watchlist(
        self,
        include_inactive: bool = False,
        sort_by: str = "score",
        ascending: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all watchlist entries for the user.

        Args:
            include_inactive: Include inactive entries
            sort_by: Field to sort by (score, added_date, ticker, price_change)
            ascending: Sort in ascending order

        Returns:
            List of watchlist entries with enriched data
        """
        query = self.db.query(Watchlist).filter(Watchlist.user_id == self.user_id)

        if not include_inactive:
            query = query.filter(Watchlist.is_active == True)

        # Apply sorting
        if sort_by == "score":
            query = query.order_by(Watchlist.score.desc() if not ascending else Watchlist.score)
        elif sort_by == "added_date":
            query = query.order_by(Watchlist.added_date.desc() if not ascending else Watchlist.added_date)
        elif sort_by == "ticker":
            query = query.order_by(Watchlist.ticker.asc() if ascending else Watchlist.ticker.desc())

        entries = query.all()

        # Enrich with latest data
        result = []
        for entry in entries:
            enriched = self._enrich_watchlist_entry(entry)
            result.append(enriched)

        # Sort by price_change if requested (calculated field)
        if sort_by == "price_change":
            result.sort(
                key=lambda x: x.get('price_change_pct', 0) or 0,
                reverse=not ascending
            )

        return result

    def _enrich_watchlist_entry(self, entry: Watchlist) -> Dict[str, Any]:
        """
        Enrich watchlist entry with latest data and performance metrics.

        Args:
            entry: Watchlist entry

        Returns:
            Enriched dictionary with all relevant data
        """
        # Get stock info
        stock = self.db.query(Stock).filter(Stock.id == entry.stock_id).first()

        # Get latest price
        latest_price = self.db.query(StockPrice).filter(
            StockPrice.stock_id == entry.stock_id
        ).order_by(desc(StockPrice.date)).first()

        # Get latest history snapshot
        latest_history = self.db.query(WatchlistHistory).filter(
            WatchlistHistory.watchlist_id == entry.id
        ).order_by(desc(WatchlistHistory.date)).first()

        # Build enriched data
        enriched = {
            'id': entry.id,
            'ticker': entry.ticker,
            'name': stock.name_kr if stock else None,
            'market': stock.market if stock else None,
            'sector': stock.sector if stock else None,
            'reason': entry.reason,
            'score': entry.score,
            'target_price': float(entry.target_price) if entry.target_price else None,
            'notes': entry.notes,
            'tags': entry.tags,
            'is_active': entry.is_active,
            'added_date': entry.added_date.isoformat() if entry.added_date else None,
            'days_on_watchlist': (datetime.utcnow() - entry.added_date).days if entry.added_date else None,

            # Latest price info
            'current_price': float(latest_price.close) if latest_price else None,
            'price_change_pct': latest_history.price_change_pct if latest_history else None,
            'total_return_pct': latest_history.total_return_pct if latest_history else None,
            'annualized_return_pct': latest_history.annualized_return_pct if latest_history else None,

            # Latest scores
            'composite_score': latest_history.composite_score if latest_history else entry.score,
            'value_score': latest_history.value_score if latest_history else None,
            'growth_score': latest_history.growth_score if latest_history else None,
            'quality_score': latest_history.quality_score if latest_history else None,
            'momentum_score': latest_history.momentum_score if latest_history else None,
            'stability_score': latest_history.stability_score if latest_history else None,

            # Alert settings
            'alert_enabled': entry.alert_enabled,
            'alert_price_upper': float(entry.alert_price_upper) if entry.alert_price_upper else None,
            'alert_price_lower': float(entry.alert_price_lower) if entry.alert_price_lower else None,

            # Metadata
            'last_updated': entry.updated_at.isoformat() if entry.updated_at else None,
        }

        return enriched

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get overall performance summary of watchlist.

        Returns:
            Dictionary with performance statistics
        """
        active_entries = self.db.query(Watchlist).filter(
            and_(
                Watchlist.user_id == self.user_id,
                Watchlist.is_active == True
            )
        ).all()

        total_stocks = len(active_entries)

        # Get latest history for each
        returns = []
        scores = []

        for entry in active_entries:
            latest_history = self.db.query(WatchlistHistory).filter(
                WatchlistHistory.watchlist_id == entry.id
            ).order_by(desc(WatchlistHistory.date)).first()

            if latest_history:
                if latest_history.total_return_pct is not None:
                    returns.append(latest_history.total_return_pct)
                if latest_history.composite_score is not None:
                    scores.append(latest_history.composite_score)

        return {
            'total_stocks': total_stocks,
            'average_return_pct': sum(returns) / len(returns) if returns else 0,
            'best_return_pct': max(returns) if returns else 0,
            'worst_return_pct': min(returns) if returns else 0,
            'average_score': sum(scores) / len(scores) if scores else 0,
            'stocks_with_positive_return': len([r for r in returns if r > 0]),
            'stocks_with_negative_return': len([r for r in returns if r < 0]),
        }

    def export_to_csv(self, filepath: str) -> bool:
        """
        Export watchlist to CSV file.

        Args:
            filepath: Output CSV file path

        Returns:
            True if successful
        """
        try:
            entries = self.get_watchlist(include_inactive=False)

            if not entries:
                logger.warning("No watchlist entries to export")
                return False

            # Define CSV columns
            fieldnames = [
                'ticker', 'name', 'market', 'sector', 'current_price',
                'target_price', 'price_change_pct', 'total_return_pct',
                'composite_score', 'value_score', 'growth_score',
                'quality_score', 'momentum_score', 'stability_score',
                'days_on_watchlist', 'reason', 'tags', 'notes', 'added_date'
            ]

            # Write CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for entry in entries:
                    # Filter only the fields we want
                    row = {k: entry.get(k, '') for k in fieldnames}
                    writer.writerow(row)

            logger.info(f"Exported {len(entries)} watchlist entries to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to export watchlist to CSV: {str(e)}")
            return False

    def export_to_json(self, filepath: str, include_history: bool = False) -> bool:
        """
        Export watchlist to JSON file.

        Args:
            filepath: Output JSON file path
            include_history: Include historical snapshots

        Returns:
            True if successful
        """
        try:
            entries = self.get_watchlist(include_inactive=False)

            if not entries:
                logger.warning("No watchlist entries to export")
                return False

            # Add history if requested
            if include_history:
                for entry in entries:
                    history = self.db.query(WatchlistHistory).filter(
                        WatchlistHistory.watchlist_id == entry['id']
                    ).order_by(desc(WatchlistHistory.date)).all()

                    entry['history'] = [
                        {
                            'date': h.date.isoformat(),
                            'price': float(h.price) if h.price else None,
                            'composite_score': h.composite_score,
                            'total_return_pct': h.total_return_pct,
                            'meets_criteria': h.meets_criteria,
                            'snapshot_reason': h.snapshot_reason
                        }
                        for h in history
                    ]

            # Write JSON
            export_data = {
                'export_date': datetime.utcnow().isoformat(),
                'user_id': self.user_id,
                'total_stocks': len(entries),
                'watchlist': entries
            }

            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)

            logger.info(f"Exported {len(entries)} watchlist entries to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to export watchlist to JSON: {str(e)}")
            return False

    def remove_from_watchlist(self, ticker: str, permanently: bool = False) -> bool:
        """
        Remove a stock from the watchlist.

        Args:
            ticker: Stock ticker to remove
            permanently: If True, delete the entry; if False, mark as inactive

        Returns:
            True if successful
        """
        entry = self.db.query(Watchlist).filter(
            and_(
                Watchlist.user_id == self.user_id,
                Watchlist.ticker == ticker,
                Watchlist.is_active == True
            )
        ).first()

        if not entry:
            logger.warning(f"Stock {ticker} not found in active watchlist")
            return False

        if permanently:
            self.db.delete(entry)
            logger.info(f"Permanently deleted {ticker} from watchlist")
        else:
            entry.is_active = False
            entry.updated_at = datetime.utcnow()
            logger.info(f"Marked {ticker} as inactive in watchlist")

        self.db.commit()
        return True

    def get_historical_performance(
        self,
        ticker: str,
        days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical performance data for a watchlist stock.

        Args:
            ticker: Stock ticker
            days: Number of days to retrieve (None for all)

        Returns:
            List of historical snapshots
        """
        entry = self.db.query(Watchlist).filter(
            and_(
                Watchlist.user_id == self.user_id,
                Watchlist.ticker == ticker
            )
        ).first()

        if not entry:
            return []

        query = self.db.query(WatchlistHistory).filter(
            WatchlistHistory.watchlist_id == entry.id
        ).order_by(desc(WatchlistHistory.date))

        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(WatchlistHistory.date >= cutoff_date)

        history = query.all()

        return [
            {
                'date': h.date.isoformat(),
                'price': float(h.price) if h.price else None,
                'price_change_pct': h.price_change_pct,
                'total_return_pct': h.total_return_pct,
                'composite_score': h.composite_score,
                'value_score': h.value_score,
                'growth_score': h.growth_score,
                'quality_score': h.quality_score,
                'momentum_score': h.momentum_score,
                'stability_score': h.stability_score,
                'meets_criteria': h.meets_criteria,
                'criteria_violations': h.criteria_violations
            }
            for h in history
        ]
