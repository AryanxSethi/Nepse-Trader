"""FastAPI application shell for NEPSE Trader.

Owns app lifecycle (DB init, seeding, cache warmup, background tasks) and
app-level routes. Feature routes live in ``app.api.routers``; data services
live in ``app.services``.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.cache_control import add_cache_headers
from app.core.config import CORS_ORIGINS, OLLAMA_MODEL, OLLAMA_URL
from app.core.rate_limit import rate_limit_middleware
from app.db.models import Security
from app.db.session import async_session, engine, init_db
from app.db.seeder import seed_securities
from app.guide.broker_directory import _ensure_brokers as _ensure_broker_cache
from app.providers.cache import (
    load_live_cache,
    persist_caches_on_exit,
    persist_live_cache,
    prewarm_caches,
)
from app.providers.yonep import circuit_breaker as fetcher_cb
from app.providers.yonep import fetch_all_securities, fetch_indices
from app.search.fuzzy import load_securities_cache, set_security_cache
from app.services.live import _fetch_live_all, _normalize_index_name, seed_daily_history, start_index_polling
from app.services.scheduler import get_market_status
from app.services.state import LIVE_CACHE, live_cache_lock, merolagani_fetcher, scheduler, sharesansar_fetcher
from app.services.updater import run_daily_update

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('main')

from app.api.routers import backtest, brokers, chat, guide, ipos, market, portfolio, search, sectors, signals, stocks


async def _securities_from_db() -> list[dict]:
    """Fallback: pull symbol/name pairs from the local DB when upstream is down."""
    try:
        async with async_session() as session:
            result = await session.execute(select(Security).order_by(Security.symbol))
            return [{"symbol": s.symbol, "name": s.name} for s in result.scalars().all()]
    except Exception as e:
        logger.warning("DB securities fallback failed: %s", e)
        return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — initialises DB, seeds data, prewarms caches, starts background tasks."""
    poll_task = None
    try:
        await init_db()
    except Exception as e:
        logger.error("Database init failed: %s — continuing with degraded service", e)
    try:
        await seed_securities()
    except Exception as e:
        logger.warning("Seeding failed: %s", e)
    try:
        securities_data = await fetch_all_securities()
        symbols = []
        seen = set()
        for item in securities_data:
            if not isinstance(item, dict):
                continue
            sym = str(item.get("symbol", "")).strip().upper()
            name = str(item.get("name", "")).strip()
            if sym and sym not in seen:
                seen.add(sym)
                symbols.append({"symbol": sym, "name": name})
        await set_security_cache(symbols)
        if not symbols:
            raise ValueError("upstream returned no securities")
    except Exception as e:
        logger.warning("Failed to load securities cache from upstream: %s", e)
        symbols = load_securities_cache()
        if not symbols:
            symbols = await _securities_from_db()
        await set_security_cache(symbols)
        if symbols:
            logger.info("Loaded %d securities from fallback", len(symbols))
    try:
        count = await run_daily_update()
        if count > 0:
            logger.info("Inserted %d new daily price records", count)
    except Exception as e:
        logger.warning("Daily update failed: %s", e)
    try:
        from app.analysis.signals import generate_signals
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
    try:
        yonepse_indices = await fetch_indices()
        if yonepse_indices:
            async with live_cache_lock:
                current = LIVE_CACHE.get('current_indices', {}) or {}
                for idx in yonepse_indices:
                    raw_name = idx.get('index', '')
                    name = _normalize_index_name(raw_name)
                    if name and name not in current:
                        current[name] = {
                            'name': name,
                            'currentValue': idx.get('currentValue'),
                            'change': idx.get('change'),
                            'perChange': idx.get('perChange'),
                        }
                LIVE_CACHE['current_indices'] = current
                n = current.get('NEPSE', {}) or {}
                LIVE_CACHE['current_index'] = {
                    'name': 'NEPSE Index',
                    'currentValue': n.get('currentValue'),
                    'change': n.get('change'),
                    'perChange': n.get('perChange'),
                } if n.get('currentValue') is not None else None
            await persist_live_cache(LIVE_CACHE)
            logger.info("Merged yonepse indices into current_indices (%d total)", len(current))
    except Exception as e:
        logger.warning("Index warmup from yonepse failed: %s", e)
    scheduler.start()
    await seed_daily_history(LIVE_CACHE)
    try:
        poll_task = await start_index_polling(LIVE_CACHE)
    except Exception as e:
        logger.warning("Index polling failed to start: %s", e)
    yield
    if poll_task is not None:
        poll_task.cancel()
        try:
            await asyncio.wait_for(poll_task, timeout=3)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    try:
        async with live_cache_lock:
            await persist_live_cache(LIVE_CACHE)
        await persist_caches_on_exit()
    except Exception as e:
        logger.warning("Failed to persist caches on exit: %s", e)
    await merolagani_fetcher.stop()
    await sharesansar_fetcher.stop()
    await scheduler.stop()
    await engine.dispose()


app = FastAPI(title="NEPSE Trader", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(add_cache_headers)
app.middleware("http")(rate_limit_middleware)


@app.exception_handler(SQLAlchemyError)
async def _db_error_handler(request: Request, exc: SQLAlchemyError):
    """Map unexpected database errors to 503 instead of a raw 500 stack trace."""
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=503, content={"detail": "Database temporarily unavailable"})

for r in (search, market, stocks, signals, backtest, portfolio, ipos, brokers, sectors, guide, chat):
    app.include_router(r.router)


@app.get("/api/companies")
async def get_companies() -> list[dict]:
    """GET /api/companies — return all listed companies with LTP, change, volume, turnover, trades."""
    data = await _fetch_live_all()
    return [
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
    ]


@app.get("/api/securities")
async def get_securities(search: str = "") -> list[dict]:
    """GET /api/securities — search securities by symbol or name; return all if no search query."""
    async with async_session() as session:
        if search:
            pattern = f"%{search}%"
            result = await session.execute(
                select(Security).where(Security.symbol.ilike(pattern) | Security.name.ilike(pattern))
            )
        else:
            result = await session.execute(select(Security).order_by(Security.symbol))
        return [{"symbol": s.symbol, "name": s.name} for s in result.scalars().all()]


@app.get("/api/health")
async def health() -> dict:
    """GET /api/health — return system health: database, data sources, scheduler, and Ollama status."""
    db_ok = False
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.warning("Health check DB failed: %s", e)

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
        import httpx
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