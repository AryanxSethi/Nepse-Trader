"""Daily price updater for yonepse LTP data and signal generation."""

import logging
from datetime import date, timedelta
import httpx
from sqlalchemy import select, func

from app.core.config import YONEPSE_BASE
from app.db.session import async_session
from app.db.models import DailyPrice
from app.analysis.signals import generate_signals

logger = logging.getLogger('updater')


def _parse_series_entry(entry: list) -> dict | None:
    """Parse a yonepse daily LTP series entry.
    Format: [index, price, volume, turnover, trades]
    Index 0 = open, Index 1 = close/last
    """
    if not entry or len(entry) < 2:
        return None
    price = entry[1]
    if not isinstance(price, (int, float)) or price <= 0:
        return None
    return {
        "price": float(price),
        "volume": int(entry[2]) if len(entry) > 2 and entry[2] else 0,
        "turnover": float(entry[3]) if len(entry) > 3 and entry[3] else 0.0,
        "trades": int(entry[4]) if len(entry) > 4 and entry[4] else 0,
    }


async def update_daily_prices(target_date: date | None = None) -> int:
    """Fetch daily LTP from yonepse for the given date and upsert into DailyPrice.
    Returns count of records inserted.
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    
    date_str = target_date.strftime("%Y-%m-%d")
    url = f"{YONEPSE_BASE}/data/ltp/daily/{date_str}.json"
    
    inserted = 0
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return 0
            
            raw = resp.json()
            series = raw.get("series", {})
            if not series:
                return 0
            
            async with async_session() as session:
                existing = set()
                rows = await session.execute(
                    select(DailyPrice.date, DailyPrice.symbol)
                    .where(DailyPrice.date == target_date)
                )
                for r in rows:
                    existing.add((r[0], r[1]))
                
                for symbol, entries in series.items():
                    if not entries:
                        continue
                    
                    if (target_date, symbol) in existing:
                        continue
                    
                    open_entry = _parse_series_entry(entries[0])
                    close_entry = _parse_series_entry(entries[-1]) if len(entries) > 1 else open_entry
                    
                    if not close_entry:
                        continue
                    
                    dp = DailyPrice(
                        symbol=symbol,
                        date=target_date,
                        close=close_entry["price"],
                        open=open_entry["price"] if open_entry else close_entry["price"],
                        high=max(
                            open_entry["price"] if open_entry else close_entry["price"],
                            close_entry["price"],
                        ),
                        low=min(
                            open_entry["price"] if open_entry else close_entry["price"],
                            close_entry["price"],
                        ),
                        volume=close_entry["volume"],
                        turnover=close_entry["turnover"],
                    )
                    session.add(dp)
                    inserted += 1
                
                await session.commit()
    
    except Exception as e:
        logger.error("update_daily_prices(%s) failed: %s", target_date, e)
        return 0
    
    return inserted


async def run_daily_update():
    """Backfill missing daily prices from last stored date up to yesterday.

    Skips weekends. Runs signal generation after successful backfill.
    """
    async with async_session() as session:
        last_date_row = await session.execute(
            select(func.max(DailyPrice.date))
        )
        last_date = last_date_row.scalar()

    if last_date is None:
        return 0

    today = date.today()
    total = 0
    current = last_date + timedelta(days=1)
    while current < today:
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue
        count = await update_daily_prices(current)
        total += count
        current += timedelta(days=1)

    if total > 0:
        await generate_signals()

    return total
