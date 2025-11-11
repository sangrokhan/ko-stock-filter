"""
Web Viewer Service - Main entry point.
Provides a web interface to view stock data from the database.
"""
import sys
from pathlib import Path
import logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

# Add shared directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database.connection import get_db
from shared.database.models import Stock, StockPrice
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Stock Database Viewer",
    description="Web interface for viewing stock data from database",
    version="1.0.0"
)

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# Pydantic models for API responses
class StockInfo(BaseModel):
    """Stock information model."""
    ticker: str
    name_kr: str
    name_en: Optional[str]
    market: Optional[str]
    sector: Optional[str]

    class Config:
        from_attributes = True


class StockPriceData(BaseModel):
    """Stock price data model."""
    id: int
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float]
    change_pct: Optional[float]

    class Config:
        from_attributes = True


class StockPriceResponse(BaseModel):
    """Response model for stock price data with pagination."""
    ticker: str
    stock_name: str
    total_records: int
    page: int
    page_size: int
    total_pages: int
    data: List[StockPriceData]


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    index_path = static_path / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Index page not found")

    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "web_viewer",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/stocks", response_model=List[StockInfo])
async def get_stocks(
    db: Session = Depends(get_db),
    is_active: bool = True,
    limit: int = Query(default=1000, le=5000)
):
    """
    Get list of all stocks in the database.

    Args:
        db: Database session
        is_active: Filter for active stocks only
        limit: Maximum number of stocks to return

    Returns:
        List of stock information
    """
    try:
        query = db.query(Stock)

        if is_active:
            query = query.filter(Stock.is_active == True)

        stocks = query.order_by(Stock.ticker).limit(limit).all()

        logger.info(f"Retrieved {len(stocks)} stocks from database")

        return stocks

    except Exception as e:
        logger.error(f"Error retrieving stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{ticker}/prices", response_model=StockPriceResponse)
async def get_stock_prices(
    ticker: str,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=10, le=500)
):
    """
    Get price data for a specific stock with pagination.

    Args:
        ticker: Stock ticker code
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of records per page

    Returns:
        Stock price data with pagination info
    """
    try:
        # Get stock info
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()

        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

        # Get total count
        total_records = db.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).count()

        if total_records == 0:
            return StockPriceResponse(
                ticker=ticker,
                stock_name=stock.name_kr,
                total_records=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                data=[]
            )

        # Calculate pagination
        total_pages = (total_records + page_size - 1) // page_size
        offset = (page - 1) * page_size

        # Get price data - sorted by date ascending (oldest first)
        # This ensures the latest data appears at the bottom when displayed
        prices = db.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).order_by(
            StockPrice.date.asc()
        ).offset(offset).limit(page_size).all()

        # Convert Decimal to float for JSON serialization
        price_data = []
        for price in prices:
            price_data.append(StockPriceData(
                id=price.id,
                date=price.date,
                open=float(price.open) if price.open else 0.0,
                high=float(price.high) if price.high else 0.0,
                low=float(price.low) if price.low else 0.0,
                close=float(price.close) if price.close else 0.0,
                volume=price.volume,
                adjusted_close=float(price.adjusted_close) if price.adjusted_close else None,
                change_pct=price.change_pct
            ))

        logger.info(f"Retrieved {len(prices)} price records for {ticker} (page {page}/{total_pages})")

        return StockPriceResponse(
            ticker=ticker,
            stock_name=stock.name_kr,
            total_records=total_records,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            data=price_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving prices for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{ticker}/info", response_model=StockInfo)
async def get_stock_info(
    ticker: str,
    db: Session = Depends(get_db)
):
    """
    Get information for a specific stock.

    Args:
        ticker: Stock ticker code
        db: Database session

    Returns:
        Stock information
    """
    try:
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()

        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

        return stock

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving stock info for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("Stock Database Viewer Service")
    logger.info("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
