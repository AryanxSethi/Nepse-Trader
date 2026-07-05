import asyncio
import pandas as pd
import httpx
import json
import logging
import re
from datetime import datetime, timedelta, date, timezone
from contextlib import asynccontextmanager
from database import engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('main')

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, desc

from config import OLLAMA_URL, OLLAMA_MODEL
from database import init_db, async_session
from models import Security, DailyPrice, Signal, PortfolioHolding
from data.fetcher import (
    fetch_top_stocks,
    fetch_indices, fetch_all_securities,
    fetch_live_prices,
    fetch_market_summary,
)
from data.seeder import seed_securities
from data.updater import run_daily_update
from data.market_scheduler import MarketScheduler, get_market_status
from data.merolagani_fetcher import MerolaganiFetcher
from data.sharesansar_fetcher import SharesansarFetcher
from analysis.indicators import compute_indicators, compute_signal
from analysis.signals import generate_signals
from analysis.backtest import run_backtest
from search.fuzzy import fuzzy_search, parse_query, extract_symbols, set_security_cache
from guide.knowledge_base import find_guide_entry, get_popular_entries
from guide.broker_directory import search_brokers, get_top_brokers, _ensure_brokers as _ensure_broker_cache
from data.fetcher_sectors import get_sectors, get_stocks_by_sector
from data.fetcher_ipo import load_ipos
from data.cache import (
    data_cache_get, data_cache_set,
    get_market_cache, set_market_cache,
    get_ipo_cache, set_ipo_cache,
    prewarm_caches, persist_caches_on_exit,
    persist_live_cache, load_live_cache,
)

LIVE_CACHE = {"data": [], "timestamp": None, "index_history": [], "current_index": None,
               "current_indices": None, "index_hourly": [], "index_30s": []}
live_cache_lock = asyncio.Lock()

scheduler = MarketScheduler()
merolagani_fetcher = MerolaganiFetcher()
sharesansar_fetcher = SharesansarFetcher()


def _to_timestamp(dt: date | datetime) -> int:
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


async def seed_daily_history(cache: dict):
    try:
        async with async_session() as session:
            result = await session.execute(
                select(DailyPrice)
                .where(DailyPrice.symbol == 'NEPSE')
                .order_by(DailyPrice.date.desc())
                .limit(35)
            )
            records = [r.to_dict() for r in result.scalars().all()]
        if not records:
            records = []
    except Exception:
        records = []

    if not records:
        try:
            html = await merolagani_fetcher.get_index_history_page()
            if html:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                for table in soup.find_all('table'):
                    rows = table.find_all('tr')
                    parsed = []
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            try:
                                date_text = cells[1].get_text(strip=True) if len(cells) >= 2 else ''
                                value_text = cells[2].get_text(strip=True) if len(cells) >= 3 else ''
                                if date_text and value_text:
                                    dt = datetime.strptime(date_text, '%Y/%m/%d')
                                    parsed.append({'time': _to_timestamp(dt), 'value': float(value_text.replace(',', ''))})
                            except (ValueError, IndexError):
                                continue
                    if len(parsed) >= 5:
                        parsed.reverse()
                        async with live_cache_lock:
                            cache['index_history'] = parsed[-35:]
                        logger.info("Seeded index_history with %d daily points from Indices.aspx", len(parsed))
                        return
        except Exception as e:
            logger.warning("Indices.aspx scrape failed: %s", e)

    if records:
        records.sort(key=lambda r: r.get('date', ''))
        history = []
        for r in records:
            dt = r.get('date', '')
            if isinstance(dt, str):
                dt = date.fromisoformat(dt)
            close = r.get('close') or r.get('ltp', 0)
            if close:
                history.append({'time': _to_timestamp(dt), 'value': float(close)})
        async with live_cache_lock:
            cache['index_history'] = history[-35:]
        logger.info("Seeded index_history with %d daily points from DB", len(history))


async def start_index_polling(cache: dict, ever_had_signalr: bool = False):
    async def _poll():
        nonlocal ever_had_signalr
        is_open = False
        while True:
            try:
                status = get_market_status()
                is_open = status.get('is_open', False)
            except Exception:
                is_open = False

            try:
                all_indices = None
                if is_open:
                    try:
                        all_indices = await merolagani_fetcher.get_live_index()
                        if all_indices:
                            ever_had_signalr = True
                    except Exception as e:
                        logger.warning("Merolagani SignalR index poll failed: %s", e)

                if not all_indices and not ever_had_signalr:
                    yonepse_indices = await fetch_indices()
                    if yonepse_indices:
                        all_indices = {}
                        for idx in yonepse_indices:
                            name = idx.get('index', '')
                            key = 'NEPSE' if name.upper() == 'NEPSE INDEX' else name
                            all_indices[key] = {
                                'name': key,
                                'currentValue': idx.get('currentValue'),
                                'change': idx.get('change'),
                                'perChange': idx.get('perChange'),
                            }

                if all_indices:
                    now_utc = datetime.now(timezone.utc)
                    now_npt = now_utc + timedelta(hours=5, minutes=45)

                    vals: dict[str, float | None] = {}
                    for name, entry in all_indices.items():
                        vals[name] = entry.get('currentValue')

                    async with live_cache_lock:
                        tail = cache.setdefault('index_30s', [])
                        prev = tail[-1] if tail else None
                        if is_open or not prev:
                            prev_vals = prev.get('values', {}) if prev else {}
                            if any(vals.get(k) != prev_vals.get(k) for k in vals):
                                tail.append({'time': _to_timestamp(now_utc), 'values': dict(vals)})
                                if len(tail) > 480:
                                    cache['index_30s'] = tail[-480:]

                        hourly = cache.setdefault('index_hourly', [])
                        hour_key = _to_timestamp(now_npt.replace(minute=0, second=0, microsecond=0))
                        if not hourly or hourly[-1].get('time') != hour_key:
                            hourly.append({'time': hour_key, 'values': dict(vals)})
                            nv = vals.get('NEPSE')
                            if nv is not None:
                                logger.info("Index hourly point: %s = %.2f",
                                            now_npt.strftime('%Y-%m-%d %H:00'), nv)

                        cache['current_indices'] = all_indices
                        n = all_indices.get('NEPSE', {})
                        cache['current_index'] = {
                            'name': 'NEPSE Index',
                            'currentValue': n.get('currentValue'),
                            'change': n.get('change'),
                            'perChange': n.get('perChange'),
                        } if n.get('currentValue') is not None else None
            except Exception as e:
                logger.warning('Index poll failed: %s', e)

            await asyncio.sleep(15 if is_open else 300)
    asyncio.create_task(_poll())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_securities()
    try:
        securities_data = await fetch_all_securities()
        symbols = []
        seen = set()
        for item in securities_data:
            sym = str(item.get("symbol", "")).strip().upper()
            name = str(item.get("name", "")).strip()
            if sym and sym not in seen:
                seen.add(sym)
                symbols.append({"symbol": sym, "name": name})
        set_security_cache(symbols)
    except Exception as e:
        logger.warning("Failed to load securities cache: %s", e)
        symbols = []
        set_security_cache(symbols)
    try:
        count = await run_daily_update()
        if count > 0:
            logger.info("Inserted %d new daily price records", count)
    except Exception as e:
        logger.warning("Daily update failed: %s", e)
    try:
        await generate_signals()
        logger.info("Signals generated")
    except Exception as e:
        logger.warning("Signal generation failed: %s", e)
    await prewarm_caches()
    try:
        await _ensure_broker_cache()
    except Exception as e:
        logger.warning("Failed to prewarm broker cache: %s", e)
    disk_live = await load_live_cache()
    async with live_cache_lock:
        for k, v in disk_live.items():
            if v is not None:
                LIVE_CACHE[k] = v
        has_signalr = bool(LIVE_CACHE.get('current_indices'))
    scheduler.start()
    await seed_daily_history(LIVE_CACHE)
    await start_index_polling(LIVE_CACHE, has_signalr)
    yield
    async with live_cache_lock:
        await persist_live_cache(LIVE_CACHE)
    await persist_caches_on_exit()
    await merolagani_fetcher.stop()
    await sharesansar_fetcher.stop()
    await scheduler.stop()
    await engine.dispose()


app = FastAPI(title="NEPSE Trader", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_CONTROL_ROUTES = {
    "/api/ipos": "public, max-age=60",
    "/api/securities": "public, max-age=300",
    "/api/market/status": "public, max-age=30",
    "/api/brokers/top": "public, max-age=300",
    "/api/brokers/search": "public, max-age=300",
    "/api/sectors": "public, max-age=300",
}

@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path in CACHE_CONTROL_ROUTES:
        response.headers["Cache-Control"] = CACHE_CONTROL_ROUTES[path]
    return response


async def _fetch_live_all() -> list[dict]:
    cached_data, cached_ts = await get_market_cache()
    try:
        data = await fetch_all_securities()
        if data:
            await set_market_cache(data)
            async with live_cache_lock:
                LIVE_CACHE["data"] = data
                LIVE_CACHE["timestamp"] = datetime.now(timezone.utc)
            return data
    except Exception as e:
        logger.warning("fetch_all_securities failed: %s", e)

    if cached_data:
        async with live_cache_lock:
            LIVE_CACHE["data"] = cached_data
            LIVE_CACHE["timestamp"] = cached_ts
        return cached_data
    return []


@app.get("/api/companies")
async def get_companies():
    data = await _fetch_live_all()
    return {
        "count": len(data),
        "companies": [
            {
                "symbol": c.get("symbol", ""),
                "name": c.get("name", ""),
                "ltp": c.get("ltp"),
                "change": c.get("change"),
                "percent_change": c.get("percent_change"),
                "volume": c.get("volume"),
                "turnover": c.get("turnover"),
                "trades": c.get("trades"),
            }
            for c in data
        ],
    }


@app.get("/api/securities")
async def get_securities(search: str = ""):
    async with async_session() as session:
        if search:
            result = await session.execute(
                select(Security).where(Security.symbol.ilike(f"%{search}%") | Security.name.ilike(f"%{search}%"))
            )
        else:
            result = await session.execute(select(Security).order_by(Security.symbol))
        return [{"symbol": s.symbol, "name": s.name} for s in result.scalars().all()]


@app.get("/api/search")
async def search(query: str = ""):
    if not query:
        return {"results": [], "suggestions": []}
    parsed = parse_query(query)
    raw_suggestions = parsed.get("suggestions") or fuzzy_search(query)
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





def _compute_point_change(ltp: float | None, percent_change: float | None) -> float | None:
    if ltp is not None and percent_change is not None and percent_change != 0:
        return round(ltp - ltp / (1 + percent_change / 100), 2)
    return None

def _enrich_item(item: dict, price_map: dict) -> dict:
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


@app.get("/api/market/overview")
async def market_overview():
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
        }
    except Exception as e:
        logger.error("Market overview failed: %s", e)
        raise HTTPException(status_code=502, detail="Market data unavailable")


@app.get("/api/market/index-history")
async def market_index_history():
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

    return {
        "points": merged,
        "current": current_index,
        "snapshots": tail[-60:] if tail else [],
        "indices": current_indices,
    }


@app.get("/api/market/live")
async def market_live():
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
            if idx.get('name', '').lower() not in existing_names:
                indices_data.append({
                    'name': idx['name'],
                    'value': idx['value'],
                    'change': None,
                    'percent_change': idx.get('percent_change'),
                })

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
        }
    except Exception as e:
        logger.error("Market live failed: %s", e)
        raise HTTPException(status_code=502, detail="Market data unavailable")


@app.get("/api/market/status")
async def market_status():
    s = get_market_status()
    return {
        "is_open": s["is_open"],
        "as_of": s["as_of"],
        "next_open": s["next_open"],
        "next_close": s["next_close"],
    }


async def _get_live_candle(symbol: str) -> dict | None:
    sym = symbol.upper()
    for source_name, fetch_fn, has_open in [
        ("yonepse_live", fetch_live_prices, False),
        ("merolagani", merolagani_fetcher.get_live_prices, True),
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


@app.get("/api/stocks/{symbol}/history")
async def stock_history(symbol: str, start: str = "", end: str = ""):
    sym = symbol.upper()
    today = date.today()
    try:
        start_date = date.fromisoformat(start) if start else today - timedelta(days=90)
        end_date = date.fromisoformat(end) if end else today
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    async with async_session() as session:
        rows = await session.execute(
            select(DailyPrice)
            .where(DailyPrice.symbol == sym, DailyPrice.date >= start_date, DailyPrice.date <= end_date)
            .order_by(DailyPrice.date)
            .limit(1000)
        )
        records = [r.to_dict() for r in rows.scalars().all()]

    if not records:
        return {"prices": [], "indicators": {}, "signal": None}

    try:
        market_status = get_market_status()
        today_candle = await _get_live_candle(sym)
        if (today_candle and market_status.get('is_open')
            and (not records or records[-1].get("date") != today.isoformat())):
            records.append(today_candle)

        df = pd.DataFrame(records)
        indicators = compute_indicators(df)
        sig_type, confidence, reason = compute_signal(indicators)
    except Exception:
        return {"prices": records, "indicators": {}, "signal": {"type": "HOLD", "confidence": 50, "reason": "Insufficient data for technical analysis"}}

    return {
        "prices": records,
        "indicators": {k: v for k, v in indicators.items() if v is not None},
        "signal": {"type": sig_type, "confidence": confidence, "reason": reason},
    }


@app.get("/api/stocks/{symbol}/detail")
async def stock_detail(symbol: str):
    detail = await merolagani_fetcher.get_company_detail(symbol)
    if not detail:
        detail = {}

    try:
        ss_price, ss_detail = await asyncio.gather(
            sharesansar_fetcher.get_today_share_price_for_symbol(symbol),
            sharesansar_fetcher.get_company_detail(symbol),
            return_exceptions=True,
        )
        ss_price_data = {} if isinstance(ss_price, Exception) else (ss_price or {})
        ss_detail_data = {} if isinstance(ss_detail, Exception) else (ss_detail or {})
    except Exception as e:
        logger.warning("Sharesansar detail fetch failed for %s: %s", symbol, e)
        ss_price_data = {}
        ss_detail_data = {}

    if ss_price_data.get('vwap') is not None:
        detail['vwap'] = str(ss_price_data['vwap'])
    if ss_price_data.get('prev_close') is not None:
        detail['prev_close'] = str(ss_price_data['prev_close'])
    if ss_price_data.get('volume') is not None:
        detail['volume'] = str(int(ss_price_data['volume']))
    if ss_price_data.get('avg_180d') is not None:
        detail['180d_avg'] = str(ss_price_data['avg_180d'])
    if ss_price_data.get('avg_120d') is not None:
        if not detail.get('120d_avg'):
            detail['120d_avg'] = str(ss_price_data['avg_120d'])
    if ss_price_data.get('confidence_score') is not None:
        detail['confidence_score'] = ss_price_data['confidence_score']
    if ss_price_data.get('high_52w') is not None:
        if not detail.get('52w_high'):
            detail['52w_high'] = str(ss_price_data['high_52w'])
    if ss_price_data.get('low_52w') is not None:
        if not detail.get('52w_low'):
            detail['52w_low'] = str(ss_price_data['low_52w'])

    pivot = ss_detail_data.get('pivot')
    if pivot:
        for k, v in pivot.items():
            detail[f'pivot_{k}'] = str(v)
    moving = ss_detail_data.get('moving')
    if moving:
        for period_key, period_data in moving.items():
            if isinstance(period_data, dict):
                detail[f'{period_key}_signal'] = period_data.get('signal')
                if period_data.get('value') is not None:
                    detail[f'{period_key}_value'] = str(period_data['value'])

    async with async_session() as session:
        result = await session.execute(
            select(Security).where(Security.symbol == symbol.upper())
        )
        sec = result.scalar_one_or_none()
        if sec and sec.sector and not detail.get("sector"):
            detail["sector"] = sec.sector
    if not detail.get("sector"):
        from data.fetcher_sectors import get_sector_for_symbol
        s = get_sector_for_symbol(symbol.upper())
        if s:
            detail["sector"] = s
    return detail


@app.get("/api/stocks/{symbol}/floorsheet")
async def stock_floorsheet(symbol: str):
    try:
        rows = await sharesansar_fetcher.get_floorsheet(symbol)
        return {"floorsheet": (rows or [])[:200]}
    except Exception as e:
        logger.error("Floorsheet fetch failed for %s: %s", symbol, e)
        return {"floorsheet": []}


@app.get("/api/signals")
async def get_signals(signal_type: str = ""):
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


@app.post("/api/signals/generate")
async def trigger_signals():
    try:
        await generate_signals()
        return {"status": "done"}
    except Exception as e:
        logger.error("Signal generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Signal generation failed")


@app.post("/api/backtest")
async def backtest(symbol: str = "NABIL", fast_ma: int = 20, slow_ma: int = 50, days: int = 365):
    result = await run_backtest(symbol, fast_ma, slow_ma, days)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/portfolio")
async def get_portfolio():
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
        l = live_map.get(h["symbol"].upper(), {})
        ltp = l.get("ltp")
        invested = h["quantity"] * h["avg_cost"]
        current_value = (h["quantity"] * ltp) if ltp else None
        pl = (current_value - invested) if current_value is not None else None
        pl_pct = ((current_value / invested - 1) * 100) if current_value is not None else None

        total_invested += invested
        if current_value is not None:
            total_value += current_value

        enriched.append({
            **h,
            "ltp": ltp,
            "name": l.get("name", ""),
            "invested": round(invested, 2),
            "current_value": round(current_value, 2) if current_value is not None else None,
            "pl": round(pl, 2) if pl is not None else None,
            "pl_percent": round(pl_pct, 2) if pl_pct is not None else None,
        })

    total_pl = total_value - total_invested
    total_pl_pct = ((total_value / total_invested - 1) * 100) if total_invested > 0 else 0

    return {
        "holdings": enriched,
        "total_invested": round(total_invested, 2),
        "total_value": round(total_value, 2),
        "total_pl": round(total_pl, 2),
        "total_pl_percent": round(total_pl_pct, 2),
    }


@app.post("/api/portfolio/holdings")
async def add_holding(symbol: str = "", quantity: int = 0, avg_cost: float = 0, buy_date: str = "", notes: str = ""):
    if not symbol or quantity <= 0 or avg_cost <= 0:
        raise HTTPException(status_code=400, detail="symbol, quantity (>0), and avg_cost (>0) are required")
    async with async_session() as session:
        h = PortfolioHolding(
            symbol=symbol.upper(),
            quantity=quantity,
            avg_cost=avg_cost,
            buy_date=date.fromisoformat(buy_date) if buy_date else None,
            notes=notes,
        )
        session.add(h)
        await session.commit()
        await session.refresh(h)
        return h.to_dict()


@app.put("/api/portfolio/holdings/{holding_id}")
async def update_holding(holding_id: int, quantity: int = 0, avg_cost: float = 0, notes: str = ""):
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


@app.delete("/api/portfolio/holdings/{holding_id}")
async def delete_holding(holding_id: int):
    async with async_session() as session:
        result = await session.execute(select(PortfolioHolding).where(PortfolioHolding.id == holding_id))
        h = result.scalar_one_or_none()
        if not h:
            raise HTTPException(status_code=404, detail="Holding not found")
        await session.delete(h)
        await session.commit()
        return {"status": "deleted"}


@app.get("/api/stocks/compare")
async def compare_stocks(symbols: str = ""):
    if not symbols:
        raise HTTPException(status_code=400, detail="Provide comma-separated symbols")
    
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if len(sym_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 symbols")
    if len(sym_list) > 5:
        sym_list = sym_list[:5]
    
    live = await _fetch_live_all()
    live_map = {c.get("symbol", "").upper(): c for c in live}
    
    records_by_symbol = {}
    try:
        async with async_session() as session:
            rows = await session.execute(
                select(DailyPrice)
                .where(DailyPrice.symbol.in_(sym_list))
                .order_by(DailyPrice.date)
            )
            for r in rows.scalars().all():
                records_by_symbol.setdefault(r.symbol, []).append(r.to_dict())
    except Exception as e:
        logger.debug("Failed to batch query daily prices: %s", e)

    market_status = get_market_status()

    result = []
    for sym in sym_list:
        l = live_map.get(sym, {})
        item = {
            "symbol": sym,
            "name": l.get("name", ""),
            "ltp": l.get("ltp"),
            "change": l.get("change"),
            "percent_change": l.get("percent_change"),
            "volume": l.get("volume"),
            "turnover": l.get("turnover"),
            "market_cap": l.get("market_cap"),
        }
        try:
            records = records_by_symbol.get(sym, [])
            if len(records) < 2:
                records = await _fetch_yonepse_history(sym, 120)
            if market_status.get('is_open'):
                today_candle = await _get_live_candle(sym)
                if today_candle and (not records or records[-1].get("date") != date.today().isoformat()):
                    records.append(today_candle)
            if len(records) >= 2:
                records.sort(key=lambda r: r.get("date", ""))
                item["prices"] = records
            if len(records) >= 20:
                df = pd.DataFrame(records)
                indicators = compute_indicators(df)
                sig_type, confidence, reason = compute_signal(indicators)
                item["rsi"] = indicators.get("rsi")
                item["macd"] = indicators.get("macd")
                item["macd_signal"] = indicators.get("macd_signal")
                item["sma20"] = indicators.get("sma20")
                item["sma50"] = indicators.get("sma50")
                item["adx"] = indicators.get("adx")
                item["trend"] = indicators.get("trend")
                item["signal_type"] = sig_type
                item["signal_confidence"] = confidence
        except Exception as e:
            logger.debug("Failed to compute indicators for %s: %s", sym, e)
        result.append(item)
    
    return {"symbols": sym_list, "comparison": result}


async def _fetch_yonepse_history(symbol: str, max_days: int = 120) -> list[dict]:
    today = date.today()
    records = []
    seen_dates = set()
    sym_upper = symbol.upper()
    async with httpx.AsyncClient(timeout=10) as client:
        for i in range(max_days):
            d = today - timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            url = f"https://shubhamnpk.github.io/yonepse/data/ltp/daily/{date_str}.json"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if isinstance(data, list):
                    for row in data:
                        if row.get("symbol", "").upper() == sym_upper:
                            ds = row.get("date", date_str)
                            if ds not in seen_dates:
                                seen_dates.add(ds)
                                close_val = float(row.get("close") or row.get("ltp") or row.get("closingPrice") or 0)
                                records.append({
                                    "symbol": sym,
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


@app.get("/api/ipos")
async def get_ipos(page: int = 1, per_page: int = 20):
    if page == 1 and per_page == 20:
        cached, ts = await get_ipo_cache()
        if cached:
            return cached
    result = await load_ipos(page=page, per_page=per_page)
    if page == 1 and per_page == 20 and result.get('data'):
        await set_ipo_cache(result)
    return result


@app.get("/api/brokers/top")
async def brokers_top(period: str = "monthly", limit: int = 20):
    await _ensure_broker_cache()
    return {"brokers": get_top_brokers(period=period, limit=limit)}


@app.get("/api/brokers/search")
async def brokers_search(q: str = ""):
    await _ensure_broker_cache()
    return {"brokers": search_brokers(q)}


@app.get("/api/sectors")
async def sectors_list():
    return {"sectors": get_sectors()}


@app.get("/api/sectors/{sector_name}/stocks")
async def sector_stocks(sector_name: str):
    stocks = get_stocks_by_sector(sector_name)
    return {"sector": sector_name, "stocks": stocks}


GUIDE_SYSTEM_PROMPT = (
    "You are a NEPSE trading data analyst assistant. Your role is to analyze "
    "provided market data and explain what the numbers indicate.\n\n"
    "SCOPE:\n"
    "- Only answer NEPSE stocks, trading, investing, regulations, "
    "brokers, demat accounts, MeroShare, technical/fundamental analysis, fees, "
    "and taxes in Nepal.\n"
    "- If asked about anything else, politely decline.\n\n"
    "TONE & CONVERSATION:\n"
    "- Be friendly, warm, and approachable. You are a helpful assistant, not a data report.\n"
    "- Greetings (\"hi\", \"hello\", \"good morning\"): respond warmly and offer help.\n"
    "  Example: \"Hi! I can look up stock data, explain indicators, or give a market overview. What would you like to know?\"\n"
    "- \"Thank you\" / \"thanks\": respond \"You're welcome!\" and offer follow-up help.\n"
    "- \"Explain more\" / \"elaborate\" / \"tell me more about\": expand on your previous answer with additional detail or examples — do not just repeat the same info.\n"
    "- \"Please\": acknowledge politely in your response.\n"
    "- End every exchange with an offer for further help when appropriate.\n"
    "- Always maintain data accuracy — friendliness never means inventing data.\n\n"
    "CONVERSATION ENDING:\n"
    "- Recognize farewell intent when the user says phrases like:\n"
    "  \"thank you\", \"thanks\", \"dhanyabad\", \"bye\", \"goodbye\", \"see you\",\n"
    "  \"that's all\", \"that's all for now\", \"nothing more\", \"nothing else\",\n"
    "  \"nothing else for now\", \"no more questions\", \"all done\", \"i'm done\",\n"
    "  and similar closing phrases.\n"
    "- If the message is ONLY a closing (no new question or topic), respond\n"
    "  with a warm, final closing message and do NOT offer follow-up help.\n"
    "- The closing should include \"Dhanyabad\" as the sign-off word\n"
    "  and the disclaimer on its own line.\n"
    "- Examples:\n"
    "  User: \"That's all for now, thank you.\"\n"
    "  Assistant: \"Dhanyabad! Happy trading, and remember — the stock market "
    "involves risk. Invest wisely.\"\n\n"
    "  User: \"Nothing else.\"\n"
    "  Assistant: \"Dhanyabad! Wishing you successful investments. "
    "The stock market involves risk — this is not financial advice.\"\n\n"
    "GUIDELINES:\n"
    "1. Base ALL numerical claims on PROVIDED DATA. If a metric is not in the "
    "data, say 'not available' — never guess.\n"
    "2. You may explain what indicators suggest (e.g., 'RSI above 70 = overbought'), "
    "but note past patterns do not guarantee future results.\n"
    "3. Offer directional analysis based on data, framed as analysis not recommendation.\n"
    "4. ALWAYS include: 'The stock market involves risk. This is not financial advice.'\n"
    "5. Cite NEPSE as data source.\n"
    "6. If you don't know something, say so honestly.\n\n"
    "STRICT FORMAT RULES:\n"
    "- Start data-backed responses with a one-line market snapshot (NEPSE + Sensitive index).\n"
    "- For stock data: use a single compact line per stock.\n"
    "  Example: **NABIL** | NPR 485.20 | +2.15% | Vol: 52,341 | RSI: 32.5\n"
    "- For technical indicators: one bullet per indicator with brief interpretation "
    "(e.g. '- RSI 32.5: oversold territory').\n"
    "- For market overview: use **bold section headers** and short bullet lists.\n"
    "- MAXIMUM 12 lines. No paragraph longer than 2 sentences.\n"
    "- End with the disclaimer on its own line."
)


@app.get("/api/guide/search")
async def guide_search(q: str = ""):
    if not q:
        return {"entries": get_popular_entries()}
    entry = find_guide_entry(q)
    if entry:
        return {"entry": entry}
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": GUIDE_SYSTEM_PROMPT},
                        {"role": "user", "content": q},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.5, "num_predict": 512},
                },
            )
            data = resp.json()
            llm_answer = data.get("message", {}).get("content", "")
    except Exception as e:
        logger.error("Guide search Ollama failed: %s", e)
        llm_answer = ""

    return {"entry": None, "llm_answer": llm_answer or None, "popular": get_popular_entries()}


@app.get("/api/guide/brokers")
async def guide_brokers(search: str = ""):
    await _ensure_broker_cache()
    return {"brokers": search_brokers(search)}


class QuestionRequest(BaseModel):
    question: str
    history: list[dict] = []


def detect_intent(query: str, symbols: list[str]) -> str:
    q = query.lower()
    if len(symbols) >= 2:
        return "compare"
    if len(symbols) == 1 and any(w in q for w in ["rsi", "macd", "sma", "moving average", "bollinger", "atr", "adx", "indicator", "signal", "technical"]):
        return "indicator"
    if len(symbols) == 1 and any(w in q for w in ["price", "ltp", "current", "how much", "rate", "value", "chart"]):
        return "price"
    if any(w in q for w in ["market", "overview", "gainers", "losers", "indices", "summary", "top"]):
        return "overview"
    return "guide"


async def build_data_context(symbols: list[str]) -> str:
    if not symbols:
        return ""

    live = await _fetch_live_all()
    live_map = {c.get("symbol", "").upper(): c for c in live}
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    lines = [f"=== REAL MARKET DATA (retrieved {now_str} NST) ==="]

    try:
        indices_data = await fetch_indices()
        if indices_data:
            lines.append("\nMarket Snapshot:")
            for idx in indices_data:
                name = idx.get("index", "")
                val = idx.get("currentValue")
                chg = idx.get("change", idx.get("perChange"))
                lines.append(f"  {name}: {val}" + (f" ({chg:+.2f}%)" if chg else ""))
    except Exception:
        pass

    records_by_symbol = {}
    try:
        async with async_session() as session:
            rows = await session.execute(
                select(DailyPrice)
                .where(DailyPrice.symbol.in_([s.upper() for s in symbols[:5]]))
                .order_by(DailyPrice.symbol, DailyPrice.date.desc())
            )
            for r in rows.scalars().all():
                records_by_symbol.setdefault(r.symbol, []).append(r.to_dict())
    except Exception:
        pass

    for sym in symbols[:5]:
        sym_u = sym.upper()
        l = live_map.get(sym_u, {})

        lines.append(f"\nStock: {sym_u}")
        ltp = l.get("ltp")
        lines.append(f"  LTP: NPR {ltp}" if ltp else "  LTP: not available")

        pct = l.get("percent_change")
        if pct is not None:
            sign = "+" if pct >= 0 else ""
            lines.append(f"  Change: {sign}{pct:.2f}%")
        prev_close = l.get("previous_close")
        if prev_close is not None:
            lines.append(f"  Prev Close: NPR {prev_close}")
        high = l.get("high")
        low = l.get("low")
        if high and low:
            lines.append(f"  Day Range: NPR {low} - NPR {high}")
        vol = l.get("volume")
        if vol:
            lines.append(f"  Volume: {int(vol):,}")
        turnover = l.get("turnover")
        if turnover:
            lines.append(f"  Turnover: NPR {turnover:,.0f}")
        trades = l.get("trades")
        if trades:
            lines.append(f"  Trades: {int(trades):,}")
        mcap = l.get("market_cap")
        if mcap:
            lines.append(f"  Market Cap: NPR {mcap:,.2f}M")

        detail = None
        try:
            cb = merolagani_fetcher.circuit_breaker_status('merolagani')
            if cb != 'open':
                detail = await merolagani_fetcher.get_company_detail(sym_u)
        except Exception:
            pass
        if not detail:
            try:
                ss_detail = await sharesansar_fetcher.get_company_detail(sym_u)
                if ss_detail:
                    ph = ss_detail.get('price_header') or {}
                    info = ss_detail.get('company_info') or {}
                    if info.get('sector'):
                        detail = {'sector': info['sector']}
                    else:
                        detail = {}
                    if ph.get('high_52w') and ph.get('low_52w'):
                        detail['52w_high'] = str(ph['high_52w'])
                        detail['52w_low'] = str(ph['low_52w'])
                    if ph.get('avg_120d'):
                        detail['120d_avg'] = str(ph['avg_120d'])
                    if ph.get('avg_180d'):
                        detail['180d_avg'] = str(ph['avg_180d'])
            except Exception:
                pass
        if detail:
            if detail.get("sector"):
                lines.append(f"  Sector: {detail['sector']}")
            if detail.get("52w_high") and detail.get("52w_low"):
                lines.append(f"  52W Range: NPR {detail['52w_low']} - NPR {detail['52w_high']}")
            if detail.get("120d_avg"):
                lines.append(f"  120D Avg: NPR {detail['120d_avg']}")
            if detail.get("180d_avg"):
                lines.append(f"  180D Avg: NPR {detail['180d_avg']}")
            if detail.get("1y_yield"):
                lines.append(f"  1Y Yield: {detail['1y_yield']}")

        try:
            records = records_by_symbol.get(sym_u, [])
            if len(records) >= 20:
                df = pd.DataFrame(records)
                indicators = compute_indicators(df)
                sig_type, confidence, reason = compute_signal(indicators)

                rsi = indicators.get("rsi")
                if rsi is not None:
                    lines.append(f"  RSI: {rsi:.1f}")

                macd = indicators.get("macd")
                macd_sig = indicators.get("macd_signal")
                if macd is not None and macd_sig is not None:
                    status = "Bullish" if macd > macd_sig else "Bearish"
                    lines.append(f"  MACD: {status} (MACD: {macd:.2f}, Signal: {macd_sig:.2f})")

                sma20 = indicators.get("sma20")
                if sma20 is not None:
                    lines.append(f"  SMA20: {sma20:.2f}")
                sma50 = indicators.get("sma50")
                if sma50 is not None:
                    lines.append(f"  SMA50: {sma50:.2f}")

                adx = indicators.get("adx")
                if adx is not None:
                    trend = "Strong" if adx >= 25 else "Weak"
                    lines.append(f"  ADX: {adx:.1f} ({trend} trend)")

                lines.append(f"  Signal: {sig_type} (confidence: {confidence}%)")
        except Exception:
            lines.append("  Technical indicators: not available")

    return "\n".join(lines)


async def _stream_llm(system_prompt: str, question: str, max_tokens: int, timeout_secs: int, history: list[dict] | None = None):
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": question})

    try:
        async with httpx.AsyncClient(timeout=timeout_secs) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.5, "num_predict": max_tokens},
                },
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logger.error("Ollama stream failed: %s", e)
        yield ""  # Signal failure — caller will use fallback


async def _generate_answer(req: QuestionRequest):
    question = req.question.strip()

    if not question:
        yield json.dumps({"type": "token", "token": "Please ask a question about NEPSE stocks or trading."}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"
        return

    NON_NEPSE_TOPICS = [
        "recipe", "cook", "bake", "movie", "song", "music", "album",
        "weather", "climate", "sports", "football", "cricket", "goal",
        "game", "play", "video game", "political", "election", "party",
        "travel", "hotel", "restaurant", "fashion", "celebrity",
    ]
    ql = question.lower()
    if any(t in ql for t in NON_NEPSE_TOPICS):
        yield json.dumps({"type": "token", "token": "I can only answer questions about NEPSE trading and the Nepali stock market."}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"
        return

    yield json.dumps({"type": "status", "status": "analyzing"}) + "\n"

    chart_match = re.search(r'(?:show\s+)?(?:me\s+)?(?:graph|chart)\s+(?:of\s+)?([A-Za-z]{2,10})\b', question, re.IGNORECASE)
    if chart_match:
        candidate = chart_match.group(1).strip().upper()
        found = fuzzy_search(candidate)
        if found:
            symbols = [found[0]["symbol"]]
            intent = "price"
        else:
            symbols = extract_symbols(question)
            intent = detect_intent(question, symbols)
    else:
        symbols = extract_symbols(question)
        intent = detect_intent(question, symbols)

    parsed = parse_query(question)
    suggestions = parsed.get("suggestions", [])
    match_type = suggestions[0].get("match_type") if suggestions else None
    symbol = symbols[0] if symbols else (parsed.get("symbol") or None)
    start_date = parsed.get("start")
    end_date = parsed.get("end")

    suggested_page = None
    data_context = ""

    if symbols:
        ctx_key = "ctx_" + "_".join(sorted(symbols))
        cached = await data_cache_get(ctx_key)
        if cached:
            data_context = cached
        else:
            yield json.dumps({"type": "status", "status": "searching"}) + "\n"
            data_context = await build_data_context(symbols)
            if data_context:
                await data_cache_set(ctx_key, data_context)
    elif intent == "overview":
        yield json.dumps({"type": "status", "status": "searching"}) + "\n"
        try:
            tops, indices, summary = await asyncio.gather(
                fetch_top_stocks(), fetch_indices(), fetch_market_summary(), return_exceptions=True
            )
            lines = [f"=== MARKET OVERVIEW (retrieved {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC) ==="]
            if not isinstance(indices, Exception) and indices:
                lines.append("\nIndices:")
                for idx in indices:
                    name = idx.get("index", "")
                    val = idx.get("currentValue")
                    chg = idx.get("change")
                    pct = idx.get("perChange")
                    high52 = idx.get("fiftyTwoWeekHigh")
                    low52 = idx.get("fiftyTwoWeekLow")
                    parts = [f"  {name}: {val}"]
                    if chg is not None:
                        parts.append(f"Chg: {chg:+.2f}")
                    if pct is not None:
                        parts.append(f"({pct:+.2f}%)")
                    if high52 and low52:
                        parts.append(f"52W: {low52} - {high52}")
                    lines.append(" | ".join(parts))
            if not isinstance(summary, Exception) and summary:
                lines.append("\nMarket Summary:")
                for item in summary[:6]:
                    if isinstance(item, dict):
                        detail = item.get("detail", "")
                        value = item.get("value", "")
                        if detail and value:
                            short = detail.replace("Total ", "").replace(" (Rs.)", "")
                            lines.append(f"  {short}: {value}")
            if not isinstance(tops, Exception) and tops:
                gainers = tops.get("top_gainer", [])
                if gainers:
                    lines.append(f"\nTop 5 Gainers:")
                    for g in gainers[:5]:
                        lines.append(f"  - {g.get('symbol')}: {g.get('percentageChange')}+%")
                losers = tops.get("top_loser", [])
                if losers:
                    lines.append(f"\nTop 5 Losers:")
                    for g in losers[:5]:
                        lines.append(f"  - {g.get('symbol')}: {g.get('percentageChange')}%")
            data_context = "\n".join(lines)
        except Exception:
            pass

    if intent == "guide" or not data_context:
        system_prompt = GUIDE_SYSTEM_PROMPT
    else:
        system_prompt = GUIDE_SYSTEM_PROMPT + (
            "\n\nADDITIONAL RULES (data analyst mode):\n"
            "1. Prioritize the provided REAL market data below for all metrics.\n"
            "2. If a metric is not in the provided data, say it is not available — do NOT use general knowledge.\n"
            "3. Cite NEPSE as the data source.\n"
            "4. Organize data into distinct sections with **bold headers** (e.g. **Index**, **Gainers**, **NABIL**).\n"
            "5. Use compact bullet-point format: one fact per line, no run-on paragraphs.\n"
            "6. Keep the total response under 12 lines."
        )

    if data_context:
        system_prompt += (
            "\n\nPROVIDED DATA:\n" + data_context +
            "\n\nUse this data for metrics when available."
        )

    yield json.dumps({"type": "meta", "suggested_page": suggested_page, "symbol": symbol,
                       "symbol_match_type": match_type, "start_date": start_date.isoformat() if start_date else None,
                       "end_date": end_date.isoformat() if end_date else None}) + "\n"

    yield json.dumps({"type": "status", "status": "thinking"}) + "\n"
    max_tokens = 1024
    timeout_secs = 180 if intent == "compare" else 120
    answer_parts: list[str] = []
    token_count = 0

    try:
        async for token in _stream_llm(system_prompt, question, max_tokens, timeout_secs, req.history):
            if token:
                answer_parts.append(token)
                token_count += 1
                yield json.dumps({"type": "token", "token": token}) + "\n"
    except Exception as e:
        logger.error("_generate_answer streaming failed: %s", e)

    answer = "".join(answer_parts)
    if not answer or token_count == 0:
        answer = (
            "The AI assistant is currently unavailable. Try asking:\n"
            "- 'Compare NABIL and SCB'\n"
            "- 'What is RSI of NABIL?'\n"
            "- 'Top gainers today'\n"
            "- 'How do I start trading?'"
        )
        yield json.dumps({"type": "token", "token": answer}) + "\n"

    yield json.dumps({"type": "done"}) + "\n"


@app.post("/api/ask")
async def ask_question(req: QuestionRequest):
    return StreamingResponse(_generate_answer(req), media_type="text/event-stream")


@app.get("/api/health")
async def health():
    db_ok = False
    try:
        async with async_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.warning("Health check DB failed: %s", e)

    from data.fetcher import circuit_breaker as fetcher_cb

    sources = {
        'yonepse': fetcher_cb.status('yonepse/live'),
        'merolagani': merolagani_fetcher.circuit_breaker_status('merolagani'),
        'sharesansar': sharesansar_fetcher.circuit_breaker_status('sharesansar'),
        'nepalipaisa': fetcher_cb.status('nepalipaisa/ipo'),
    }

    scheduler_ts = scheduler.get_last_good_timestamps()

    ollama_ok = False
    ollama_error = None
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                base = OLLAMA_MODEL.split(":")[0]
                ollama_ok = any(m.get("name", "").startswith(base) for m in r.json().get("models", []))
            else:
                ollama_error = f"status {r.status_code}"
    except Exception as e:
        ollama_error = str(e)
    if ollama_error:
        logger.warning("Ollama health check: %s", ollama_error)

    return {
        "status": "ok" if db_ok else "degraded",
        "time": datetime.now(timezone.utc).isoformat(),
        "database": "connected" if db_ok else "error",
        "sources": sources,
        "scheduler": scheduler_ts,
        "ollama": {"running": ollama_ok, "model": OLLAMA_MODEL},
    }
