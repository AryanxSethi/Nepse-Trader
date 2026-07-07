"""Broker directory — caches broker list and provides search/top queries."""

import time
import logging

from data.broker_fetcher import fetch_brokers, transform_broker

logger = logging.getLogger('broker_directory')

_broker_cache: list[dict] | None = None
_broker_cache_ts: float = 0
CACHE_TTL = 300


async def _ensure_brokers():
    """Refresh broker list from upstream if the cache is stale or empty."""
    global _broker_cache, _broker_cache_ts
    now = time.time()
    if _broker_cache is not None and now - _broker_cache_ts < CACHE_TTL:
        return
    raw = await fetch_brokers()
    if raw:
        _broker_cache = [transform_broker(b) for b in raw]
        _broker_cache_ts = now
        logger.info("Loaded %d brokers from yonepse", len(_broker_cache))
    elif _broker_cache is None:
        _broker_cache = []
        _broker_cache_ts = now
        logger.warning("No broker data available — empty list will be used")


def search_brokers(query: str, _force_brokers: list | None = None) -> list[dict]:
    """Search cached brokers by name, code, district or phone; return up to 30 matches."""

    brokers = _force_brokers if _force_brokers is not None else _broker_cache
    if brokers is None:
        return []
    q = query.strip().lower()
    if not q:
        return brokers[:20]
    results = []
    for b in brokers:
        if q in b['name'].lower() or b['code'].startswith(q):
            results.append(b)
        elif any(q in d.lower() for d in b.get('districts', [])):
            results.append(b)
        elif q in b.get('phone', '').replace('-', '').replace(' ', ''):
            results.append(b)
        if len(results) >= 30:
            break
    return results[:30]


def get_top_brokers(period: str = 'monthly', limit: int = 20) -> list[dict]:
    """Return top brokers by turnover for the given period (daily/weekly/monthly)."""
    brokers = _broker_cache or []
    if period == 'daily':
        key = 'latest_turnover'
    elif period == 'weekly':
        key = 'weekly_turnover'
        enriched = []
        for b in brokers:
            copy = dict(b)
            copy['weekly_turnover'] = (b.get('thirty_days_turnover', 0) or 0) / 4.3
            enriched.append(copy)
        sorted_brokers = sorted(enriched, key=lambda b: b.get(key, 0) or 0, reverse=True)
        return [{'rank': i+1, **b} for i, b in enumerate(sorted_brokers[:limit])]
    else:
        key = 'thirty_days_turnover'
    sorted_brokers = sorted(brokers, key=lambda b: b.get(key, 0) or 0, reverse=True)
    return [{'rank': i+1, **b} for i, b in enumerate(sorted_brokers[:limit])]
