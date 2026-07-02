import httpx
from datetime import date
from typing import Optional

YONEPSE_BASE = "https://shubhamnpk.github.io/yonepse"


async def fetch_all_securities() -> list[dict]:
    url = f"{YONEPSE_BASE}/data/nepse_data.json"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return []


async def fetch_live_prices() -> list[dict]:
    url = f"{YONEPSE_BASE}/data/market/live.json"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return []


async def fetch_market_summary() -> list[dict]:
    url = f"{YONEPSE_BASE}/data/market/summary.json"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return []


async def fetch_top_stocks() -> dict:
    url = f"{YONEPSE_BASE}/data/market/top_stocks.json"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return {}


async def fetch_indices() -> list[dict]:
    url = f"{YONEPSE_BASE}/data/market/indices.json"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return []


async def fetch_ltp_history(symbol: str, target_date: date) -> Optional[dict]:
    try:
        date_str = target_date.strftime("%Y-%m-%d")
        url = f"{YONEPSE_BASE}/data/ltp/daily/{date_str}.json"
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if isinstance(data, list):
                for row in data:
                    if row.get("symbol", "").upper() == symbol.upper():
                        return row
    except Exception:
        pass
    return None


async def fetch_market_status() -> dict:
    url = f"{YONEPSE_BASE}/data/market/status.json"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(url)
            if resp.status_code != 200:
                return {"is_open": False, "last_checked": None}
            return resp.json()
    except Exception:
        return {"is_open": False, "last_checked": None}
