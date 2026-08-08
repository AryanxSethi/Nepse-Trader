"""Application-wide mutable singletons: live market cache and data-source fetchers.

Routers and services import from here so the whole app shares one cache and
one set of fetcher/scheduler instances.
"""

import asyncio

from app.providers.merolagani import MerolaganiFetcher
from app.providers.sharesansar import SharesansarFetcher
from app.services.scheduler import MarketScheduler

LIVE_CACHE = {
    "data": [],
    "timestamp": None,
    "index_history": [],
    "current_index": None,
    "current_indices": {},
    "index_hourly": [],
    "index_30s": [],
    "last_updated": None,
}
live_cache_lock = asyncio.Lock()

scheduler = MarketScheduler()
merolagani_fetcher = MerolaganiFetcher()
sharesansar_fetcher = SharesansarFetcher()