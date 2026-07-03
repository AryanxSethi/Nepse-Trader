import asyncio
import json
import logging
import os
import time as time_module
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from cachetools import TTLCache

logger = logging.getLogger('cache')

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache"

MARKET_CACHE_TTL = 30
IPO_CACHE_TTL = 60
DATA_CACHE_TTL = 30
DATA_CACHE_MAXSIZE = 100

_market_cache: TTLCache = TTLCache(maxsize=1, ttl=MARKET_CACHE_TTL)
_ipo_cache: TTLCache = TTLCache(maxsize=1, ttl=IPO_CACHE_TTL)
_data_cache: TTLCache = TTLCache(maxsize=DATA_CACHE_MAXSIZE, ttl=DATA_CACHE_TTL)

_disk_lock = Lock()


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(name: str) -> Path:
    return CACHE_DIR / f"{name}.json"


def _persist(name: str, data):
    _ensure_cache_dir()
    path = _cache_path(name)
    try:
        with _disk_lock:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, default=str)
    except Exception as e:
        logger.debug('cache persist %s failed: %s', name, e)


def _load_from_disk(name: str):
    path = _cache_path(name)
    if not path.exists():
        return None
    try:
        with _disk_lock:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.debug('cache load %s failed: %s', name, e)
        return None


def get_market_cache():
    data = _market_cache.get('data')
    ts = _market_cache.get('timestamp')
    if data is None:
        disk = _load_from_disk('market')
        if disk:
            _market_cache['data'] = disk.get('data', [])
            _market_cache['timestamp'] = disk.get('timestamp')
            return disk.get('data', []), disk.get('timestamp')
    return data or [], ts


def set_market_cache(data, timestamp: str | None = None):
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    _market_cache['data'] = data
    _market_cache['timestamp'] = ts
    _persist('market', {'data': data, 'timestamp': ts})


def get_ipo_cache():
    data = _ipo_cache.get('data')
    ts = _ipo_cache.get('timestamp')
    return data, ts


def set_ipo_cache(data, timestamp: str | None = None):
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    _ipo_cache['data'] = data
    _ipo_cache['timestamp'] = ts
    _persist('ipo', {'data': data, 'timestamp': ts})


def data_cache_get(key: str) -> str | None:
    val = _data_cache.get(key)
    if val is not None:
        val_str, ts = val
        if time_module.time() - ts < DATA_CACHE_TTL:
            return val_str
    return None


def data_cache_set(key: str, val: str) -> None:
    _data_cache[key] = (val, time_module.time())


LIVE_CACHE_KEYS = ['current_indices', 'current_index', 'index_30s', 'index_hourly', 'index_history']


def persist_live_cache(live_cache: dict):
    data = {k: live_cache.get(k) for k in LIVE_CACHE_KEYS if k in live_cache}
    _persist('live_cache', data)


def load_live_cache() -> dict:
    disk = _load_from_disk('live_cache')
    return disk if isinstance(disk, dict) else {}


async def prewarm_caches():
    _ensure_cache_dir()
    for name in ('market', 'ipo'):
        disk = _load_from_disk(name)
        if disk:
            cache = _market_cache if name == 'market' else _ipo_cache
            cache['data'] = disk.get('data', [])
            cache['timestamp'] = disk.get('timestamp')
            logger.info('Prewarmed %s cache from disk (%d items)', name, len(cache.get('data', [])) if isinstance(cache.get('data'), list) else 1)


async def persist_caches_on_exit():
    _persist('market', {'data': _market_cache.get('data', []), 'timestamp': _market_cache.get('timestamp')})
    _persist('ipo', {'data': _ipo_cache.get('data', []), 'timestamp': _ipo_cache.get('timestamp')})
