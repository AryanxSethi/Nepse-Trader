"""Market routes — overview, live data, index history, status."""

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.providers.yonep import fetch_indices, fetch_live_prices, fetch_market_summary, fetch_top_stocks
from app.services.live import _fetch_live_all, _normalize_index_name, _sort_indices
from app.services.scheduler import NPT, get_market_status
from app.services.state import LIVE_CACHE, live_cache_lock, merolagani_fetcher, sharesansar_fetcher

router = APIRouter()
logger = logging.getLogger('routers.market')


def _compute_point_change(ltp: float | None, percent_change: float | None) -> float | None:
    """Compute the absolute point change from LTP and percent change."""
    if ltp is not None and percent_change is not None and percent_change != 0:
        return round(ltp - ltp / (1 + percent_change / 100), 2)
    return None


def _enrich_item(item: dict, price_map: dict) -> dict:
    """Merge live price data into a market summary item (gainer/loser/turnover)."""
    sym = item.get("symbol", "")
    p = price_map.get(sym.upper(), {})
    ltp = item.get("ltp")
    if ltp is None:
        ltp = p.get("ltp")
    pct = item.get("percent_change")
    if pct is None:
        pct = item.get("change")
    if pct is None:
        pct = p.get("percent_change")
    if isinstance(pct, str):
        try:
            pct = float(pct.replace('%', ''))
        except (ValueError, TypeError):
            pct = None
    if pct is not None:
        pct = round(float(pct), 2)
    change = item.get("point_change") or item.get("change") or _compute_point_change(ltp, pct)
    if not isinstance(change, (int, float)):
        change = None
    return {
        "symbol": sym,
        "ltp": ltp,
        "change": change,
        "percent_change": pct,
    }


@router.get("/api/market/overview")
async def market_overview() -> dict:
    """GET /api/market/overview — return indices, summary, top gainers/losers, most active, and sectors."""
    try:
        merolagani_prices, merolagani_summary, summary_resp = await asyncio.gather(
            merolagani_fetcher.get_live_prices(),
            merolagani_fetcher.get_market_summary(),
            fetch_market_summary(),
            return_exceptions=True,
        )

        m_prices = [] if isinstance(merolagani_prices, Exception) else (merolagani_prices or [])
        m_summary = {} if isinstance(merolagani_summary, Exception) else (merolagani_summary or {})
        summary_list = [] if isinstance(summary_resp, Exception) else (summary_resp or [])

        async with live_cache_lock:
            current_indices = LIVE_CACHE.get('current_indices')
        indices_data = []
        if current_indices:
            for entry in current_indices.values():
                indices_data.append({
                    "name": entry.get("name", ""),
                    "value": entry.get("currentValue"),
                    "change": entry.get("change"),
                    "percent_change": entry.get("perChange"),
                })
        indices_data = _sort_indices(indices_data)

        market_summary = {"turnover": None, "trades": None, "scrips": None, "market_cap": None}
        for item in summary_list:
            detail = (item.get("detail") or "").lower()
            val = item.get("value")
            if "turnover" in detail:
                market_summary["turnover"] = val
            elif "transaction" in detail or "trades" in detail:
                market_summary["trades"] = int(val) if val else None
            elif "scrips" in detail:
                market_summary["scrips"] = int(val) if val else None
            elif "market capitalization" in detail and "float" not in detail:
                market_summary["market_cap"] = val

        price_map = {p.get("symbol", "").upper(): p for p in m_prices}

        gainers = m_summary.get('gainers', [])
        losers = m_summary.get('losers', [])
        sectors = m_summary.get('sectors', [])
        active = m_summary.get('turnovers', [])

        if not gainers and m_prices:
            sorted_by_change = sorted(
                [p for p in m_prices if p.get('percent_change') is not None],
                key=lambda p: p.get('percent_change', 0), reverse=True
            )
            gainers = [_enrich_item(p, price_map) for p in sorted_by_change[:10] if p.get('percent_change', 0) >= 0]
            losers = [_enrich_item(p, price_map) for p in sorted_by_change[-10:] if p.get('percent_change', 0) < 0]
            losers.reverse()

        if not active and m_prices:
            with_turnover = [p for p in m_prices if p.get('turnover', 0) > 0]
            if with_turnover:
                with_turnover.sort(key=lambda p: p.get('turnover', 0), reverse=True)
            active = [{"symbol": p.get("symbol", ""), "ltp": p.get("ltp"), "turnover": p.get("turnover")} for p in (with_turnover or m_prices[:10])]

        tops: dict | None = None
        if not gainers:
            _, tops_resp = await asyncio.gather(
                fetch_live_prices(),
                fetch_top_stocks(),
                return_exceptions=True,
            )
            tops = None if isinstance(tops_resp, Exception) else tops_resp

        if not gainers and tops is not None:
            gainers = [_enrich_item(g, price_map) for g in (tops.get("top_gainer") or [])]
            losers = [_enrich_item(g, price_map) for g in (tops.get("top_loser") or [])]
            if not active:
                active = [
                    {"symbol": g.get("symbol", ""), "turnover": g.get("turnover"), "price": g.get("closingPrice")}
                    for g in (tops.get("top_turnover") or [])
                ]

        if gainers and not gainers[0].get("ltp"):
            gainers = [_enrich_item(g, price_map) for g in m_summary.get('gainers', [])]
        if losers and not losers[0].get("ltp"):
            losers = [_enrich_item(g, price_map) for g in m_summary.get('losers', [])]

        return {
            "indices": indices_data,
            "summary": market_summary,
            "top_gainers": gainers,
            "top_losers": losers,
            "most_active": active,
            "sectors": sectors,
            "_fetched_at": LIVE_CACHE.get("timestamp").isoformat() if LIVE_CACHE.get("timestamp") else None,
        }
    except Exception as e:
        logger.error("Market overview failed: %s", e)
        raise HTTPException(status_code=502, detail="Market data unavailable")


@router.get("/api/market/index-history")
async def market_index_history() -> dict:
    """GET /api/market/index-history — return merged daily, hourly, and 30-second index history with current snapshot."""
    async with live_cache_lock:
        daily = LIVE_CACHE.get("index_history", [])
        hourly = LIVE_CACHE.get("index_hourly", [])
        tail = LIVE_CACHE.get("index_30s", [])
        current_index = LIVE_CACHE.get("current_index")
        current_indices = LIVE_CACHE.get("current_indices")

    merged = []
    if daily:
        merged.extend(daily)
    if hourly:
        daily_ts = daily[-1].get('time', 0) if daily else 0
        for p in hourly:
            if p.get('time', 0) > daily_ts:
                merged.append(p)
    if tail:
        hourly_ts = hourly[-1].get('time', 0) if hourly else 0
        for p in tail:
            if p.get('time', 0) > hourly_ts:
                merged.append(p)

    now_npt = datetime.now(NPT)
    today_start_npt = datetime(now_npt.year, now_npt.month, now_npt.day, tzinfo=NPT)
    today_ts = int(today_start_npt.timestamp())
    today_intraday = [p for p in (tail or []) if p.get('time', 0) >= today_ts]

    return {
        "points": merged,
        "current": current_index,
        "snapshots": tail[-60:] if tail else [],
        "today": today_intraday,
        "indices": current_indices,
        "last_updated": LIVE_CACHE.get("last_updated"),
    }


@router.get("/api/market/live")
async def market_live() -> dict:
    """GET /api/market/live — return live prices, indices, gainers, losers, turnovers, and sectors."""
    try:
        prices_resp, summary_resp, ss_resp = await asyncio.gather(
            merolagani_fetcher.get_live_prices(),
            merolagani_fetcher.get_market_summary(),
            sharesansar_fetcher.get_live_trading(),
            return_exceptions=True,
        )
        prices = [] if isinstance(prices_resp, Exception) else (prices_resp or [])
        summary = {} if isinstance(summary_resp, Exception) else (summary_resp or {})
        ss_data = {} if isinstance(ss_resp, Exception) else (ss_resp or {})

        ss_prices = ss_data.get('prices', [])
        if ss_prices:
            ss_by_symbol = {p['symbol'].upper(): p for p in ss_prices if 'symbol' in p and p['symbol']}
            for p in prices:
                sym = p.get('symbol', '').upper()
                ss = ss_by_symbol.get(sym)
                if ss:
                    if ss.get('volume') is not None:
                        p['volume'] = ss['volume']
                    if ss.get('prev_close') is not None:
                        p['prev_close'] = ss['prev_close']

        async with live_cache_lock:
            current_indices = LIVE_CACHE.get('current_indices')
        indices_data = []
        if current_indices:
            for entry in current_indices.values():
                indices_data.append({
                    "name": entry.get("name", ""),
                    "value": entry.get("currentValue"),
                    "change": entry.get("change"),
                    "percent_change": entry.get("perChange"),
                })

        ss_indices = ss_data.get('indices', [])
        existing_names = {i['name'].lower() for i in indices_data}
        for idx in ss_indices:
            name = _normalize_index_name(idx.get('name', ''))
            if name.lower() not in existing_names:
                indices_data.append({
                    'name': name,
                    'value': idx.get('value'),
                    'change': None,
                    'percent_change': idx.get('percent_change'),
                })
        indices_data = _sort_indices(indices_data)

        turnovers = summary.get('turnovers', [])
        if turnovers:
            turnovers.sort(key=lambda t: t.get('turnover', 0), reverse=True)

        return {
            "indices": indices_data,
            "prices": prices,
            "gainers": summary.get('gainers', []),
            "losers": summary.get('losers', []),
            "turnovers": turnovers,
            "sectors": summary.get('sectors', []),
            "timestamp": LIVE_CACHE.get("timestamp"),
        }
    except Exception as e:
        logger.error("Market live failed: %s", e)
        raise HTTPException(status_code=502, detail="Market data unavailable")


@router.get("/api/market/status")
async def market_status() -> dict:
    """GET /api/market/status — return market open/close status and schedule."""
    s = get_market_status()
    return {
        "is_open": s["is_open"],
        "as_of": s["as_of"],
        "next_open": s["next_open"],
        "next_close": s["next_close"],
    }