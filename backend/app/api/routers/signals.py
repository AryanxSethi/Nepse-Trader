"""Signal routes — generated BUY/SELL/HOLD signals."""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, select

from app.analysis.signals import generate_signals
from app.db.models import Signal
from app.db.session import async_session

router = APIRouter()
logger = logging.getLogger('routers.signals')


@router.get("/api/signals")
async def get_signals(signal_type: str = "") -> list[dict]:
    """GET /api/signals — return generated trading signals, optionally filtered by type."""
    async with async_session() as session:
        q = select(Signal).order_by(desc(Signal.confidence), Signal.generated_at).limit(200)
        if signal_type:
            q = q.where(Signal.signal_type == signal_type.upper())
        result = await session.execute(q)
        return [
            {
                "symbol": s.symbol,
                "signal_type": s.signal_type,
                "confidence": s.confidence,
                "reason": s.reason,
                "generated_at": s.generated_at.isoformat(),
            }
            for s in result.scalars().all()
        ]


@router.post("/api/signals/generate")
async def trigger_signals() -> dict:
    """POST /api/signals/generate — manually trigger signal generation for all tracked symbols."""
    try:
        await generate_signals()
        return {"status": "done"}
    except Exception as e:
        logger.error("Signal generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Signal generation failed")