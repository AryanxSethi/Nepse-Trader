"""Broker routes — top brokers and broker search."""

from fastapi import APIRouter, HTTPException

from app.guide.broker_directory import _ensure_brokers as _ensure_broker_cache
from app.guide.broker_directory import get_top_brokers, search_brokers

router = APIRouter()

_VALID_PERIODS = {"daily", "weekly", "monthly"}


@router.get("/api/brokers/top")
async def brokers_top(period: str = "monthly", limit: int = 20) -> dict:
    """GET /api/brokers/top — return top brokers by transaction volume for a given period."""
    period = (period or "monthly").strip().lower()
    if period not in _VALID_PERIODS:
        raise HTTPException(status_code=400, detail="period must be one of: daily, weekly, monthly")
    limit = max(1, min(limit, 100))
    await _ensure_broker_cache()
    return {"brokers": get_top_brokers(period=period, limit=limit)}


@router.get("/api/brokers/search")
async def brokers_search(q: str = "") -> dict:
    """GET /api/brokers/search — search brokers by name or code."""
    q = (q or "")[:100]
    await _ensure_broker_cache()
    return {"brokers": search_brokers(q)}