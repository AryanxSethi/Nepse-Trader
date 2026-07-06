import asyncio
import json
import logging
import time as _t
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from config import MEROLAGANI_BASE, MEROLAGANI_TIMEOUT, DEFAULT_USER_AGENT
from data._http import CircuitBreaker

logger = logging.getLogger('merolagani_fetcher')

class MerolaganiFetcher:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._circuit_breaker = CircuitBreaker(threshold=3, cooloff=60.0)

    async def _init_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={'User-Agent': DEFAULT_USER_AGENT},
                timeout=MEROLAGANI_TIMEOUT,
                follow_redirects=True,
            )

    async def _fetch_with_retry(self, client, url, params=None, max_retries=3):
        last_exc = None
        for attempt in range(max_retries):
            try:
                resp = await client.get(url, params=params)
                if resp.status_code >= 500:
                    if attempt < max_retries - 1:
                        logger.warning(
                            'GET %s returned %s, retrying (%d/%d)',
                            url, resp.status_code, attempt + 1, max_retries,
                        )
                        await asyncio.sleep(2 ** attempt)
                        continue
                    resp.raise_for_status()
                return resp
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException) as e:
                last_exc = e
                if attempt < max_retries - 1:
                    (logger.debug if str(e) == '' else logger.warning)(
                        'GET %s failed (%s), retrying (%d/%d)',
                        url, e, attempt + 1, max_retries,
                    )
                    await asyncio.sleep(2 ** attempt)
        raise last_exc

    async def _get(self, path: str) -> str | None:
        await self._init_client()
        if self._circuit_breaker.is_open('merolagani'):
            logger.debug('[merolagani] circuit open, skipping %s', path)
            return None
        try:
            resp = await self._fetch_with_retry(self._client, f'{MEROLAGANI_BASE}{path}')
            resp.raise_for_status()
            self._circuit_breaker.record_success('merolagani')
            return resp.text
        except Exception as e:
            self._circuit_breaker.record_failure('merolagani')
            logger.debug('Merolagani GET %s failed: %s', path, e)
            return None

    async def get_live_prices(self) -> list[dict]:
        html = await self._get('/LatestMarket.aspx')
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='live-trading')
        if not table:
            return []
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else []

        turnover_map: dict[str, float] = {}
        for t in soup.find_all('table'):
            if t.get('data-live', '') == 'turnovers':
                for tr in t.find_all('tr', recursive=False)[1:]:
                    cells = tr.find_all('td')
                    if len(cells) >= 2:
                        sym = cells[0].get_text(strip=True)
                        txt = cells[1].get_text(strip=True).replace(',', '')
                        try:
                            turnover_map[sym] = float(txt) if txt else 0
                        except ValueError:
                            pass

        prices = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 6:
                try:
                    symbol = cells[0].get_text(strip=True)
                    ltp_text = cells[1].get_text(strip=True).replace(',', '')
                    change_text = cells[2].get_text(strip=True).replace('%', '').replace(',', '')
                    open_text = cells[3].get_text(strip=True).replace(',', '')
                    high_text = cells[4].get_text(strip=True).replace(',', '')
                    low_text = cells[5].get_text(strip=True).replace(',', '')
                    prices.append({
                        'symbol': symbol,
                        'ltp': float(ltp_text) if ltp_text else 0,
                        'percent_change': float(change_text) if change_text else 0,
                        'open': float(open_text) if open_text else 0,
                        'high': float(high_text) if high_text else 0,
                        'low': float(low_text) if low_text else 0,
                        'turnover': turnover_map.get(symbol, 0),
                    })
                except (ValueError, IndexError):
                    continue
        return prices

    async def get_market_summary(self) -> dict:
        html = await self._get('/LatestMarket.aspx')
        if not html:
            return {}
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        result = {}

        for t in tables:
            live = t.get('data-live', '')
            rows = t.find_all('tr', recursive=False)
            if not rows or len(rows) < 2:
                continue

            if live == 'gainers' and 'gainers' not in result:
                result['gainers'] = self._parse_gainers_losers(rows)
            elif live == 'losers' and 'losers' not in result:
                result['losers'] = self._parse_gainers_losers(rows)
            elif live == 'turnovers' and 'turnovers' not in result:
                result['turnovers'] = self._parse_turnovers(rows)
            elif live == 'sectors' and 'sectors' not in result:
                result['sectors'] = self._parse_sectors(rows)

        return result

    async def get_index_history_page(self) -> str | None:
        return await self._get('/Indices.aspx')

    async def get_live_index(self) -> dict | None:
        if self._circuit_breaker.is_open('merolagani'):
            return None
        try:
            conn_data = json.dumps([{'name': 'stocktickerhub'}])

            def _signalr() -> dict | None:
                with httpx.Client(
                    headers={'User-Agent': DEFAULT_USER_AGENT},
                    timeout=MEROLAGANI_TIMEOUT, verify=False,
                ) as c:
                    c.get(f'{MEROLAGANI_BASE}/LatestMarket.aspx')
                    neg = c.post(
                        f'{MEROLAGANI_BASE}/signalr/negotiate',
                        data={'connectionData': conn_data},
                    )
                    if neg.status_code != 200:
                        return None
                    neg_data = neg.json()
                    ct = neg_data['ConnectionToken']
                    proto = neg_data.get('ProtocolVersion', '1.2')

                    qs = (
                        f'transport=longPolling'
                        f'&connectionToken={quote(ct)}'
                        f'&connectionData={quote(conn_data)}'
                        f'&clientProtocol={quote(proto)}'
                    )

                    for _ in range(6):
                        try:
                            sr = c.get(
                                f'{MEROLAGANI_BASE}/signalr/start?{qs}',
                                timeout=20,
                            )
                            if sr.status_code == 200:
                                return sr.json()
                        except httpx.TimeoutException:
                            _t.sleep(1)
                            continue
                    return None

            result_data = await asyncio.to_thread(_signalr)
            if not result_data:
                return None

            for msg in result_data.get('M', []):
                args = msg.get('A', [])
                if args and isinstance(args[0], dict):
                    raw_indices = args[0].get('Indices', {})
                    if isinstance(raw_indices, dict):
                        out: dict[str, dict] = {}
                        for name, entry in raw_indices.items():
                            if isinstance(entry, dict):
                                v = entry.get('v')
                                pc = entry.get('pc', 0)
                                change = round(v * pc / 100, 2) if v and pc else None
                                out[name] = {
                                    'name': name,
                                    'currentValue': v,
                                    'change': change,
                                    'perChange': pc,
                                }
                        if out:
                            self._circuit_breaker.record_success('merolagani')
                            return out

            self._circuit_breaker.record_success('merolagani')
            return None
        except Exception as e:
            logger.debug('Merolagani SignalR index poll failed: %s', e)
            self._circuit_breaker.record_failure('merolagani')
            return None

    def _parse_gainers_losers(self, rows):
        items = []
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) >= 7:
                try:
                    symbol = cells[0].get_text(strip=True)
                    ltp_text = cells[1].get_text(strip=True).replace(',', '')
                    change_text = cells[2].get_text(strip=True).replace('%', '').replace(',', '')
                    items.append({
                        'symbol': symbol,
                        'ltp': float(ltp_text) if ltp_text else 0,
                        'percent_change': float(change_text) if change_text else 0,
                    })
                except (ValueError, IndexError):
                    continue
        return items

    def _parse_turnovers(self, rows):
        items = []
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) >= 3:
                try:
                    symbol = cells[0].get_text(strip=True)
                    turnover_text = cells[1].get_text(strip=True).replace(',', '')
                    ltp_text = cells[2].get_text(strip=True).replace(',', '')
                    items.append({
                        'symbol': symbol,
                        'turnover': float(turnover_text) if turnover_text else 0,
                        'ltp': float(ltp_text) if ltp_text else 0,
                    })
                except (ValueError, IndexError):
                    continue
        return items

    def _parse_sectors(self, rows):
        items = []
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) >= 2:
                try:
                    name = cells[0].get_text(strip=True)
                    turnover_text = cells[1].get_text(strip=True).replace(',', '')
                    items.append({
                        'name': name,
                        'turnover': float(turnover_text) if turnover_text else 0,
                    })
                except ValueError:
                    continue
        return items

    async def get_company_detail(self, symbol: str) -> dict:
        html = await self._get(f'/CompanyDetail.aspx?symbol={symbol.upper()}')
        if not html:
            return {}
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='table-zeromargin')
        if not table:
            table = soup.find('table', id=lambda x: x and 'accordion' in x) or soup.find('table', id='accordion')
        if not table:
            return {}
        rows = table.find_all('tr')
        result = {}
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            if not th or not td:
                continue
            label = th.get_text(strip=True).lower()
            value = td.get_text(strip=True)
            if 'sector' in label and 'sector' not in result:
                result['sector'] = value
            elif 'shares outstanding' in label:
                continue
            elif 'market price' in label:
                result['market_price'] = value
            elif '% change' in label:
                result['percent_change'] = value
            elif 'last traded on' in label:
                result['last_traded_on'] = value
            elif '52 weeks' in label or '52 week' in label:
                parts = value.replace('-', ' - ').split('-')
                if len(parts) >= 2:
                    result['52w_high'] = parts[0].strip()
                    result['52w_low'] = parts[-1].strip()
                else:
                    result['52w_range'] = value
            elif '120 day average' in label:
                result['120d_avg'] = value
            elif '1 year yield' in label:
                result['1y_yield'] = value
        return result

    def circuit_breaker_status(self, source: str) -> str:
        return self._circuit_breaker.status(source)

    async def stop(self):
        if self._client:
            await self._client.aclose()
            self._client = None
