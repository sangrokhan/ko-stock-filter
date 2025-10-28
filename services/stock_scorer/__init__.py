"""
Stock Scorer Service.

Calculates comprehensive composite investment scores for Korean stocks based on:
- Value score (PER, PBR, dividend yield, PSR)
- Growth score (revenue growth, earnings growth, equity growth)
- Quality score (ROE, margins, debt ratios)
- Momentum score (RSI, MACD, price trend, volume trend)

Produces an overall composite score (0-100) where higher values indicate better investment opportunities.
"""
from services.stock_scorer.stock_scorer import (
    StockScorer,
    ScoreMetrics
)
from services.stock_scorer.score_repository import ScoreDataRepository
from services.stock_scorer.score_service import ScoreService

__all__ = [
    'StockScorer',
    'ScoreMetrics',
    'ScoreDataRepository',
    'ScoreService',
]
