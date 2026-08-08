"""Portfolio routes — holdings CRUD with live P&L."""

from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.db.models import PortfolioHolding
from app.db.session import async_session
from app.services.live import _fetch_live_all

router = APIRouter()


def enrich_holding(holding: dict, live_item: dict) -> dict:
    """Compute P&L fields for a single holding from a live quote item.

    Pure helper, safe with missing/empty upstream data.
    """
    ltp_raw = live_item.get("ltp")
    try:
        ltp = float(ltp_raw) if ltp_raw not in (None, "") else None
    except (TypeError, ValueError):
        ltp = None
    invested = holding["quantity"] * holding["avg_cost"]
    current_value = (holding["quantity"] * ltp) if ltp is not None else None
    pl = (current_value - invested) if current_value is not None else None
    pl_pct = ((current_value / invested - 1) * 100) if current_value is not None else None
    return {
        **holding,
        "ltp": ltp,
        "name": live_item.get("name", ""),
        "invested": round(invested, 2),
        "current_value": round(current_value, 2) if current_value is not None else None,
        "pl": round(pl, 2) if pl is not None else None,
        "pl_percent": round(pl_pct, 2) if pl_pct is not None else None,
    }


@router.get("/api/portfolio")
async def get_portfolio() -> dict:
    """GET /api/portfolio — return portfolio holdings with live prices, P&L calculations."""
    async with async_session() as session:
        rows = await session.execute(
            select(PortfolioHolding).order_by(PortfolioHolding.created_at.desc()).limit(500)
        )
        holdings = [r.to_dict() for r in rows.scalars().all()]

    if not holdings:
        return {"holdings": [], "total_invested": 0, "total_value": 0, "total_pl": 0, "total_pl_percent": 0}

    symbols = [h["symbol"] for h in holdings]
    live = await _fetch_live_all()
    live_map = {c.get("symbol", "").upper(): c for c in live}

    total_invested = 0.0
    total_value = 0.0
    enriched = []
    for h in holdings:
        item = enrich_holding(h, live_map.get(h["symbol"].upper(), {}))
        total_invested += item["invested"]
        if item["current_value"] is not None:
            total_value += item["current_value"]
        enriched.append(item)

    total_pl = total_value - total_invested
    total_pl_pct = ((total_value / total_invested - 1) * 100) if total_invested > 0 else 0

    return {
        "holdings": enriched,
        "total_invested": round(total_invested, 2),
        "total_value": round(total_value, 2),
        "total_pl": round(total_pl, 2),
        "total_pl_percent": round(total_pl_pct, 2),
    }


@router.post("/api/portfolio/holdings")
async def add_holding(symbol: str = "", quantity: int = 0, avg_cost: float = 0, buy_date: str = "", notes: str = "") -> dict:
    """POST /api/portfolio/holdings — add a new portfolio holding.

    Args:
        symbol: Stock symbol.
        quantity: Number of shares held.
        avg_cost: Average cost per share.
        buy_date: Purchase date (YYYY-MM-DD).
        notes: Optional notes.

    Returns:
        The created holding record.
    """
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol is required")
    symbol = symbol.strip().upper()
    if len(symbol) > 30:
        raise HTTPException(status_code=400, detail="symbol must be 30 characters or fewer")
    if quantity <= 0 or quantity > 1_000_000_000:
        raise HTTPException(status_code=400, detail="quantity must be between 1 and 1,000,000,000")
    if avg_cost <= 0 or avg_cost > 100_000_000:
        raise HTTPException(status_code=400, detail="avg_cost must be between 0 and 100,000,000")
    if len(notes) > 2000:
        raise HTTPException(status_code=400, detail="notes must be 2000 characters or fewer")
    parsed_date = None
    if buy_date:
        try:
            parsed_date = date.fromisoformat(buy_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="buy_date must be valid (YYYY-MM-DD)")
    async with async_session() as session:
        h = PortfolioHolding(
            symbol=symbol,
            quantity=quantity,
            avg_cost=avg_cost,
            buy_date=parsed_date,
            notes=notes,
        )
        session.add(h)
        await session.commit()
        await session.refresh(h)
        return h.to_dict()


@router.put("/api/portfolio/holdings/{holding_id}")
async def update_holding(holding_id: int, quantity: int = 0, avg_cost: float = 0, notes: str = "") -> dict:
    """PUT /api/portfolio/holdings/{holding_id} — update quantity, avg_cost, or notes for a holding."""
    async with async_session() as session:
        result = await session.execute(select(PortfolioHolding).where(PortfolioHolding.id == holding_id))
        h = result.scalar_one_or_none()
        if not h:
            raise HTTPException(status_code=404, detail="Holding not found")
        if quantity > 0:
            h.quantity = quantity
        if avg_cost > 0:
            h.avg_cost = avg_cost
        h.notes = notes
        await session.commit()
        await session.refresh(h)
        return h.to_dict()


@router.delete("/api/portfolio/holdings/{holding_id}")
async def delete_holding(holding_id: int) -> dict:
    """DELETE /api/portfolio/holdings/{holding_id} — remove a portfolio holding by ID."""
    async with async_session() as session:
        result = await session.execute(select(PortfolioHolding).where(PortfolioHolding.id == holding_id))
        h = result.scalar_one_or_none()
        if not h:
            raise HTTPException(status_code=404, detail="Holding not found")
        await session.delete(h)
        await session.commit()
        return {"status": "deleted"}