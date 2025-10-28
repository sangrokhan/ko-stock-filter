# Stock Scoring System

A comprehensive stock scoring and ranking system that evaluates Korean stocks across multiple dimensions to identify the best investment opportunities.

## Overview

The Stock Scoring System calculates composite investment scores (0-100) based on four key dimensions:

1. **Value Score** (25% weight) - Valuation metrics
2. **Growth Score** (25% weight) - Growth metrics
3. **Quality Score** (25% weight) - Financial health and profitability
4. **Momentum Score** (25% weight) - Technical indicators and trends

## Score Components

### 1. Value Score (0-100)

Evaluates how attractively priced a stock is relative to fundamentals.

**Metrics:**
- **PER (Price-to-Earnings Ratio)**
  - Excellent: < 10 (100 pts)
  - Good: 10-15 (80-100 pts)
  - Fair: 15-25 (40-80 pts)
  - Poor: > 25 (0-40 pts)

- **PBR (Price-to-Book Ratio)**
  - Excellent: < 1.0 (100 pts)
  - Good: 1.0-2.0 (70-100 pts)
  - Fair: 2.0-3.0 (30-70 pts)
  - Poor: > 3.0 (0-30 pts)

- **PSR (Price-to-Sales Ratio)**
  - Excellent: < 1.0 (100 pts)
  - Good: 1.0-2.0 (70-100 pts)
  - Fair: 2.0-4.0 (30-70 pts)
  - Poor: > 4.0 (0-30 pts)

- **Dividend Yield**
  - Excellent: > 5% (100 pts)
  - Good: 3-5% (80-100 pts)
  - Fair: 1-3% (50-80 pts)
  - Poor: < 1% (0-50 pts)

### 2. Growth Score (0-100)

Evaluates the company's growth trajectory.

**Metrics:**
- **Revenue Growth (YoY)**
  - Excellent: > 20% (100 pts)
  - Good: 10-20% (80-100 pts)
  - Fair: 0-10% (50-80 pts)
  - Poor: < 0% (0-50 pts)

- **Earnings Growth (YoY)**
  - Excellent: > 25% (100 pts)
  - Good: 15-25% (80-100 pts)
  - Fair: 5-15% (50-80 pts)
  - Poor: < 5% (0-50 pts)

- **Equity Growth (YoY)**
  - Excellent: > 15% (100 pts)
  - Good: 10-15% (80-100 pts)
  - Fair: 5-10% (50-80 pts)
  - Poor: < 5% (0-50 pts)

### 3. Quality Score (0-100)

Evaluates financial health and operational efficiency.

**Metrics:**
- **ROE (Return on Equity)**
  - Excellent: > 20% (100 pts)
  - Good: 15-20% (80-100 pts)
  - Fair: 10-15% (50-80 pts)
  - Poor: < 10% (0-50 pts)

- **Operating Margin**
  - Excellent: > 20% (100 pts)
  - Good: 15-20% (80-100 pts)
  - Fair: 10-15% (50-80 pts)
  - Poor: < 10% (0-50 pts)

- **Net Margin**
  - Excellent: > 15% (100 pts)
  - Good: 10-15% (80-100 pts)
  - Fair: 5-10% (50-80 pts)
  - Poor: < 5% (0-50 pts)

- **Debt Ratio** (inverse scoring)
  - Excellent: < 30% (100 pts)
  - Good: 30-50% (80-100 pts)
  - Fair: 50-70% (40-80 pts)
  - Poor: > 70% (0-40 pts)

- **Current Ratio**
  - Excellent: > 2.0 (100 pts)
  - Good: 1.5-2.0 (80-100 pts)
  - Fair: 1.0-1.5 (50-80 pts)
  - Poor: < 1.0 (0-50 pts)

### 4. Momentum Score (0-100)

Evaluates technical indicators and price trends.

**Metrics:**
- **RSI (14-day)**
  - Excellent: 50-70 (100 pts) - Bullish but not overbought
  - Good: 40-80 (80 pts)
  - Fair: 30-90 (50 pts)
  - Poor: < 30 or > 90 (0-50 pts) - Oversold/Overbought

- **MACD Histogram**
  - Positive = Bullish (50-100 pts)
  - Negative = Bearish (0-50 pts)

- **Price Trend (20-day linear regression)**
  - Excellent: > +0.5% per day (100 pts)
  - Good: +0.2-0.5% per day (80-100 pts)
  - Fair: -0.2 to +0.2% per day (50-80 pts)
  - Poor: < -0.2% per day (0-50 pts)

- **Volume Trend**
  - Increasing volume = Positive (50-100 pts)
  - Decreasing volume = Neutral (0-50 pts)

## Composite Score Calculation

The composite score is calculated as a weighted average:

```
Composite Score = (Value × 0.25) + (Growth × 0.25) + (Quality × 0.25) + (Momentum × 0.25)
```

Weights can be customized based on investment strategy:
- **Value investing**: Increase value and quality weights
- **Growth investing**: Increase growth and momentum weights
- **Balanced**: Use default equal weights

## Usage

### Command Line

#### Calculate scores for all stocks
```bash
cd /home/user/ko-stock-filter
python -m services.stock_scorer.main calculate --limit 100
```

#### Get top-scoring stocks
```bash
python -m services.stock_scorer.main top --limit 50 --min-score 60
```

#### Add top stocks to watchlist
```bash
python -m services.stock_scorer.main watchlist --user-id "my_user" --limit 30 --min-score 65
```

#### Get detailed breakdown for a stock
```bash
python -m services.stock_scorer.main breakdown --ticker "005930"
```

### Python API

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.stock_scorer import ScoreService

# Create database session
engine = create_engine("postgresql://...")
Session = sessionmaker(bind=engine)
db = Session()

# Create service with default weights
service = ScoreService(db)

# Calculate scores for all stocks
results = service.calculate_scores_for_all_stocks(update_percentiles=True)

# Get top 50 stocks
top_stocks = service.get_top_stocks(limit=50, min_score=60)

# Add to watchlist
service.add_top_stocks_to_watchlist(
    user_id="my_user",
    limit=30,
    min_score=65
)

# Get detailed breakdown
breakdown = service.get_stock_score_breakdown(stock_id=123)
```

### Custom Weights

```python
# Emphasize value and quality (40% each)
service = ScoreService(
    db,
    weight_value=0.40,
    weight_quality=0.40,
    weight_growth=0.10,
    weight_momentum=0.10
)

# Emphasize growth and momentum
service = ScoreService(
    db,
    weight_value=0.15,
    weight_quality=0.15,
    weight_growth=0.35,
    weight_momentum=0.35
)
```

## Output

### Top Stocks Output
```
Rank  Ticker  Name                          Score   Value  Growth Quality Momentum Percentile
================================================================================================
1     005930  삼성전자                        85.3    82.5   88.0   87.1    83.6     98.5%
2     000660  SK하이닉스                      82.1    78.3   85.9   84.2    80.0     96.2%
...
```

### Score Breakdown Output
```
=== Score Breakdown for 005930 ===
Name: 삼성전자
Market: KOSPI
Sector: 전기전자
Industry: 반도체

Composite Score: 85.3
Percentile Rank: 98.5%

--- Component Scores ---

Value Score: 82.5 (weight: 25%)
  per_score: 85.0
  pbr_score: 80.0
  psr_score: 82.0
  dividend_yield_score: 83.0

Growth Score: 88.0 (weight: 25%)
  revenue_growth_score: 85.0
  earnings_growth_score: 92.0
  equity_growth_score: 87.0

Quality Score: 87.1 (weight: 25%)
  roe_score: 90.0
  operating_margin_score: 88.0
  net_margin_score: 86.0
  debt_ratio_score: 85.0
  current_ratio_score: 84.0

Momentum Score: 83.6 (weight: 25%)
  rsi_score: 85.0
  macd_score: 82.0
  price_trend_score: 84.0
  volume_trend_score: 83.5
```

## Database Schema

The system stores scores in the `composite_scores` table:

```sql
CREATE TABLE composite_scores (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    date TIMESTAMP,

    -- Component scores
    value_score FLOAT,
    growth_score FLOAT,
    quality_score FLOAT,
    momentum_score FLOAT,

    -- Composite score
    composite_score FLOAT NOT NULL,
    percentile_rank FLOAT,

    -- Weights
    weight_value FLOAT DEFAULT 0.25,
    weight_growth FLOAT DEFAULT 0.25,
    weight_quality FLOAT DEFAULT 0.25,
    weight_momentum FLOAT DEFAULT 0.25,

    -- Detailed component scores
    per_score FLOAT,
    pbr_score FLOAT,
    dividend_yield_score FLOAT,
    -- ... (see models.py for full schema)

    -- Data quality
    data_quality_score FLOAT,
    missing_value_count INTEGER,
    total_metric_count INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_composite_scores_stock_date ON composite_scores(stock_id, date);
CREATE INDEX idx_composite_scores_score ON composite_scores(composite_score);
```

## Integration with Watchlist

Top-scoring stocks can be automatically added to a user's watchlist:

```python
# Add top 50 stocks with score >= 60 to watchlist
service.add_top_stocks_to_watchlist(
    user_id="my_user",
    limit=50,
    min_score=60.0,
    tags="top-scored,auto-added"
)
```

Each watchlist entry includes:
- Stock reference
- Composite score
- Reason for inclusion
- Tags for categorization
- Timestamp

## Data Requirements

For accurate scoring, the system requires:
- **Fundamental indicators**: PER, PBR, PSR, ROE, margins, debt ratios, growth rates
- **Technical indicators**: RSI, MACD, moving averages
- **Price history**: At least 20 days of OHLCV data

Missing data is handled gracefully:
- Scores are calculated from available metrics
- Data quality score indicates completeness
- Warnings are logged for missing critical data

## Performance

- Single stock calculation: ~50-100ms
- Batch calculation (1000 stocks): ~1-2 minutes
- Percentile rank update: ~1-2 seconds

## Future Enhancements

- Industry-relative scoring (compare to sector peers)
- Time-series score tracking (trend analysis)
- Machine learning-based weight optimization
- Custom scoring formulas per user
- Real-time score updates on new data
- Alert system for score changes

## See Also

- `/examples/stock_scoring_example.py` - Comprehensive usage examples
- `/shared/database/models.py` - Database models
- `/services/stock_screener/` - Stock screening engine
- `/services/stability_calculator/` - Stability score calculator
