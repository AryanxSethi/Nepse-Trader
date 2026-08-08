"""IPO data loader — tries nepalipaisa API, falls back to static ipos.json."""

import json
import logging
from datetime import datetime, timezone

from app.providers.nepalipaisa import fetch_ipos_from_nepalipaisa

logger = logging.getLogger('fetcher_ipo')

from app.core.config import DATA_DIR

IPO_JSON_PATH = DATA_DIR / "ipos.json"


def _load_static(page: int, per_page: int) -> dict:
    """Load IPO data from the static ipos.json file with pagination."""
    if not IPO_JSON_PATH.exists():
        return {'data': [], 'pager': {'pageNo': 1, 'itemsPerPage': per_page, 'totalNextPages': -1, 'totalPages': 1}, '_meta': {'source': 'static', 'updated_at': ''}}
    try:
        with open(IPO_JSON_PATH, encoding='utf-8') as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning('Failed to load ipos.json: %s', e)
        return {'data': [], 'pager': {'pageNo': 1, 'itemsPerPage': per_page, 'totalNextPages': -1, 'totalPages': 1}, '_meta': {'source': 'static', 'updated_at': ''}}

    all_items = []
    defaults = {
        'open_date_bs': '',
        'close_date_bs': '',
        'share_type': '',
        'share_registrar': '',
        'rating': '',
        'sector': '',
        'min_units': '',
        'max_units': '',
        'price_per_unit': '',
    }
    for item in raw.get('upcoming', []):
        all_items.append({**defaults, **item})
    for item in raw.get('recently_closed', []):
        all_items.append({**defaults, **item, 'status': 'closed'})

    all_items.sort(key=lambda x: x.get('ipo_id', 0), reverse=True)
    total = len(all_items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = all_items[start:end]

    return {
        'data': page_items,
        'pager': {
            'pageNo': page,
            'itemsPerPage': per_page,
            'totalNextPages': total_pages - 1,
            'totalPages': total_pages,
        },
        '_meta': {
            'source': 'static',
            'updated_at': datetime.now(timezone.utc).isoformat(),
        },
    }


async def load_ipos(page: int = 1, per_page: int = 20) -> dict:
    """Load IPOs — try nepalipaisa first, fall back to static JSON on failure."""
    result = await fetch_ipos_from_nepalipaisa(page=page, per_page=per_page)
    if result and result.get('data'):
        return result

    logger.info('nepalipaisa returned no data, falling back to static ipos.json')
    return _load_static(page, per_page)
