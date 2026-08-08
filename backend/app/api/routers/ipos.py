"""IPO route — paginated IPO listings."""

from fastapi import APIRouter, HTTPException

from app.providers.cache import get_ipo_cache, set_ipo_cache
from app.providers.ipos import load_ipos

router = APIRouter()


@router.get("/api/ipos")
async def get_ipos(page: int = 1, per_page: int = 20) -> dict:
    """GET /api/ipos — return paginated list of current and upcoming IPOs."""
    if page < 1 or page > 2000:
        raise HTTPException(status_code=400, detail="page must be between 1 and 2000")
    if per_page < 1 or per_page > 100:
        raise HTTPException(status_code=400, detail="per_page must be between 1 and 100")
    if page == 1 and per_page == 20:
        cached, ts = await get_ipo_cache()
        if cached:
            return cached
    result = await load_ipos(page=page, per_page=per_page)
    if page == 1 and per_page == 20 and result.get('data'):
        await set_ipo_cache(result)
    return result