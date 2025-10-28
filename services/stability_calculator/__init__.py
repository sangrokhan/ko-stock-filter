"""
Stability Calculator Service.

Calculates comprehensive stability scores for Korean stocks based on:
- Price volatility (standard deviation of returns)
- Beta coefficient (systematic risk vs market)
- Volume stability (coefficient of variation)
- Earnings consistency
- Debt stability trend

Produces an overall stability score (0-100) where higher values indicate more stable stocks.
"""
from services.stability_calculator.stability_calculator import (
    StabilityCalculator,
    StabilityMetrics
)
from services.stability_calculator.stability_repository import StabilityDataRepository
from services.stability_calculator.stability_service import StabilityService

__all__ = [
    'StabilityCalculator',
    'StabilityMetrics',
    'StabilityDataRepository',
    'StabilityService',
]
