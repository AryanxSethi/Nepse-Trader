import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup

from data._http import CircuitBreaker

logger = logging.getLogger('sharesansar_fetcher')

SHARESANSAR_BASE = 'https://www.sharesansar.com'
TIMEOUT_SEC = 20
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

circuit_breaker = CircuitBreaker(threshold=3, cooloff=60.0)

_sharesansar_lock = asyncio.Lock()

_CSRF_CACHE: dict[str, Any] = {}
_CSRF_CACHE_TTL = 300
_CSRF_CACHE_TIME: float = 0

_indices_table_cache: list[dict] | None = None
_indices_table_cache_ts: float = 0
_INDICES_TABLE_TTL = 300

_today_price_cache: dict[str, dict] | None = None
_today_price_cache_ts: float = 0
_TODAY_PRICE_TTL = 120


class SharesansarFetcher:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _init_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={'User-Agent': USER_AGENT},
                timeout=TIMEOUT_SEC,
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
                    logger.warning(
                        'GET %s failed (%s), retrying (%d/%d)',
                        url, e, attempt + 1, max_retries,
                    )
                    await asyncio.sleep(2 ** attempt)
        raise last_exc

    async def _get(self, path: str) -> str | None:
        await self._init_client()
        if circuit_breaker.is_open('sharesansar'):
            logger.warning('[sharesansar] circuit open, skipping %s', path)
            return None
        try:
            resp = await self._fetch_with_retry(self._client, f'{SHARESANSAR_BASE}{path}')
            resp.raise_for_status()
            circuit_breaker.record_success('sharesansar')
            return resp.text
        except Exception as e:
            circuit_breaker.record_failure('sharesansar')
            logger.debug('Sharesansar GET %s failed: %s', path, e)
            return None

    async def _post(self, path: str, data: dict[str, str]) -> str | None:
        await self._init_client()
        if circuit_breaker.is_open('sharesansar'):
            return None
        try:
            resp = await self._client.post(f'{SHARESANSAR_BASE}{path}', data=data)
            resp.raise_for_status()
            circuit_breaker.record_success('sharesansar')
            return resp.text
        except Exception as e:
            circuit_breaker.record_failure('sharesansar')
            logger.debug('Sharesansar POST %s failed: %s', path, e)
            return None

    async def get_live_trading(self) -> dict:
        html = await self._get('/live-trading')
        if not html:
            return {'prices': [], 'indices': [], 'timestamp': None}
        soup = BeautifulSoup(html, 'html.parser')
        timestamp_el = soup.find('span', id='dDate')
        timestamp = timestamp_el.get_text(strip=True) if timestamp_el else None
        prices = self._parse_live_price_table(soup)
        indices = self._parse_live_indices(soup)
        return {'prices': prices, 'indices': indices, 'timestamp': timestamp}

    def _parse_live_price_table(self, soup: BeautifulSoup) -> list[dict]:
        table = soup.find('table', id='headFixed')
        if not table:
            table = soup.find('table', class_='table')
        if not table:
            return []
        tbody = table.find('tbody')
        if not tbody:
            return []
        rows = tbody.find_all('tr')
        prices = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 10:
                continue
            try:
                sym_link = cells[1].find('a')
                symbol = sym_link.get_text(strip=True) if sym_link else cells[1].get_text(strip=True)
                if not symbol:
                    continue
                prices.append({
                    'symbol': symbol,
                    'ltp': _parse_float(cells[2]),
                    'point_change': _parse_float(cells[3]),
                    'percent_change': _parse_float(cells[4]),
                    'open': _parse_float(cells[5]),
                    'high': _parse_float(cells[6]),
                    'low': _parse_float(cells[7]),
                    'volume': _parse_float(cells[8]),
                    'prev_close': _parse_float(cells[9]),
                })
            except (ValueError, IndexError):
                continue
        return prices

    def _parse_live_indices(self, soup: BeautifulSoup) -> list[dict]:
        wrapper = soup.find('div', class_='liveTradingWrapper')
        if not wrapper:
            return []
        slider = wrapper.find('div', class_='slider1')
        if not slider:
            slider = wrapper
        items = slider.find_all('div', class_='col-md-3') if slider else []
        indices = []
        for item in items:
            h4 = item.find('h4')
            name = h4.get_text(strip=True) if h4 else None
            if not name:
                continue
            if name.lower() in ('banking subindex', 'development bank ind.'):
                pass
            value_span = item.find('span', class_='mu-value')
            pct_span = item.find('span', class_='mu-percent')
            price_p = item.find('p', class_='mu-price')
            if value_span:
                try:
                    val = float(value_span.get_text(strip=True).replace(',', ''))
                except (ValueError, AttributeError):
                    continue
                pct_text = pct_span.get_text(strip=True).replace('%', '').replace(',', '') if pct_span else '0'
                try:
                    pct = float(pct_text) if pct_text else 0
                except ValueError:
                    pct = 0
                turnover = None
                if price_p:
                    try:
                        turnover = float(price_p.get_text(strip=True).replace(',', ''))
                    except ValueError:
                        pass
                indices.append({
                    'name': name,
                    'value': val,
                    'percent_change': pct,
                    'turnover': turnover,
                })
        return indices

    async def get_today_share_price_for_symbol(self, symbol: str) -> dict | None:
        global _today_price_cache, _today_price_cache_ts
        now = asyncio.get_running_loop().time()
        async with _sharesansar_lock:
            if _today_price_cache is not None and (now - _today_price_cache_ts) <= _TODAY_PRICE_TTL:
                return _today_price_cache.get(symbol.upper())
        html = await self._get('/today-share-price')
        if not html:
            return None
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', id='headFixed')
        if not table:
            table = soup.find('table', class_='table')
        if not table:
            return None
        tbody = table.find('tbody')
        if not tbody:
            return None
        all_prices: dict[str, dict] = {}
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 24:
                continue
            try:
                sym_link = cells[1].find('a')
                sym = sym_link.get_text(strip=True) if sym_link else cells[1].get_text(strip=True)
                if not sym:
                    continue
                all_prices[sym] = {
                    'vwap': _parse_float(cells[10]),
                    'volume': _parse_float(cells[11]),
                    'prev_close': _parse_float(cells[12]),
                    'turnover': _parse_float(cells[13]),
                    'transactions': _parse_int(cells[14]),
                    'avg_120d': _parse_float(cells[20]),
                    'avg_180d': _parse_float(cells[21]),
                    'high_52w': _parse_float(cells[22]),
                    'low_52w': _parse_float(cells[23]),
                    'close': _parse_float(cells[6]),
                    'ltp': _parse_float(cells[7]),
                    'open': _parse_float(cells[3]),
                    'high': _parse_float(cells[4]),
                    'low': _parse_float(cells[5]),
                    'confidence_score': _parse_confidence(cells[2]),
                    'vwap_pct': _parse_float(cells[19]),
                    'range_pct': _parse_float(cells[18]),
                }
            except (ValueError, IndexError):
                continue
        async with _sharesansar_lock:
            _today_price_cache = all_prices
            _today_price_cache_ts = now
        return _today_price_cache.get(symbol.upper())

    async def get_company_detail(self, symbol: str) -> dict:
        html = await self._get(f'/company/{symbol.upper()}')
        if not html:
            return {}
        soup = BeautifulSoup(html, 'html.parser')
        result: dict[str, Any] = {}
        company_info = self._parse_company_info_table(soup)
        if company_info:
            result.update(company_info)
        price_header = self._parse_price_header(soup)
        if price_header:
            result['price_header'] = price_header
        pivot = self._parse_pivot_analysis(soup)
        if pivot:
            result['pivot'] = pivot
        moving = self._parse_moving_analysis(soup)
        if moving:
            result['moving'] = moving
        return result

    def _parse_company_info_table(self, soup: BeautifulSoup) -> dict | None:
        table = soup.find('table', id='myTableCInfo')
        if not table:
            return None
        rows = table.find_all('tr')
        info = {}
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            if not th or not td:
                continue
            label = th.get_text(strip=True).lower()
            value = td.get_text(strip=True)
            if 'sector' in label:
                info['sector'] = value
            elif 'listed shares' in label:
                info['listed_shares'] = value
            elif 'paid up' in label and 'total' not in label:
                info['paid_up'] = value
            elif 'address' in label:
                info['address'] = value
            elif 'phone' in label:
                info['phone'] = value
            elif 'email' in label:
                info['email'] = value
            elif 'website' in label:
                info['website'] = value
        return info if info else None

    def _parse_price_header(self, soup: BeautifulSoup) -> dict | None:
        header_div = soup.find('div', class_='price-header')
        if not header_div:
            header_div = soup.find('div', class_='company-price-header')
        if not header_div:
            return None
        text = header_div.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        header: dict[str, Any] = {}
        for line in lines:
            lower = line.lower()
            if line.startswith('Rs.'):
                try:
                    header['current_price'] = float(line.replace('Rs.', '').replace(',', '').strip())
                except ValueError:
                    pass
            elif 'open' in lower and ':' in line:
                header['open'] = _parse_float_from_line(line)
            elif 'high' in lower and ':' in line:
                header['high'] = _parse_float_from_line(line)
            elif 'low' in lower and ':' in line:
                header['low'] = _parse_float_from_line(line)
            elif 'volume' in lower and ':' in line:
                header['volume'] = _parse_float_from_line(line)
            elif '52 week' in lower or '52-week' in lower:
                parts = line.split('-')
                if len(parts) >= 2:
                    try:
                        header['high_52w'] = float(parts[0].replace(',', '').strip())
                        header['low_52w'] = float(parts[-1].replace(',', '').strip())
                    except ValueError:
                        pass
            elif '120 days' in lower or '120 day' in lower:
                header['avg_120d'] = _parse_float_from_line(line)
            elif '180 days' in lower or '180 day' in lower:
                header['avg_180d'] = _parse_float_from_line(line)
        return header if header else None

    def _parse_pivot_analysis(self, soup: BeautifulSoup) -> dict | None:
        for col in soup.find_all('div', class_='col-md-6'):
            if 'pivot analysis' in col.get_text(strip=True).lower():
                text = col.get_text(strip=True)
                pivot: dict[str, float] = {}
                labels = {'S3': 's3', 'S2': 's2', 'S1': 's1', 'PP': 'pp', 'R1': 'r1', 'R2': 'r2', 'R3': 'r3'}
                for label, key in labels.items():
                    match = re.search(rf'{label}[^0-9]*([\d,]+\.?\d*)', text)
                    if match:
                        try:
                            pivot[key] = float(match.group(1).replace(',', ''))
                        except ValueError:
                            pass
                return pivot if pivot else None
        return None

    def _parse_moving_analysis(self, soup: BeautifulSoup) -> dict | None:
        for col in soup.find_all('div', class_='col-md-6'):
            if 'moving analysis' in col.get_text(strip=True).lower():
                table = col.find('table')
                if not table:
                    continue
                rows = table.find_all('tr')
                moving: dict[str, Any] = {}
                for i in range(0, len(rows) - 1, 2):
                    label_cell = rows[i].find('td')
                    if not label_cell:
                        continue
                    label = label_cell.get_text(strip=True).upper()
                    if not label.startswith('MA'):
                        continue
                    val_cell = rows[i].find_all('td')
                    value = _parse_float(val_cell[1]) if len(val_cell) > 1 else None
                    signal = 'NEUTRAL'
                    if i + 1 < len(rows):
                        sig_cell = rows[i + 1].find_all('td')
                        if len(sig_cell) >= 2:
                            sig_text = sig_cell[1].get_text(strip=True).upper()
                            if 'BULLISH' in sig_text:
                                signal = 'BULLISH'
                            elif 'BEARISH' in sig_text:
                                signal = 'BEARISH'
                    moving[label.lower()] = {'value': value, 'signal': signal}
                return moving if moving else None
        return None

    async def get_floorsheet(self, symbol: str) -> list[dict]:
        company_id = await self._get_company_id(symbol)
        if not company_id:
            return []
        csrf = await self._get_csrf_token(f'/company/{symbol.upper()}')
        if not csrf:
            return []
        html = await self._post('/company-floor-sheet', {
            '_token': csrf,
            'company': str(company_id),
        })
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        if not table:
            return []
        tbody = table.find('tbody')
        if not tbody:
            return []
        rows = []
        for tr in tbody.find_all('tr'):
            cells = tr.find_all('td')
            if len(cells) < 6:
                continue
            try:
                rows.append({
                    'contract_no': cells[1].get_text(strip=True),
                    'buyer': cells[2].get_text(strip=True),
                    'seller': cells[3].get_text(strip=True),
                    'quantity': _parse_int(cells[4]),
                    'rate': _parse_float(cells[5]),
                    'amount': _parse_float(cells[6]) if len(cells) > 6 else None,
                })
            except (ValueError, IndexError):
                continue
        return rows

    async def _get_company_id(self, symbol: str) -> str | None:
        html = await self._get(f'/company/{symbol.upper()}')
        if not html:
            return None
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div', id='companyid')
        if div:
            return div.get_text(strip=True)
        return None

    async def _get_csrf_token(self, path: str) -> str | None:
        global _CSRF_CACHE, _CSRF_CACHE_TIME
        now = asyncio.get_running_loop().time()
        async with _sharesansar_lock:
            if _CSRF_CACHE.get('token') and (now - _CSRF_CACHE_TIME) < _CSRF_CACHE_TTL:
                return _CSRF_CACHE['token']
        html = await self._get(path)
        if not html:
            return None
        soup = BeautifulSoup(html, 'html.parser')
        meta = soup.find('meta', attrs={'name': '_token'})
        if meta and meta.get('content'):
            async with _sharesansar_lock:
                _CSRF_CACHE['token'] = meta['content']
                _CSRF_CACHE_TIME = now
            return meta['content']
        return None

    async def get_all_indices(self) -> list[dict]:
        global _indices_table_cache, _indices_table_cache_ts
        now = asyncio.get_running_loop().time()
        async with _sharesansar_lock:
            if _indices_table_cache is not None and (now - _indices_table_cache_ts) < _INDICES_TABLE_TTL:
                return _indices_table_cache
        html = await self._get('/market')
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        indices = self._parse_market_indices(soup)
        if indices:
            async with _sharesansar_lock:
                _indices_table_cache = indices
                _indices_table_cache_ts = now
        return indices

    def _parse_market_indices(self, soup: BeautifulSoup) -> list[dict]:
        table = soup.find('table', class_='table')
        if not table:
            return []
        rows = table.find_all('tr')
        indices = []
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
            try:
                name = cells[0].get_text(strip=True)
                indices.append({
                    'name': name,
                    'open': _parse_float(cells[1]),
                    'high': _parse_float(cells[2]),
                    'low': _parse_float(cells[3]),
                    'close': _parse_float(cells[4]),
                    'point_change': _parse_float(cells[5]),
                    'percent_change': _parse_float(cells[6]),
                    'turnover': _parse_float(cells[7]) if len(cells) > 7 else None,
                })
            except (ValueError, IndexError):
                continue
        return indices

    async def stop(self):
        if self._client:
            await self._client.aclose()
            self._client = None


def _parse_float(cell) -> float | None:
    try:
        text = cell.get_text(strip=True).replace(',', '')
        return float(text) if text else None
    except (ValueError, AttributeError):
        return None


def _parse_int(cell) -> int | None:
    val = _parse_float(cell)
    return int(val) if val is not None else None


def _parse_float_from_line(line: str) -> float | None:
    parts = line.split(':')
    if len(parts) >= 2:
        try:
            return float(parts[-1].replace(',', '').strip())
        except ValueError:
            pass
    return None


def _parse_confidence(cell) -> str | None:
    text = cell.get_text(strip=True)
    if not text:
        return None
    text = text.strip()
    if text == '3':
        return 'High'
    elif text == '2':
        return 'Medium'
    elif text == '1':
        return 'Low'
    try:
        val = float(text)
        if val >= 80:
            return 'High'
        elif val >= 50:
            return 'Medium'
        else:
            return 'Low'
    except ValueError:
        return text if text else None
