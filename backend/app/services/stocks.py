"""Stock data services: live candle lookup and yonepse historical fetch."""

import asyncio
import time
from datetime import date, timedelta

import httpx

from app.core.config import YONEPSE_BASE
from app.providers.yonep import fetch_live_prices
from app.services.state import merolagani_fetcher


async def _get_live_candle(symbol: str) -> dict | None:
    """Fetch today's live candle (O/H/L/C/V/T) for a symbol from Merolagani or yonepse."""
    sym = symbol.upper()
    for source_name, fetch_fn, has_open in [
        ("merolagani", merolagani_fetcher.get_live_prices, True),
        ("yonepse_live", fetch_live_prices, False),
    ]:
        try:
            items = await fetch_fn()
            for p in items:
                if p.get("symbol", "").upper() == sym:
                    ltp = p.get("ltp")
                    if ltp is None:
                        continue
                    open_price = p.get("open") or p.get("previous_close") or ltp
                    return {
                        "symbol": sym,
                        "date": date.today().isoformat(),
                        "open": float(open_price),
                        "high": float(p.get("high") or ltp),
                        "low": float(p.get("low") or ltp),
                        "close": float(ltp),
                        "volume": int(p.get("volume", 0) or 0),
                        "turnover": float(p.get("turnover", 0) or 0),
                    }
        except Exception:
            continue
    return None


async def _fetch_yonepse_history(symbol: str, max_days: int = 60) -> list[dict]:
    """Fetch historical daily prices for a symbol from the yonepse JSON archive.

    Args:
        symbol: Stock symbol to fetch.
        max_days: Maximum number of days to look back (default: 60).

    Returns:
        Sorted list of daily price dicts with O/H/L/C/V/T fields.
    """
    today = date.today()
    records = []
    seen_dates = set()
    sym_upper = symbol.upper()
    deadline = time.monotonic() + 25.0
    async with httpx.AsyncClient(timeout=10) as client:
        dates = [d for i in range(max_days) if (d := today - timedelta(days=i)).weekday() < 5]
        batch_size = 10
        for batch_start in range(0, len(dates), batch_size):
            if time.monotonic() >= deadline:
                break
            batch = dates[batch_start:batch_start + batch_size]
            tasks = []
            for d in batch:
                date_str = d.strftime("%Y-%m-%d")
                url = f"{YONEPSE_BASE}/data/ltp/daily/{date_str}.json"
                tasks.append(client.get(url))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for d, resp in zip(batch, responses):
                if isinstance(resp, Exception):
                    continue
                if resp.status_code != 200:
                    continue
                date_str = d.strftime("%Y-%m-%d")
                try:
                    data = resp.json()
                except Exception:
                    continue
                try:
                    if isinstance(data, list):
                        for row in data:
                            if row.get("symbol", "").upper() == sym_upper:
                                ds = row.get("date", date_str)
                                if ds not in seen_dates:
                                    seen_dates.add(ds)
                                    close_val = float(row.get("close") or row.get("ltp") or row.get("closingPrice") or 0)
                                    records.append({
                                        "symbol": symbol,
                                        "date": ds,
                                        "open": float(row.get("open") or close_val),
                                        "high": float(row.get("high") or close_val),
                                        "low": float(row.get("low") or close_val),
                                        "close": close_val,
                                        "volume": int(row.get("volume", 0) or 0),
                                        "turnover": float(row.get("turnover", 0) or 0),
                                    })
                                break
                    elif isinstance(data, dict):
                        series = data.get("series", {})
                        entries = series.get(symbol, []) or series.get(sym_upper, [])
                        if entries and len(entries) > 0:
                            entry = entries[0]
                            close = float(entry[1]) if len(entry) > 1 else 0
                            if date_str not in seen_dates:
                                seen_dates.add(date_str)
                                records.append({
                                    "symbol": symbol,
                                    "date": date_str,
                                    "open": float(entry[0]) if entry else close,
                                    "high": close,
                                    "low": close,
                                    "close": close,
                                    "volume": int(entry[2]) if len(entry) > 2 else 0,
                                    "turnover": float(entry[3]) if len(entry) > 3 else 0,
                                })
                except Exception:
                    continue
    records.sort(key=lambda r: r.get("date", ""))
    return records