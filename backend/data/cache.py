import asyncio
import json
import logging
import time as time_module
from datetime import datetime, timezone
from pathlib import Path

from cachetools import TTLCache

logger = logging.getLogger('cache')

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache"

MARKET_CACHE_TTL = 30
IPO_CACHE_TTL = 60
DATA_CACHE_TTL = 30
DATA_CACHE_MAXSIZE = 100

_market_cache: TTLCache = TTLCache(maxsize=2, ttl=MARKET_CACHE_TTL)
_ipo_cache: TTLCache = TTLCache(maxsize=2, ttl=IPO_CACHE_TTL)
_data_cache: TTLCache = TTLCache(maxsize=DATA_CACHE_MAXSIZE, ttl=DATA_CACHE_TTL)

_market_cache_lock = asyncio.Lock()
_ipo_cache_lock = asyncio.Lock()
_data_cache_lock = asyncio.Lock()
_disk_lock = asyncio.Lock()


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(name: str) -> Path:
    return CACHE_DIR / f"{name}.json"


async def _persist(name: str, data):
    _ensure_cache_dir()
    path = _cache_path(name)
    try:
        async with _disk_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _write_json, path, data)
    except Exception as e:
        logger.warning('cache persist %s failed: %s', name, e)


def _write_json(path: Path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, default=str)


def _read_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def _load_from_disk(name: str):
    path = _cache_path(name)
    if not path.exists():
        return None
    try:
        async with _disk_lock:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, _read_json, path)
    except Exception as e:
        logger.warning('cache load %s failed: %s', name, e)
        return None


async def get_market_cache():
    async with _market_cache_lock:
        data = _market_cache.get('data')
        ts = _market_cache.get('timestamp')
        if data is None:
            disk = await _load_from_disk('market')
            if disk:
                _market_cache['data'] = disk.get('data', [])
                _market_cache['timestamp'] = disk.get('timestamp')
                return disk.get('data', []), disk.get('timestamp')
        return data or [], ts


async def set_market_cache(data, timestamp: str | None = None):
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    async with _market_cache_lock:
        _market_cache['data'] = data
        _market_cache['timestamp'] = ts
    await _persist('market', {'data': data, 'timestamp': ts})


async def get_ipo_cache():
    async with _ipo_cache_lock:
        data = _ipo_cache.get('data')
        ts = _ipo_cache.get('timestamp')
    return data, ts


async def set_ipo_cache(data, timestamp: str | None = None):
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    async with _ipo_cache_lock:
        _ipo_cache['data'] = data
        _ipo_cache['timestamp'] = ts
    await _persist('ipo', {'data': data, 'timestamp': ts})


async def data_cache_get(key: str) -> str | None:
    async with _data_cache_lock:
        val = _data_cache.get(key)
        if val is not None:
            val_str, ts = val
            if time_module.time() - ts < DATA_CACHE_TTL:
                return val_str
    return None


async def data_cache_set(key: str, val: str) -> None:
    async with _data_cache_lock:
        _data_cache[key] = (val, time_module.time())


LIVE_CACHE_KEYS = ['current_indices', 'current_index', 'index_30s', 'index_hourly', 'index_history']


async def persist_live_cache(live_cache: dict):
    data = {k: live_cache.get(k) for k in LIVE_CACHE_KEYS if k in live_cache}
    await _persist('live_cache', data)


async def load_live_cache() -> dict:
    data = await _load_from_disk('live_cache')
    return data or {}


async def prewarm_caches():
    _ensure_cache_dir()
    for name in ('market', 'ipo'):
        disk = await _load_from_disk(name)
        if disk:
            if name == 'market':
                async with _market_cache_lock:
                    _market_cache['data'] = disk.get('data', [])
                    _market_cache['timestamp'] = disk.get('timestamp')
            else:
                async with _ipo_cache_lock:
                    _ipo_cache['data'] = disk.get('data', [])
                    _ipo_cache['timestamp'] = disk.get('timestamp')
            items = disk.get('data', [])
            logger.info('Prewarmed %s cache from disk (%d items)', name, len(items) if isinstance(items, list) else 1)


async def persist_caches_on_exit():
    async with _market_cache_lock:
        market_data = _market_cache.get('data', [])
        market_ts = _market_cache.get('timestamp')
    async with _ipo_cache_lock:
        ipo_data = _ipo_cache.get('data', [])
        ipo_ts = _ipo_cache.get('timestamp')
    await _persist('market', {'data': market_data, 'timestamp': market_ts})
    await _persist('ipo', {'data': ipo_data, 'timestamp': ipo_ts})
