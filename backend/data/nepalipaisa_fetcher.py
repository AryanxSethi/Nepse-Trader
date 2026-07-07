"""Nepalipaisa IPO data fetcher.

Fetches IPO listings from nepalipaisa.com API and normalises status values.
"""

import logging
from datetime import datetime, timezone

from config import NEPALIPAISA_BASE
from data._http import FetchResult, retry_get_json

logger = logging.getLogger('nepalipaisa_fetcher')

STATUS_MAP = {
    'open': 'open',
    'nearing': 'open',
    'closed': 'closed',
    'upcoming': 'upcoming',
}


def _normalize_status(raw: str) -> str:
    """Map raw API status string to a canonical status value."""
    return STATUS_MAP.get(raw.lower(), 'upcoming')


async def fetch_ipos_from_nepalipaisa(page: int = 1, per_page: int = 20) -> dict | None:
    """Fetch IPO listings from nepalipaisa API, paginated.

    Returns a dict with *data*, *pager*, and *_meta*, or None on failure.
    """
    result = await retry_get_json(
        f'{NEPALIPAISA_BASE}/api/GetIpos',
        source='nepalipaisa/ipo',
        params={
            'stockSymbol': '',
            'pageNo': page,
            'itemsPerPage': per_page,
            'pagePerDisplay': 5,
        },
    )
    if not result.ok:
        logger.warning('nepalipaisa IPO fetch failed: %s', result.error)
        return None

    data = result.data
    if data.get('statusCode') != 200:
        logger.warning('nepalipaisa API error: %s', data.get('message'))
        return None

    api_result = data.get('result', {})
    items = api_result.get('data', [])
    pager = api_result.get('pager', {})

    if not items:
        return None

    total_next = pager.get('totalNextPages', -1)
    total_pages = (total_next + 1) if total_next >= 0 else 1

    normalized = []
    for item in items:
        raw_status = item.get('status', '')
        status = _normalize_status(raw_status)

        company_name = (item.get('companyName') or '').strip()
        stock_symbol = (item.get('stockSymbol') or '').strip()
        share_type = (item.get('shareType') or '').strip().lower()
        units_str = item.get('units') or '0'
        price_str = item.get('pricePerUnit') or ''

        try:
            units_num = int(str(units_str).replace(',', ''))
        except (ValueError, TypeError):
            units_num = 0

        issue_size = f'{units_num:,} shares' if units_num else ''
        price_range = f'NPR {price_str}' if price_str else 'NPR 100'

        open_date_ad = (item.get('openingDateAD') or '').strip()
        open_date_bs = (item.get('openingDateBS') or '').strip()
        close_date_ad = (item.get('closingDateAD') or '').strip()
        close_date_bs = (item.get('closingDateBS') or '').strip()

        normalized.append({
            'company': company_name,
            'symbol': stock_symbol,
            'issue_size': issue_size,
            'open_date': open_date_ad,
            'open_date_bs': open_date_bs,
            'close_date': close_date_ad,
            'close_date_bs': close_date_bs,
            'price_range': price_range,
            'status': status,
            'share_type': share_type,
            'share_registrar': (item.get('shareRegistrar') or '').strip(),
            'rating': (item.get('rating') or '').strip(),
            'sector': (item.get('sectorName') or '').strip(),
            'min_units': item.get('minUnits') or '',
            'max_units': item.get('maxUnits') or '',
            'total_amount': item.get('totalAmount') or '',
            'price_per_unit': price_str,
            'ipo_id': item.get('ipoId'),
            'status_raw': raw_status,
        })

    logger.info('nepalipaisa page %s: %d items, totalPages=%s', page, len(normalized), total_pages)

    return {
        'data': normalized,
        'pager': {
            'pageNo': pager.get('pageNo', page),
            'itemsPerPage': pager.get('itemsPerPage', per_page),
            'totalNextPages': total_next,
            'totalPages': total_pages,
        },
        '_meta': {
            'source': 'nepalipaisa',
            'updated_at': datetime.now(timezone.utc).isoformat(),
        },
    }
