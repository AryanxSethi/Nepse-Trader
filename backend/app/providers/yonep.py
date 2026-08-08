"""JSON fetchers for the yonepse static data source (GitHub Pages).

All functions share a single circuit breaker and retry logic via :mod:`data._http`.
"""

import logging

from app.core.config import YONEPSE_BASE
from app.providers.http import (
    CircuitBreaker,
    FetchResult,
    retry_get_json,
)

logger = logging.getLogger('fetcher')

circuit_breaker = CircuitBreaker(threshold=3, cooloff=60.0)


async def _fetch_json(path: str, source: str) -> FetchResult:
    """Fetch a JSON file from the yonepse GitHub Pages source with circuit-breaker protection."""
    url = f"{YONEPSE_BASE}{path}"
    if circuit_breaker.is_open(source):
        logger.warning('[%s] circuit open, skipping', source)
        return FetchResult(ok=False, source=source, error='circuit open')
    result = await retry_get_json(url, source=source)
    if result.ok:
        circuit_breaker.record_success(source)
    else:
        circuit_breaker.record_failure(source)
    return result


async def fetch_all_securities() -> list[dict]:
    """Return the full list of securities (symbol, name, sector) from yonepse."""
    result = await _fetch_json("/data/nepse_data.json", "yonepse/securities")
    if result.ok and isinstance(result.data, list):
        return result.data
    logger.warning('fetch_all_securities: %s', result.error or 'non-list response')
    return []


async def fetch_live_prices() -> list[dict]:
    """Return live stock prices from yonepse (delayed snapshot)."""
    result = await _fetch_json("/data/market/live.json", "yonepse/live")
    if result.ok and isinstance(result.data, list):
        return result.data
    logger.warning('fetch_live_prices: %s', result.error or 'non-list response')
    return []


async def fetch_market_summary() -> list | dict:
    """Return the market summary (turnover, trades, scrips, market cap) from yonepse."""
    result = await _fetch_json("/data/market/summary.json", "yonepse/summary")
    if result.ok and isinstance(result.data, (dict, list)):
        return result.data
    logger.warning('fetch_market_summary: %s', result.error or 'unexpected response')
    return []


async def fetch_top_stocks() -> dict:
    """Return top gainers / losers / turnover stocks from yonepse."""
    result = await _fetch_json("/data/market/top_stocks.json", "yonepse/top")
    if result.ok and isinstance(result.data, dict):
        return result.data
    logger.warning('fetch_top_stocks: %s', result.error or 'non-dict response')
    return {}


async def fetch_indices() -> list[dict]:
    """Return the index list (NEPSE, Sensitive, Float, etc.) from yonepse (static snapshot)."""
    result = await _fetch_json("/data/market/indices.json", "yonepse/indices")
    if result.ok and isinstance(result.data, list):
        return result.data
    logger.warning('fetch_indices: %s', result.error or 'non-list response')
    return []


async def fetch_market_status() -> dict:
    """Return market open/close status from yonepse."""
    result = await _fetch_json("/data/market/status.json", "yonepse/status")
    if result.ok and isinstance(result.data, dict):
        return result.data
    logger.warning('fetch_market_status: %s', result.error or 'non-dict response')
    return {"is_open": False, "last_checked": None}


async def fetch_ltp_history(date_str: str) -> dict | None:
    """Return per-symbol LTP history for a given *date_str* (YYYY-MM-DD) from yonepse."""
    result = await _fetch_json(f"/data/ltp/daily/{date_str}.json", "yonepse/ltp")
    if result.ok and isinstance(result.data, dict):
        return result.data
    logger.debug('fetch_ltp_history(%s): %s', date_str, result.error or 'no data')
    return None
