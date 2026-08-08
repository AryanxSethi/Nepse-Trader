"""Search route — fuzzy security lookup with NLP date hints."""

from fastapi import APIRouter

from app.search.fuzzy import parse_query, fuzzy_search
from app.services.live import _fetch_live_all

router = APIRouter()


@router.get("/api/search")
async def search(query: str = "") -> dict:
    """GET /api/search — fuzzy search securities by query; returns symbol, suggestions with LTP."""
    query = (query or "")[:200]
    if not query.strip():
        return {"results": [], "suggestions": []}
    parsed = await parse_query(query)
    raw_suggestions = parsed.get("suggestions") or await fuzzy_search(query)
    live = await _fetch_live_all()
    live_map = {c.get("symbol", "").upper(): c for c in live}
    enriched = []
    for r in raw_suggestions:
        sym = r["symbol"].upper()
        l = live_map.get(sym, {})
        enriched.append({**r, "ltp": l.get("ltp"), "percent_change": l.get("percent_change")})
    return {
        "symbol": enriched[0]["symbol"] if enriched else None,
        "start": parsed.get("start").isoformat() if parsed.get("start") else None,
        "end": parsed.get("end").isoformat() if parsed.get("end") else None,
        "suggestions": enriched,
    }