import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger('nepalipaisa_fetcher')

NEPALIPAISA_BASE = 'https://nepalipaisa.com'
TIMEOUT_SEC = 15

STATUS_MAP = {
    'open': 'open',
    'nearing': 'open',
    'closed': 'closed',
    'upcoming': 'upcoming',
}


def _normalize_status(raw: str) -> str:
    return STATUS_MAP.get(raw.lower(), 'upcoming')


async def fetch_ipos_from_nepalipaisa(page: int = 1, per_page: int = 20) -> dict | None:
    async with httpx.AsyncClient(timeout=TIMEOUT_SEC, follow_redirects=True) as client:
        try:
            resp = await client.get(
                f'{NEPALIPAISA_BASE}/api/GetIpos',
                params={
                    'stockSymbol': '',
                    'pageNo': page,
                    'itemsPerPage': per_page,
                    'pagePerDisplay': 5,
                },
            )
            if resp.status_code != 200:
                logger.warning('nepalipaisa returned %s on page %s', resp.status_code, page)
                return None
            data = resp.json()
            if data.get('statusCode') != 200:
                logger.warning('nepalipaisa API error on page %s: %s', page, data.get('message'))
                return None
        except httpx.TimeoutException:
            logger.warning('nepalipaisa timeout on page %s', page)
            return None
        except Exception as e:
            logger.warning('nepalipaisa fetch failed on page %s: %s', page, e)
            return None

    result = data.get('result', {})
    items = result.get('data', [])
    pager = result.get('pager', {})

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

        if price_str:
            price_range = f'NPR {price_str}'
        else:
            price_range = 'NPR 100'

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
