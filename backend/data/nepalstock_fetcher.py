import asyncio
import logging
import httpx
from typing import Any

from data._http import CircuitBreaker, FetchResult, retry_get, retry_get_json
from data.assets.css_wasm_funcs import extract_salts, build_column_map

logger = logging.getLogger('nepalstock_fetcher')

NEPSE_BASE = 'https://www.nepalstock.com.np'
YONEPSE_BASE = 'https://shubhamnpk.github.io/yonepse'
CSS_URL = 'https://cdn.nepalstock.com.np/css/main.css'

TIMEOUT_SEC = 15
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

circuit_breaker = CircuitBreaker(threshold=3, cooloff=60.0)


class NepalStockFetcher:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._salt1 = 0
        self._salt2 = 0
        self._column_map: dict[str, str] = {}
        self._css_loaded = False
        self._semaphore = asyncio.Semaphore(1)

    async def _init_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={'User-Agent': USER_AGENT},
                timeout=TIMEOUT_SEC,
                follow_redirects=True,
            )

    async def _ensure_css(self) -> bool:
        if self._css_loaded:
            return True
        await self._init_client()
        try:
            resp = await self._client.get(CSS_URL)
            resp.raise_for_status()
            css_text = resp.text
            self._salt1, self._salt2 = extract_salts(css_text)
            self._css_loaded = True
            logger.info('CSS salts loaded: salt1=%s salt2=%s', self._salt1, self._salt2)
            return True
        except Exception as e:
            logger.warning('Failed to load CSS: %s', e)
            return False

    async def _nepse_get(self, path: str, params: dict | None = None) -> FetchResult:
        await self._init_client()
        url = f'{NEPSE_BASE}{path}'
        if circuit_breaker.is_open('nepalstock'):
            logger.warning('[nepalstock] circuit open, skipping')
            return FetchResult(ok=False, source='nepalstock', error='circuit open')
        result = await retry_get(
            url, source='nepalstock', params=params, timeout=TIMEOUT_SEC, retries=2, client=self._client
        )
        if result.ok:
            circuit_breaker.record_success('nepalstock')
            resp: httpx.Response = result.data
            try:
                parsed = resp.json()
            except Exception as e:
                return FetchResult(ok=False, source='nepalstock', error=f'JSON parse: {e}')
            return FetchResult(ok=True, data=parsed, source='nepalstock', fetched_at=result.fetched_at)
        circuit_breaker.record_failure('nepalstock')
        return result

    async def _yonepse_get(self, path: str) -> FetchResult:
        url = f'{YONEPSE_BASE}{path}'
        if circuit_breaker.is_open('yonepse'):
            logger.warning('[yonepse] circuit open, skipping')
            return FetchResult(ok=False, source='yonepse', error='circuit open')
        result = await retry_get_json(url, source='yonepse', timeout=TIMEOUT_SEC, retries=2)
        if result.ok:
            circuit_breaker.record_success('yonepse')
        else:
            circuit_breaker.record_failure('yonepse')
        return result

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_market_status(self) -> dict[str, Any]:
        result = await self._nepse_get('/api/nots/marketStatus')
        if result.ok and isinstance(result.data, dict):
            return {
                'is_open': result.data.get('isOpen', False),
                'market_phase': result.data.get('marketPhase', ''),
                'as_of': result.data.get('asOf', ''),
            }
        fallback = await self._yonepse_get('/data/market/status.json')
        if fallback.ok and isinstance(fallback.data, dict):
            return fallback.data
        return {'is_open': False, 'market_phase': 'unknown', 'as_of': ''}

    async def get_live_prices(self) -> list[dict[str, Any]]:
        await self._ensure_css()
        result = await self._nepse_get('/api/nots/security', {'sort': 'symbol', 'limit': 400})
        if result.ok and isinstance(result.data, list):
            return self._descramble(result.data)
        fallback = await self._yonepse_get('/data/market/live.json')
        if fallback.ok and isinstance(fallback.data, list):
            return fallback.data
        return []

    async def get_market_summary(self) -> list[dict] | dict:
        result = await self._nepse_get('/api/nots/nepseIndex')
        if result.ok and isinstance(result.data, dict):
            return {
                'index': result.data.get('indexValue', 0),
                'change': result.data.get('pointChange', 0),
                'percent_change': result.data.get('percentChange', 0),
                'turnover': result.data.get('turnover', 0),
                'volume': result.data.get('volume', 0),
            }
        fallback = await self._yonepse_get('/data/market/summary.json')
        if fallback.ok:
            return fallback.data
        return {}

    async def get_top_stocks(self, top_type: str = 'gainers') -> list[dict[str, Any]]:
        type_map = {'gainers': '1', 'losers': '2', 'active': '3'}
        t = type_map.get(top_type, '1')
        result = await self._nepse_get(f'/api/nots/top10/tradeGainer?type={t}')
        if result.ok and isinstance(result.data, list):
            return self._descramble(result.data)
        fallback = await self._yonepse_get('/data/market/top_stocks.json')
        if fallback.ok and isinstance(fallback.data, dict):
            key = {'gainers': 'top_gainer', 'losers': 'top_loser', 'active': 'top_turnover'}.get(top_type, 'top_gainer')
            return fallback.data.get(key, [])
        return []

    async def get_indices(self) -> list[dict[str, Any]]:
        result = await self._nepse_get('/api/nots/nepseIndex')
        if result.ok and isinstance(result.data, dict):
            subs = result.data.get('subIndices', [])
            if isinstance(subs, list):
                return subs
        return []

    async def get_security_history(self, symbol: str) -> list[dict[str, Any]]:
        result = await self._nepse_get(f'/api/nots/security/{symbol}/history')
        if result.ok and isinstance(result.data, list):
            return self._descramble(result.data)
        return []

    async def ensure_css(self) -> bool:
        return await self._ensure_css()

    def _descramble(self, data: list[dict]) -> list[dict]:
        if not self._column_map and data:
            cols = list(data[0].keys())
            if not cols:
                return data
            self._column_map = build_column_map(self._salt1, self._salt2, cols)
        if not self._column_map:
            return data
        result = []
        for item in data:
            mapped = {}
            for k, v in item.items():
                mapped[self._column_map.get(k, k)] = v
            result.append(mapped)
        return result
