"""HTTP scraper for the Sharesansar website (sharesansar.com).

Provides parsed stock data, indices, company details,
and live trading snapshots extracted from Sharesansar's HTML pages.

All public methods use an internal circuit breaker (3 failures, 60s cooloff)
and retry transient HTTP errors with exponential backoff.
"""

import asyncio
import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from config import SHARESANSAR_BASE, SHARESANSAR_TIMEOUT, DEFAULT_USER_AGENT
from data._http import CircuitBreaker

logger = logging.getLogger('sharesansar_fetcher')

class SharesansarFetcher:
    """Scrapes and parses live trading data, stock prices, and company details from sharesansar.com.

    Uses an internal ``httpx.AsyncClient`` with automatic retry and circuit-breaker
    protection. Caches today's share prices for ``TODAY_PRICE_TTL`` seconds.
    """

    CIRCUIT_BREAKER_THRESHOLD = 3
    CIRCUIT_BREAKER_COOLOFF = 60.0
    TODAY_PRICE_TTL = 120

    # Column indices in the Sharesansar live price table (/live-trading)
    LTP_TABLE_COL_SYMBOL = 1
    LTP_TABLE_COL_LTP = 2
    LTP_TABLE_COL_POINT_CHANGE = 3
    LTP_TABLE_COL_PERCENT_CHANGE = 4
    LTP_TABLE_COL_OPEN = 5
    LTP_TABLE_COL_HIGH = 6
    LTP_TABLE_COL_LOW = 7
    LTP_TABLE_COL_VOLUME = 8
    LTP_TABLE_COL_PREV_CLOSE = 9
    LTP_TABLE_MIN_COLS = 10

    # Column indices in the Sharesansar today-share-price table
    TODAY_TABLE_COL_SYMBOL = 1
    TODAY_TABLE_COL_CONFIDENCE = 2
    TODAY_TABLE_COL_OPEN = 3
    TODAY_TABLE_COL_HIGH = 4
    TODAY_TABLE_COL_LOW = 5
    TODAY_TABLE_COL_CLOSE = 6
    TODAY_TABLE_COL_LTP = 7
    TODAY_TABLE_COL_VWAP = 10
    TODAY_TABLE_COL_VOLUME = 11
    TODAY_TABLE_COL_PREV_CLOSE = 12
    TODAY_TABLE_COL_TURNOVER = 13
    TODAY_TABLE_COL_TRANSACTIONS = 14
    TODAY_TABLE_COL_RANGE_PCT = 18
    TODAY_TABLE_COL_VWAP_PCT = 19
    TODAY_TABLE_COL_AVG_120D = 20
    TODAY_TABLE_COL_AVG_180D = 21
    TODAY_TABLE_COL_HIGH_52W = 22
    TODAY_TABLE_COL_LOW_52W = 23
    TODAY_TABLE_MIN_COLS = 24

    def __init__(self):
        """Prepare the fetcher — client is lazily created on the first request."""
        self._client: httpx.AsyncClient | None = None
        self._circuit_breaker = CircuitBreaker(
            threshold=self.CIRCUIT_BREAKER_THRESHOLD,
            cooloff=self.CIRCUIT_BREAKER_COOLOFF,
        )
        self._lock = asyncio.Lock()
        self._today_price_cache: dict[str, dict] | None = None
        self._today_price_cache_ts: float = 0

    async def _init_client(self):
        """Lazily create the shared HTTP client on first use."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={'User-Agent': DEFAULT_USER_AGENT},
                timeout=SHARESANSAR_TIMEOUT,
                follow_redirects=True,
            )

    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str, params: dict | None = None, max_retries: int = 3) -> httpx.Response:
        """GET *url* with exponential-backoff retry on 5xx and network errors."""
        last_exc: Exception | None = None
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
        raise last_exc  # type: ignore[misc]

    async def _get(self, path: str) -> str | None:
        """GET *path* relative to Sharesansar base URL.

        Returns the response body as text, or *None* on failure.
        Respects the circuit breaker — skips the request if open.
        """
        await self._init_client()
        if self._circuit_breaker.is_open('sharesansar'):
            logger.warning('[sharesansar] circuit open, skipping %s', path)
            return None
        try:
            resp = await self._fetch_with_retry(self._client, f'{SHARESANSAR_BASE}{path}')
            resp.raise_for_status()
            self._circuit_breaker.record_success('sharesansar')
            return resp.text
        except Exception as e:
            self._circuit_breaker.record_failure('sharesansar')
            logger.debug('Sharesansar GET %s failed: %s', path, e)
            return None

    async def get_live_trading(self) -> dict:
        """Scrape the /live-trading page for real-time prices and indices.

        Returns
        -------
        dict
            ``{"prices": [...], "indices": [...], "timestamp": str | None}``
            where *prices* are parsed by :meth:`_parse_live_price_table` and
            *indices* by :meth:`_parse_live_indices`.
        """
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
        """Parse the live price table (``#headFixed``) into a list of stock dicts.

        Each dict contains *symbol*, *ltp*, *point_change*, *percent_change*,
        *open*, *high*, *low*, *volume*, and *prev_close*.
        """
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
            if len(cells) < self.LTP_TABLE_MIN_COLS:
                continue
            try:
                sym_link = cells[self.LTP_TABLE_COL_SYMBOL].find('a')
                sym_cell = cells[self.LTP_TABLE_COL_SYMBOL]
                symbol = sym_link.get_text(strip=True) if sym_link else sym_cell.get_text(strip=True)
                if not symbol:
                    continue
                prices.append({
                    'symbol': symbol,
                    'ltp': _parse_float(cells[self.LTP_TABLE_COL_LTP]),
                    'point_change': _parse_float(cells[self.LTP_TABLE_COL_POINT_CHANGE]),
                    'percent_change': _parse_float(cells[self.LTP_TABLE_COL_PERCENT_CHANGE]),
                    'open': _parse_float(cells[self.LTP_TABLE_COL_OPEN]),
                    'high': _parse_float(cells[self.LTP_TABLE_COL_HIGH]),
                    'low': _parse_float(cells[self.LTP_TABLE_COL_LOW]),
                    'volume': _parse_float(cells[self.LTP_TABLE_COL_VOLUME]),
                    'prev_close': _parse_float(cells[self.LTP_TABLE_COL_PREV_CLOSE]),
                })
            except (ValueError, IndexError):
                continue
        return prices

    def _parse_live_indices(self, soup: BeautifulSoup) -> list[dict]:
        """Parse index cards from the live-trading slider into a list of dicts.

        Each dict contains *name*, *value*, *percent_change*, and *turnover*.

        Sub-indices such as "banking subindex" and "development bank ind." are
        deliberately skipped because the page also returns a combined "Banking"
        index for the same sector, avoiding duplicate entries.
        """
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
            # Skip sub-indices that overlap with the main Banking/Development Bank index
            if name.lower() in ('banking subindex', 'development bank ind.'):
                continue
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
        """Return today's price details for a single *symbol*.

        Fetches and caches the full today-share-price table for **all** symbols
        on the first call, then returns only the requested symbol's entry.
        Cache expires after ``TODAY_PRICE_TTL`` seconds.

        Returns *None* if the symbol is not found or the page is unreachable.
        """
        now = asyncio.get_running_loop().time()
        async with self._lock:
            if self._today_price_cache is not None and (now - self._today_price_cache_ts) <= self.TODAY_PRICE_TTL:
                return self._today_price_cache.get(symbol.upper())
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
            if len(cells) < self.TODAY_TABLE_MIN_COLS:
                continue
            try:
                sym_link = cells[self.TODAY_TABLE_COL_SYMBOL].find('a')
                sym_cell = cells[self.TODAY_TABLE_COL_SYMBOL]
                sym = sym_link.get_text(strip=True) if sym_link else sym_cell.get_text(strip=True)
                if not sym:
                    continue
                all_prices[sym] = {
                    'vwap': _parse_float(cells[self.TODAY_TABLE_COL_VWAP]),
                    'volume': _parse_float(cells[self.TODAY_TABLE_COL_VOLUME]),
                    'prev_close': _parse_float(cells[self.TODAY_TABLE_COL_PREV_CLOSE]),
                    'turnover': _parse_float(cells[self.TODAY_TABLE_COL_TURNOVER]),
                    'transactions': _parse_int(cells[self.TODAY_TABLE_COL_TRANSACTIONS]),
                    'avg_120d': _parse_float(cells[self.TODAY_TABLE_COL_AVG_120D]),
                    'avg_180d': _parse_float(cells[self.TODAY_TABLE_COL_AVG_180D]),
                    'high_52w': _parse_float(cells[self.TODAY_TABLE_COL_HIGH_52W]),
                    'low_52w': _parse_float(cells[self.TODAY_TABLE_COL_LOW_52W]),
                    'close': _parse_float(cells[self.TODAY_TABLE_COL_CLOSE]),
                    'ltp': _parse_float(cells[self.TODAY_TABLE_COL_LTP]),
                    'open': _parse_float(cells[self.TODAY_TABLE_COL_OPEN]),
                    'high': _parse_float(cells[self.TODAY_TABLE_COL_HIGH]),
                    'low': _parse_float(cells[self.TODAY_TABLE_COL_LOW]),
                    'confidence_score': _parse_confidence(cells[self.TODAY_TABLE_COL_CONFIDENCE]),
                    'vwap_pct': _parse_float(cells[self.TODAY_TABLE_COL_VWAP_PCT]),
                    'range_pct': _parse_float(cells[self.TODAY_TABLE_COL_RANGE_PCT]),
                }
            except (ValueError, IndexError):
                continue
        async with self._lock:
            self._today_price_cache = all_prices
            self._today_price_cache_ts = now
        return self._today_price_cache.get(symbol.upper())

    async def get_company_detail(self, symbol: str) -> dict:
        """Scrape the company profile page for the given *symbol*.

        Returns a dict that may contain company info (sector, shares, contact),
        *price_header* (current price, OHLC, volume, 52-week range, averages),
        *pivot* (pivot analysis levels), and *moving* (moving-average signals).
        """
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
        """Parse the company info table (``#myTableCInfo``) from a profile page.

        Extracts *sector*, *listed_shares*, *paid_up*, *address*, *phone*,
        *email*, and *website*. Returns *None* if the table is missing.
        """
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
        """Parse the price-header section of a company profile page.

        Extracts *current_price*, *open*, *high*, *low*, *volume*,
        *high_52w*/*low_52w*, *avg_120d*, and *avg_180d*.
        Returns *None* if no price-header div is found.
        """
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
        """Extract pivot-analysis levels (S3–R3) from a company profile page.

        Returns a dict with keys *s3*, *s2*, *s1*, *pp*, *r1*, *r2*, *r3*
        or *None* if no pivot analysis section exists.
        """
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
        """Extract moving-average signals (MA5–MA200) from a profile page.

        Each entry in the returned dict contains *value* and *signal*
        (one of ``"BULLISH"``, ``"BEARISH"``, ``"NEUTRAL"``).
        Returns *None* if no moving analysis section exists.
        """
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

    def circuit_breaker_status(self, source: str) -> str:
        """Return the current circuit-breaker state (*closed*, *open*, *half-open*)."""
        return self._circuit_breaker.status(source)

    async def stop(self):
        """Close the underlying HTTP client and release resources."""
        if self._client:
            await self._client.aclose()
            self._client = None


def _parse_float(cell: Any) -> float | None:
    """Extract a float from a BeautifulSoup ``<td>`` cell, or *None*."""
    try:
        text = cell.get_text(strip=True).replace(',', '')
        return float(text) if text else None
    except (ValueError, AttributeError):
        return None


def _parse_int(cell: Any) -> int | None:
    """Extract an integer from a BeautifulSoup ``<td>`` cell, or *None*."""
    val = _parse_float(cell)
    return int(val) if val is not None else None


def _parse_float_from_line(line: str) -> float | None:
    """Parse a ``"label: value"`` line into a float, or *None*."""
    parts = line.split(':')
    if len(parts) >= 2:
        try:
            return float(parts[-1].replace(',', '').strip())
        except ValueError:
            pass
    return None


def _parse_confidence(cell: Any) -> str | None:
    """Convert a confidence-score cell into a human label.

    Sharesansar reports confidence as 1/2/3 or as a 0–100 percentage.
    Returns ``"High"``, ``"Medium"``, ``"Low"``, or the raw text.
    """
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
