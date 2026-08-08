"""Live market data services: index history seeding, background polling, live fetch.

All services mutate the shared singleton :data:`app.services.state.LIVE_CACHE`
under :data:`app.services.state.live_cache_lock`.
"""

import asyncio
import logging
import time as time_module
from datetime import date, datetime, timezone

from bs4 import BeautifulSoup
from sqlalchemy import select

from app.db.models import DailyPrice
from app.db.session import async_session
from app.providers.cache import get_market_cache, persist_live_cache, set_market_cache
from app.providers.yonep import fetch_all_securities
from app.services.scheduler import NPT, get_market_status
from app.services.state import LIVE_CACHE, live_cache_lock, merolagani_fetcher, sharesansar_fetcher

logger = logging.getLogger('services.live')

_poll_task: asyncio.Task | None = None


def _to_timestamp(dt: date | datetime) -> int:
    """Convert a date or datetime to a Unix timestamp in UTC."""
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


async def seed_daily_history(cache: dict):
    """Seed the index history cache from the database or Merolagani scrape.

    Attempts to load the last 35 daily NEPSE index points from the database.
    Falls back to scraping Merolagani's Indices.aspx if the database is empty.
    Also populates the Sensitive Index data and initial 30-second snapshots.

    Args:
        cache: The LIVE_CACHE dict to populate with index_history and index_30s.
    """
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
    except Exception as e:
        logger.warning("Daily price history query failed: %s", e)
        records = []

    if not records:
        try:
            html = await merolagani_fetcher.get_index_history_page()
            if html:
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
                            if len(cache.get('index_30s', [])) < 2:
                                cache['index_30s'] = [{'time': p['time'], 'values': {'NEPSE': p['value']}} for p in parsed[-35:]]
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
        try:
            async with async_session() as session:
                sens_result = await session.execute(
                    select(DailyPrice)
                    .where(DailyPrice.symbol == 'Sensitive Index')
                    .order_by(DailyPrice.date.desc())
                    .limit(35)
                )
                sens_records = [r.to_dict() for r in sens_result.scalars().all()]
        except Exception:
            sens_records = []
        sens_map = {}
        for r in sens_records:
            dt = r.get('date', '')
            if isinstance(dt, str):
                dt = date.fromisoformat(dt)
            close = r.get('close') or r.get('ltp', 0)
            if close:
                ts = int(_to_timestamp(dt))
                sens_map[ts] = float(close)
        async with live_cache_lock:
            cache['index_history'] = history[-35:]
            if len(cache.get('index_30s', [])) < 2:
                seeded = []
                for p in history[-35:]:
                    entry = {'time': p['time'], 'values': {'NEPSE': p['value']}}
                    sv = sens_map.get(p['time'])
                    if sv is not None:
                        entry['values']['Sensitive Index'] = sv
                    seeded.append(entry)
                cache['index_30s'] = seeded
        logger.info("Seeded index_history with %d daily points from DB", len(history))


INDEX_PRIORITY = ['NEPSE', 'Sensitive Index', 'Float Index']


def _sort_indices(indices: list[dict]) -> list[dict]:
    """Sort a list of index dicts so that major indices (NEPSE, Sensitive, Float) appear first."""

    def sort_key(item):
        """Return a sort key — priority 0 for major indices, 1 for others."""
        name = item.get('name', '')
        try:
            return (0, INDEX_PRIORITY.index(name))
        except ValueError:
            return (1, name.lower())
    return sorted(indices, key=sort_key)


def _normalize_index_name(name: str) -> str:
    """Normalize an index name to a canonical form (e.g. 'NEPSE', 'Sensitive Index')."""
    n = name.strip()
    if n.upper() == 'NEPSE' or n.upper() == 'NEPSE INDEX':
        return 'NEPSE'
    if 'index' in n.lower():
        return n
    return f"{n} Index"


def _log_poll_failure(task: asyncio.Task) -> None:
    """Log unexpected failures of the background index poll task."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.warning('Index poll task failed: %s', exc)


async def start_index_polling(cache: dict):
    """Start a background task that polls index data at regular intervals.

    During market hours polls every 10 seconds; during closed hours polls every 5 minutes.
    Data is sourced from Merolagani SignalR (priority 1) or Sharesansar (priority 2).
    Stores results in the provided cache dict under index_30s, index_hourly,
    current_indices, last_updated, and current_index keys.

    Args:
        cache: The LIVE_CACHE dict to update with polled index data.

    Returns:
        The background task (so callers can cancel it on shutdown).
    """
    global _poll_task
    if _poll_task is not None and not _poll_task.done():
        return _poll_task

    async def _poll():
        """Background loop: poll indices, update cache, sleep."""
        is_open = False
        while True:
            try:
                status = get_market_status()
                is_open = status.get('is_open', False)
            except Exception as e:
                logger.warning("Market status check failed: %s", e)
                is_open = False

            try:
                all_indices = None

                # Priority 1: Merolagani SignalR (real-time)
                if is_open:
                    try:
                        raw = await merolagani_fetcher.get_live_index()
                        if raw:
                            all_indices = {}
                            for name, entry in raw.items():
                                key = _normalize_index_name(name)
                                all_indices[key] = entry
                                all_indices[key]['name'] = key
                    except Exception as e:
                        logger.warning("Merolagani SignalR index poll failed: %s", e)

                # Priority 2: Sharesansar live trading (HTML scrape, fresher than yonepse)
                if not all_indices:
                    try:
                        ss_data = await sharesansar_fetcher.get_live_trading()
                        ss_indices = ss_data.get('indices', []) if ss_data else []
                        if ss_indices:
                            all_indices = {}
                            for idx in ss_indices:
                                name = idx.get('name', '')
                                key = _normalize_index_name(name)
                                val = idx.get('value')
                                pct = idx.get('percent_change', 0) or 0
                                change = round(val * pct / 100, 2) if val else 0
                                all_indices[key] = {
                                    'name': key,
                                    'currentValue': val,
                                    'change': change,
                                    'perChange': pct,
                                }
                    except Exception as e:
                        logger.warning("Sharesansar index poll failed: %s", e)

                if all_indices:
                    async with live_cache_lock:
                        base = dict(LIVE_CACHE.get('current_indices', {}))
                    base.update(all_indices)
                    all_indices = base

                    now_npt = datetime.now(NPT)
                    now_utc = datetime.now(timezone.utc)

                    vals: dict[str, float | None] = {}
                    for name, entry in all_indices.items():
                        vals[name] = entry.get('currentValue')

                    async with live_cache_lock:
                        tail = cache.setdefault('index_30s', [])
                        prev = tail[-1] if tail else None
                        if is_open or not prev:
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
                        cache['last_updated'] = _to_timestamp(now_utc)
                        n = all_indices.get('NEPSE', {})
                        cache['current_index'] = {
                            'name': 'NEPSE Index',
                            'currentValue': n.get('currentValue'),
                            'change': n.get('change'),
                            'perChange': n.get('perChange'),
                        } if n.get('currentValue') is not None else None
                    await persist_live_cache(cache)
            except Exception as e:
                logger.warning('Index poll failed: %s', e)

            await asyncio.sleep(10 if is_open else 300)

    _poll_task = asyncio.create_task(_poll())
    _poll_task.add_done_callback(_log_poll_failure)
    return _poll_task

def _cache_ts_to_epoch(ts) -> float | None:
    """Convert a cache timestamp (ISO string or epoch float) to epoch seconds."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    try:
        parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError:
        return None


async def _fetch_live_all() -> list[dict]:
    """Fetch all securities data, falling back to cached data on failure.

    Short-circuits when the market cache is fresher than 30 seconds so that
    bursty requests (API calls, charts, search) never hammer upstream.
    """
    cached_data, cached_ts = await get_market_cache()
    ts_epoch = _cache_ts_to_epoch(cached_ts)
    if ts_epoch is not None and (time_module.time() - ts_epoch) < 30:
        return cached_data
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