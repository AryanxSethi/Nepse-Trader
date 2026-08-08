"""Sector routes — sector list and stocks per sector."""

from fastapi import APIRouter, HTTPException

from app.providers.sectors import get_sectors, get_stocks_by_sector

router = APIRouter()


@router.get("/api/sectors")
async def sectors_list() -> dict:
    """GET /api/sectors — return list of all market sectors."""
    return {"sectors": get_sectors()}


@router.get("/api/sectors/{sector_name}/stocks")
async def sector_stocks(sector_name: str) -> dict:
    """GET /api/sectors/{sector_name}/stocks — return stocks belonging to a given sector."""
    stocks = get_stocks_by_sector(sector_name)
    if not stocks:
        raise HTTPException(status_code=404, detail=f"Sector '{sector_name}' not found")
    return {"sector": sector_name, "stocks": stocks}