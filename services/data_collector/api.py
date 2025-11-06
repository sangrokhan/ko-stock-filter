"""
FastAPI endpoint for health checks and service monitoring.
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add shared directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Global reference to the service instance (set by main.py)
_service_instance = None


def set_service_instance(service):
    """Set the global service instance for API access."""
    global _service_instance
    _service_instance = service


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    service: str
    version: str
    scheduler_enabled: bool
    scheduler_running: bool
    scheduled_jobs: list


class JobTriggerRequest(BaseModel):
    """Request model for triggering a job."""
    job_id: str


class CollectionRequest(BaseModel):
    """Request model for data collection."""
    ticker: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# Create FastAPI app
app = FastAPI(
    title="Data Collector Service",
    description="Korean Stock Data Collection Service",
    version="1.0.0"
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns service status and scheduler information.
    """
    if _service_instance is None:
        return {
            "status": "starting",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "data_collector",
            "version": "1.0.0",
            "scheduler_enabled": False,
            "scheduler_running": False,
            "scheduled_jobs": []
        }

    scheduler_status = _service_instance.get_scheduler_status()

    return {
        "status": "healthy" if _service_instance.running else "stopped",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "data_collector",
        "version": "1.0.0",
        "scheduler_enabled": scheduler_status['enabled'],
        "scheduler_running": scheduler_status['running'],
        "scheduled_jobs": scheduler_status.get('jobs', [])
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Data Collector Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "scheduler_status": "/scheduler/status",
            "trigger_job": "/scheduler/trigger (POST)",
            "collect_stocks": "/collect/stocks (POST)",
            "collect_prices": "/collect/prices (POST)",
            "collect_fundamentals": "/collect/fundamentals (POST)"
        }
    }


@app.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status and job information."""
    if _service_instance is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return _service_instance.get_scheduler_status()


@app.post("/scheduler/trigger")
async def trigger_job(request: JobTriggerRequest):
    """Manually trigger a scheduled job."""
    if _service_instance is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        _service_instance.run_scheduled_job(request.job_id)
        return {"status": "triggered", "job_id": request.job_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/collect/stocks")
async def collect_stocks():
    """Collect all stock codes from KOSPI, KOSDAQ, and KONEX."""
    if _service_instance is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        count = _service_instance.collect_all_stock_codes()
        return {
            "status": "completed",
            "stocks_collected": count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collect/prices")
async def collect_prices(request: CollectionRequest):
    """
    Collect price data for stocks.
    If ticker is provided, collects for that stock only.
    Otherwise, collects for all active stocks.
    """
    if _service_instance is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        if request.ticker:
            count = _service_instance.collect_prices_for_stock(
                request.ticker,
                request.start_date,
                request.end_date
            )
            return {
                "status": "completed",
                "ticker": request.ticker,
                "records_collected": count,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            stats = _service_instance.collect_prices_for_all_stocks(
                request.start_date,
                request.end_date
            )
            return {
                "status": "completed",
                "statistics": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collect/fundamentals")
async def collect_fundamentals(request: CollectionRequest):
    """
    Collect fundamental data for stocks.
    If ticker is provided, collects for that stock only.
    Otherwise, collects for all active stocks.
    """
    if _service_instance is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        if request.ticker:
            success = _service_instance.collect_fundamentals_for_stock(
                request.ticker,
                request.start_date  # Using start_date as date parameter
            )
            return {
                "status": "completed" if success else "failed",
                "ticker": request.ticker,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            stats = _service_instance.collect_fundamentals_for_all_stocks(
                request.start_date  # Using start_date as date parameter
            )
            return {
                "status": "completed",
                "statistics": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collect/initial")
async def run_initial_collection():
    """
    Run initial data collection for new setup.
    This will:
    1. Collect all stock codes
    2. Collect last 30 days of price data
    3. Collect current fundamental data
    """
    if _service_instance is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        _service_instance.run_initial_collection()
        return {
            "status": "completed",
            "message": "Initial data collection completed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
