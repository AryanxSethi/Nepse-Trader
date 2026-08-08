"""
Import historical OHLC data from Aabishkar2/nepse-data GitHub repo.
Usage: python -m app.db.importer NABIL
       python -m app.db.importer --all
"""

import asyncio
import csv
import io
import sys
from datetime import date, datetime

import httpx

from app.core.config import GITHUB_NEPSE_DATA
from app.db.session import async_session, init_db
from app.db.models import DailyPrice, Security
from sqlalchemy import select


async def fetch_csv(symbol: str) -> list[dict] | None:
    """Fetch CSV data for a given symbol from the nepse-data GitHub repo.

    Args:
        symbol: The stock symbol to fetch data for.

    Returns:
        A list of parsed row dicts sorted by date, or None on failure.
    """
    url = f"{GITHUB_NEPSE_DATA}/{symbol}.csv"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.text
    except Exception as e:
        print(f"[import] Failed to fetch {symbol}: {e}")
        return None

    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for row in reader:
        date_str = row.get("published_date", "").strip()
        if not date_str:
            continue
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            try:
                parsed_date = datetime.strptime(date_str, "%m/%d/%Y").date()
            except ValueError:
                continue

        rows.append({
            "symbol": symbol,
            "date": parsed_date,
            "open": _float(row.get("open")),
            "high": _float(row.get("high")),
            "low": _float(row.get("low")),
            "close": _float(row.get("close")),
            "volume": _int_or_none(row.get("traded_quantity")),
            "turnover": _float(row.get("traded_amount")),
        })

    rows.sort(key=lambda r: r["date"])
    return rows


def _float(val: str | None) -> float | None:
    """Safely convert a string value to float.

    Args:
        val: The string to convert, or None.

    Returns:
        The float value, or None if conversion fails.
    """
    if val is None:
        return None
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return None


def _int_or_none(val: str | None) -> int | None:
    """Safely convert a string value to int.

    Args:
        val: The string to convert, or None.

    Returns:
        The int value, or None if conversion fails.
    """
    if val is None:
        return None
    try:
        return int(float(val.strip()))
    except (ValueError, AttributeError):
        return None


async def import_symbol(symbol: str) -> int:
    """Import CSV data for a single symbol into the database.

    Args:
        symbol: The stock symbol to import.

    Returns:
        The number of new rows inserted.
    """
    symbol = symbol.upper().strip()
    rows = await fetch_csv(symbol)
    if not rows:
        return 0

    async with async_session() as session:
        existing = await session.execute(
            select(DailyPrice.date).where(DailyPrice.symbol == symbol)
        )
        existing_dates = {row[0] for row in existing.all()}

        new_count = 0
        for r in rows:
            if r["date"] not in existing_dates:
                session.add(DailyPrice(**r))
                new_count += 1

        if new_count:
            await session.commit()

    print(f"[import] {symbol}: {new_count} new rows (from {len(rows)} fetched)")
    return new_count


async def import_all_symbols():
    """Import CSV data for all symbols in the database."""
    await init_db()
    async with async_session() as session:
        result = await session.execute(select(Security.symbol))
        symbols = [row[0] for row in result.all()]

    total = 0
    for sym in symbols:
        count = await import_symbol(sym)
        total += count

    print(f"[import] Done. {total} total new rows across {len(symbols)} symbols.")


async def main():
    """Parse CLI args and trigger import for specified symbols or --all."""
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--all" in sys.argv or "-a" in sys.argv:
        await import_all_symbols()
    elif args:
        await init_db()
        for sym in args:
            await import_symbol(sym)
    else:
        print("Usage: python -m backend.data.import_nepse_data SYMBOL [SYMBOL...]")
        print("       python -m backend.data.import_nepse_data --all")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
