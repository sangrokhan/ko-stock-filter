"""
FastAPI endpoints for Risk Manager Service.
Provides REST API for portfolio risk monitoring and order validation.
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.database.connection import get_db
from services.risk_manager.main import RiskManagerService, RiskParameters
from services.risk_manager.position_sizing import PositionSizingMethod

app = FastAPI(
    title="Risk Manager Service API",
    description="Portfolio risk monitoring and order validation service with stop-loss and take-profit management",
    version="2.0.0"
)

# Initialize risk manager service
risk_manager = RiskManagerService()


# Pydantic models for API
class OrderRequest(BaseModel):
    """Order request model."""
    ticker: str = Field(..., description="Stock ticker code")
    side: str = Field(..., description="Order side: BUY or SELL")
    quantity: int = Field(..., gt=0, description="Number of shares")
    price: float = Field(..., gt=0, description="Price per share")


class OrderValidationResponse(BaseModel):
    """Order validation response model."""
    is_valid: bool
    reason: str
    warnings: List[str]
    suggested_quantity: Optional[int] = None


class PortfolioSummaryResponse(BaseModel):
    """Portfolio summary response model."""
    user_id: str
    portfolio_summary: Dict
    risk_metrics: Dict
    positions: List[Dict]


class RiskStatusResponse(BaseModel):
    """Risk status response model."""
    status: str
    metrics: Dict
    limits: Dict
    violations: List[str]
    warnings: List[str]


class RiskParametersUpdate(BaseModel):
    """Risk parameters update model."""
    max_position_size: Optional[float] = Field(None, ge=0, le=100)
    max_portfolio_risk: Optional[float] = Field(None, ge=0, le=100)
    max_drawdown: Optional[float] = Field(None, ge=0, le=100)
    stop_loss_pct: Optional[float] = Field(None, ge=0, le=100)
    max_leverage: Optional[float] = Field(None, ge=1)
    max_total_loss: Optional[float] = Field(None, ge=0, le=100)


class InitializePortfolioRequest(BaseModel):
    """Initialize portfolio with initial capital."""
    initial_capital: int = Field(..., gt=0, description="Initial capital in KRW")
    cash_balance: Optional[int] = Field(None, description="Current cash balance in KRW")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Risk Manager Service",
        "version": "1.0.0",
        "status": "running" if risk_manager.running else "stopped"
    }


@app.post("/start")
async def start_service():
    """Start the risk manager service."""
    risk_manager.start()
    return {"message": "Risk Manager Service started", "status": "running"}


@app.post("/stop")
async def stop_service():
    """Stop the risk manager service."""
    risk_manager.stop()
    return {"message": "Risk Manager Service stopped", "status": "stopped"}


@app.get("/risk-parameters")
async def get_risk_parameters():
    """Get current risk parameters."""
    return {
        "max_position_size": risk_manager.risk_params.max_position_size,
        "max_portfolio_risk": risk_manager.risk_params.max_portfolio_risk,
        "max_drawdown": risk_manager.risk_params.max_drawdown,
        "stop_loss_pct": risk_manager.risk_params.stop_loss_pct,
        "max_leverage": risk_manager.risk_params.max_leverage,
        "max_total_loss": risk_manager.risk_params.max_total_loss
    }


@app.put("/risk-parameters")
async def update_risk_parameters(params: RiskParametersUpdate):
    """Update risk parameters."""
    if params.max_position_size is not None:
        risk_manager.risk_params.max_position_size = params.max_position_size
    if params.max_portfolio_risk is not None:
        risk_manager.risk_params.max_portfolio_risk = params.max_portfolio_risk
    if params.max_drawdown is not None:
        risk_manager.risk_params.max_drawdown = params.max_drawdown
    if params.stop_loss_pct is not None:
        risk_manager.risk_params.stop_loss_pct = params.stop_loss_pct
    if params.max_leverage is not None:
        risk_manager.risk_params.max_leverage = params.max_leverage
    if params.max_total_loss is not None:
        risk_manager.risk_params.max_total_loss = params.max_total_loss

    return {
        "message": "Risk parameters updated",
        "parameters": {
            "max_position_size": risk_manager.risk_params.max_position_size,
            "max_portfolio_risk": risk_manager.risk_params.max_portfolio_risk,
            "max_drawdown": risk_manager.risk_params.max_drawdown,
            "stop_loss_pct": risk_manager.risk_params.stop_loss_pct,
            "max_leverage": risk_manager.risk_params.max_leverage,
            "max_total_loss": risk_manager.risk_params.max_total_loss
        }
    }


@app.post("/portfolio/{user_id}/initialize")
async def initialize_portfolio(
    user_id: str,
    request: InitializePortfolioRequest,
    db: Session = Depends(get_db)
):
    """
    Initialize portfolio with initial capital.
    This is required before risk management can properly track losses.
    """
    from shared.database.models import PortfolioRiskMetrics

    # Create initial risk metrics record
    initial_metrics = PortfolioRiskMetrics(
        user_id=user_id,
        date=datetime.utcnow(),
        total_value=request.initial_capital,
        cash_balance=request.cash_balance or request.initial_capital,
        invested_amount=0,
        peak_value=request.initial_capital,
        initial_capital=request.initial_capital,
        total_pnl=0,
        total_pnl_pct=0.0,
        realized_pnl=0,
        unrealized_pnl=0,
        daily_pnl=0,
        daily_pnl_pct=0.0,
        current_drawdown=0.0,
        max_drawdown=0.0,
        drawdown_duration_days=0,
        is_at_peak=True,
        position_count=0,
        largest_position_pct=0.0,
        total_exposure_pct=0.0,
        total_loss_from_initial=0,
        total_loss_from_initial_pct=0.0,
        total_loss_from_peak=0,
        total_loss_from_peak_pct=0.0,
        max_position_size_limit=risk_manager.risk_params.max_position_size,
        max_loss_limit=risk_manager.risk_params.max_total_loss,
        is_trading_halted=False
    )

    db.add(initial_metrics)
    db.commit()
    db.refresh(initial_metrics)

    return {
        "message": f"Portfolio initialized for user {user_id}",
        "initial_capital": request.initial_capital,
        "cash_balance": request.cash_balance or request.initial_capital
    }


@app.post("/orders/{user_id}/validate", response_model=OrderValidationResponse)
async def validate_order(
    user_id: str,
    order: OrderRequest,
    db: Session = Depends(get_db)
):
    """
    Validate an order against risk management rules.
    Returns validation status and warnings.
    """
    order_dict = {
        'ticker': order.ticker,
        'side': order.side.upper(),
        'quantity': order.quantity,
        'price': order.price
    }

    result = risk_manager.validate_order(order_dict, user_id, db)

    return OrderValidationResponse(
        is_valid=result.is_valid,
        reason=result.reason,
        warnings=result.warnings,
        suggested_quantity=result.suggested_quantity
    )


@app.get("/portfolio/{user_id}/metrics")
async def get_portfolio_metrics(user_id: str, db: Session = Depends(get_db)):
    """
    Get current portfolio metrics including P&L, drawdown, and positions.
    """
    metrics = risk_manager.calculate_portfolio_metrics(user_id, db)

    return {
        "user_id": metrics.user_id,
        "total_value": metrics.total_value,
        "cash_balance": metrics.cash_balance,
        "invested_amount": metrics.invested_amount,
        "total_pnl": metrics.total_pnl,
        "total_pnl_pct": round(metrics.total_pnl_pct, 2),
        "realized_pnl": metrics.realized_pnl,
        "unrealized_pnl": metrics.unrealized_pnl,
        "current_drawdown": round(metrics.current_drawdown, 2),
        "peak_value": metrics.peak_value,
        "initial_capital": metrics.initial_capital,
        "total_loss_from_initial_pct": round(metrics.total_loss_from_initial_pct, 2),
        "is_trading_halted": metrics.is_trading_halted,
        "position_count": metrics.position_count,
        "largest_position_pct": round(metrics.largest_position_pct, 2),
        "largest_position_ticker": metrics.largest_position_ticker,
        "positions": metrics.positions
    }


@app.post("/portfolio/{user_id}/update-metrics")
async def update_portfolio_metrics(user_id: str, db: Session = Depends(get_db)):
    """
    Calculate and update portfolio risk metrics in database.
    """
    metrics = risk_manager.calculate_portfolio_metrics(user_id, db)
    risk_metrics = risk_manager.update_risk_metrics(metrics, db)

    return {
        "message": "Portfolio metrics updated",
        "user_id": user_id,
        "metrics_id": risk_metrics.id,
        "total_value": risk_metrics.total_value,
        "total_pnl": risk_metrics.total_pnl,
        "current_drawdown": round(risk_metrics.current_drawdown, 2),
        "is_trading_halted": risk_metrics.is_trading_halted,
        "timestamp": risk_metrics.date
    }


@app.get("/portfolio/{user_id}/risk-status", response_model=RiskStatusResponse)
async def get_risk_status(user_id: str, db: Session = Depends(get_db)):
    """
    Get current risk status including violations and warnings.
    """
    risk_status = risk_manager.check_portfolio_risk(user_id, db)

    return RiskStatusResponse(**risk_status)


@app.get("/portfolio/{user_id}/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(user_id: str, db: Session = Depends(get_db)):
    """
    Get comprehensive portfolio summary with positions and risk metrics.
    """
    summary = risk_manager.get_position_summary(user_id, db)

    return PortfolioSummaryResponse(**summary)


@app.get("/portfolio/{user_id}/is-trading-allowed")
async def is_trading_allowed(user_id: str, db: Session = Depends(get_db)):
    """
    Check if trading is currently allowed for this user.
    Returns False if 30% loss limit has been reached.
    """
    metrics = risk_manager.calculate_portfolio_metrics(user_id, db)

    return {
        "user_id": user_id,
        "is_trading_allowed": not metrics.is_trading_halted,
        "is_trading_halted": metrics.is_trading_halted,
        "total_loss_pct": round(metrics.total_loss_from_initial_pct, 2),
        "max_loss_limit": risk_manager.risk_params.max_total_loss,
        "reason": (
            f"Trading halted: Loss {metrics.total_loss_from_initial_pct:.2f}% exceeds limit"
            if metrics.is_trading_halted
            else "Trading allowed"
        )
    }


@app.post("/portfolio/{user_id}/resume-trading")
async def resume_trading(user_id: str, db: Session = Depends(get_db)):
    """
    Resume trading after manual review (admin function).
    This should only be used after addressing the underlying issues.
    """
    from shared.database.models import PortfolioRiskMetrics
    from sqlalchemy import desc

    # Get latest risk metrics
    latest = db.query(PortfolioRiskMetrics).filter(
        PortfolioRiskMetrics.user_id == user_id
    ).order_by(desc(PortfolioRiskMetrics.date)).first()

    if not latest:
        raise HTTPException(status_code=404, detail="No portfolio metrics found")

    if not latest.is_trading_halted:
        return {
            "message": "Trading is not halted",
            "user_id": user_id,
            "is_trading_halted": False
        }

    # Create new metrics record with trading resumed
    metrics = risk_manager.calculate_portfolio_metrics(user_id, db)
    risk_metrics = risk_manager.update_risk_metrics(metrics, db)

    # Override trading halt status
    risk_metrics.is_trading_halted = False
    risk_metrics.trading_halt_reason = "Trading resumed by admin"
    risk_metrics.risk_warnings = "Trading resumed - monitor closely"
    db.commit()

    return {
        "message": "Trading resumed",
        "user_id": user_id,
        "is_trading_halted": False,
        "warning": "Trading halt was overridden - monitor risk carefully"
    }


@app.get("/portfolio/{user_id}/risk-history")
async def get_risk_history(
    user_id: str,
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get historical risk metrics for a user.
    """
    from shared.database.models import PortfolioRiskMetrics
    from sqlalchemy import desc

    history = db.query(PortfolioRiskMetrics).filter(
        PortfolioRiskMetrics.user_id == user_id
    ).order_by(desc(PortfolioRiskMetrics.date)).limit(limit).all()

    return {
        "user_id": user_id,
        "count": len(history),
        "history": [
            {
                "date": h.date,
                "total_value": h.total_value,
                "total_pnl": h.total_pnl,
                "total_pnl_pct": round(h.total_pnl_pct or 0, 2),
                "current_drawdown": round(h.current_drawdown, 2),
                "total_loss_from_initial_pct": round(h.total_loss_from_initial_pct, 2),
                "is_trading_halted": h.is_trading_halted,
                "position_count": h.position_count,
                "daily_pnl": h.daily_pnl,
                "daily_pnl_pct": round(h.daily_pnl_pct or 0, 2)
            }
            for h in history
        ]
    }


@app.post("/position-size/calculate")
async def calculate_position_size(
    ticker: str,
    entry_price: float,
    stop_loss_price: float,
    portfolio_value: float,
    method: Optional[str] = "kelly_half",
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Calculate recommended position size based on risk parameters and method.
    Supports Kelly Criterion, fixed percent, and fixed risk methods.
    """
    try:
        # Convert method string to enum
        try:
            sizing_method = PositionSizingMethod(method) if method else None
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid method: {method}. Valid methods: kelly_criterion, kelly_half, kelly_quarter, fixed_percent, fixed_risk, volatility_adjusted"
            )

        result = risk_manager.calculate_position_size(
            ticker=ticker,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            portfolio_value=portfolio_value,
            method=sizing_method,
            user_id=user_id,
            db=db if user_id else None
        )

        return {
            "ticker": ticker,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "portfolio_value": portfolio_value,
            "recommended_shares": result['shares'],
            "position_value": result['position_value'],
            "position_pct": round(result['position_pct'], 2),
            "method": result['method'],
            "kelly_fraction": result.get('kelly_fraction'),
            "risk_amount": result.get('risk_amount'),
            "risk_per_share": abs(entry_price - stop_loss_price),
            "total_risk": result['shares'] * abs(entry_price - stop_loss_price),
            "notes": result.get('notes')
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Stop-Loss and Take-Profit Management Endpoints
# ============================================================================

class PositionLimitsRequest(BaseModel):
    """Request to set/update position limits."""
    stop_loss_pct: Optional[float] = Field(None, ge=0, le=100, description="Stop-loss percentage")
    take_profit_pct: Optional[float] = Field(None, ge=0, le=100, description="Take-profit percentage")
    trailing_stop_enabled: Optional[bool] = Field(None, description="Enable trailing stop-loss")
    trailing_stop_distance_pct: Optional[float] = Field(None, ge=0, le=100, description="Trailing stop distance %")
    take_profit_use_technical: Optional[bool] = Field(None, description="Use technical signals for take-profit")


class PositionLimitsResponse(BaseModel):
    """Response with position limits."""
    user_id: str
    ticker: str
    stop_loss_price: Optional[float]
    stop_loss_pct: float
    take_profit_price: Optional[float]
    take_profit_pct: float
    trailing_stop_price: Optional[float]
    trailing_stop_enabled: bool
    trailing_stop_distance_pct: float
    highest_price_since_purchase: Optional[float]
    current_price: Optional[float]


@app.post("/portfolio/{user_id}/positions/{ticker}/initialize-limits")
async def initialize_position_limits(
    user_id: str,
    ticker: str,
    stop_loss_pct: float = 10.0,
    take_profit_pct: float = 20.0,
    trailing_stop_enabled: bool = True,
    trailing_stop_distance_pct: float = 10.0,
    db: Session = Depends(get_db)
):
    """
    Initialize stop-loss and take-profit limits for a position.
    Should be called when a new position is opened.
    """
    from shared.database.models import Portfolio
    from decimal import Decimal

    position = db.query(Portfolio).filter(
        Portfolio.user_id == user_id,
        Portfolio.ticker == ticker
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail=f"Position not found for {ticker}")

    # Initialize limits using position monitor
    entry_price = float(position.avg_price)
    risk_manager.position_monitor.initialize_position_limits(
        position=position,
        entry_price=entry_price,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        trailing_stop_enabled=trailing_stop_enabled,
        trailing_stop_distance_pct=trailing_stop_distance_pct
    )

    db.commit()
    db.refresh(position)

    return {
        "message": f"Position limits initialized for {ticker}",
        "user_id": user_id,
        "ticker": ticker,
        "entry_price": entry_price,
        "stop_loss_price": float(position.stop_loss_price),
        "stop_loss_pct": position.stop_loss_pct,
        "take_profit_price": float(position.take_profit_price),
        "take_profit_pct": position.take_profit_pct,
        "trailing_stop_enabled": position.trailing_stop_enabled,
        "trailing_stop_distance_pct": position.trailing_stop_distance_pct
    }


@app.put("/portfolio/{user_id}/positions/{ticker}/limits", response_model=PositionLimitsResponse)
async def update_position_limits(
    user_id: str,
    ticker: str,
    limits: PositionLimitsRequest,
    db: Session = Depends(get_db)
):
    """
    Update stop-loss and take-profit limits for a position.
    """
    from shared.database.models import Portfolio
    from decimal import Decimal

    position = db.query(Portfolio).filter(
        Portfolio.user_id == user_id,
        Portfolio.ticker == ticker
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail=f"Position not found for {ticker}")

    entry_price = float(position.avg_price)

    # Update stop-loss
    if limits.stop_loss_pct is not None:
        position.stop_loss_pct = limits.stop_loss_pct
        stop_loss_price = entry_price * (1 - limits.stop_loss_pct / 100)
        position.stop_loss_price = Decimal(str(stop_loss_price))

    # Update take-profit
    if limits.take_profit_pct is not None:
        position.take_profit_pct = limits.take_profit_pct
        take_profit_price = entry_price * (1 + limits.take_profit_pct / 100)
        position.take_profit_price = Decimal(str(take_profit_price))

    # Update trailing stop settings
    if limits.trailing_stop_enabled is not None:
        position.trailing_stop_enabled = limits.trailing_stop_enabled

    if limits.trailing_stop_distance_pct is not None:
        position.trailing_stop_distance_pct = limits.trailing_stop_distance_pct
        # Recalculate trailing stop price if highest price exists
        if position.highest_price_since_purchase:
            highest = float(position.highest_price_since_purchase)
            trailing_stop_price = highest * (1 - limits.trailing_stop_distance_pct / 100)
            position.trailing_stop_price = Decimal(str(trailing_stop_price))

    if limits.take_profit_use_technical is not None:
        position.take_profit_use_technical = limits.take_profit_use_technical

    position.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(position)

    return PositionLimitsResponse(
        user_id=position.user_id,
        ticker=position.ticker,
        stop_loss_price=float(position.stop_loss_price) if position.stop_loss_price else None,
        stop_loss_pct=position.stop_loss_pct,
        take_profit_price=float(position.take_profit_price) if position.take_profit_price else None,
        take_profit_pct=position.take_profit_pct,
        trailing_stop_price=float(position.trailing_stop_price) if position.trailing_stop_price else None,
        trailing_stop_enabled=position.trailing_stop_enabled,
        trailing_stop_distance_pct=position.trailing_stop_distance_pct,
        highest_price_since_purchase=float(position.highest_price_since_purchase) if position.highest_price_since_purchase else None,
        current_price=float(position.current_price) if position.current_price else None
    )


@app.get("/portfolio/{user_id}/positions/{ticker}/limits", response_model=PositionLimitsResponse)
async def get_position_limits(
    user_id: str,
    ticker: str,
    db: Session = Depends(get_db)
):
    """
    Get current stop-loss and take-profit limits for a position.
    """
    from shared.database.models import Portfolio

    position = db.query(Portfolio).filter(
        Portfolio.user_id == user_id,
        Portfolio.ticker == ticker
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail=f"Position not found for {ticker}")

    return PositionLimitsResponse(
        user_id=position.user_id,
        ticker=position.ticker,
        stop_loss_price=float(position.stop_loss_price) if position.stop_loss_price else None,
        stop_loss_pct=position.stop_loss_pct or 10.0,
        take_profit_price=float(position.take_profit_price) if position.take_profit_price else None,
        take_profit_pct=position.take_profit_pct or 20.0,
        trailing_stop_price=float(position.trailing_stop_price) if position.trailing_stop_price else None,
        trailing_stop_enabled=position.trailing_stop_enabled if position.trailing_stop_enabled is not None else True,
        trailing_stop_distance_pct=position.trailing_stop_distance_pct or 10.0,
        highest_price_since_purchase=float(position.highest_price_since_purchase) if position.highest_price_since_purchase else None,
        current_price=float(position.current_price) if position.current_price else None
    )


@app.post("/portfolio/{user_id}/monitor")
async def monitor_positions(user_id: str, db: Session = Depends(get_db)):
    """
    Monitor all positions for stop-loss, trailing stop, and take-profit triggers.
    Returns exit signals for positions that have breached their limits.
    """
    result = risk_manager.position_monitor.monitor_positions(user_id, db)

    # Convert exit signals to dict format
    exit_signals = [
        {
            "ticker": signal.ticker,
            "signal_type": signal.signal_type,
            "current_price": signal.current_price,
            "trigger_price": signal.trigger_price,
            "quantity": signal.quantity,
            "reason": signal.reason,
            "urgency": signal.urgency,
            "technical_signals": signal.technical_signals
        }
        for signal in result.exit_signals
    ]

    return {
        "user_id": user_id,
        "positions_checked": result.positions_checked,
        "exit_signals_count": len(result.exit_signals),
        "exit_signals": exit_signals,
        "trailing_stops_updated": result.trailing_stops_updated,
        "warnings": result.warnings,
        "emergency_liquidation_triggered": result.emergency_liquidation_triggered
    }


@app.get("/portfolio/{user_id}/all-positions-limits")
async def get_all_positions_limits(user_id: str, db: Session = Depends(get_db)):
    """
    Get stop-loss and take-profit limits for all positions.
    """
    from shared.database.models import Portfolio

    positions = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

    if not positions:
        return {
            "user_id": user_id,
            "count": 0,
            "positions": []
        }

    positions_data = []
    for position in positions:
        positions_data.append({
            "ticker": position.ticker,
            "quantity": position.quantity,
            "avg_price": float(position.avg_price),
            "current_price": float(position.current_price) if position.current_price else None,
            "unrealized_pnl_pct": float(position.unrealized_pnl_pct) if position.unrealized_pnl_pct else 0.0,
            "stop_loss_price": float(position.stop_loss_price) if position.stop_loss_price else None,
            "stop_loss_pct": position.stop_loss_pct or 10.0,
            "take_profit_price": float(position.take_profit_price) if position.take_profit_price else None,
            "take_profit_pct": position.take_profit_pct or 20.0,
            "trailing_stop_price": float(position.trailing_stop_price) if position.trailing_stop_price else None,
            "trailing_stop_enabled": position.trailing_stop_enabled if position.trailing_stop_enabled is not None else True,
            "highest_price_since_purchase": float(position.highest_price_since_purchase) if position.highest_price_since_purchase else None
        })

    return {
        "user_id": user_id,
        "count": len(positions_data),
        "positions": positions_data
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
