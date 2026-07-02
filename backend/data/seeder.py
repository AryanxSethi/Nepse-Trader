import asyncio
import httpx
from datetime import datetime
from sqlalchemy import select
from database import async_session, init_db
from models import Security, DailyPrice
from data.fetcher import fetch_all_securities

NEPSEMAN_BASE = "https://nepseman-api-production.up.railway.app"


async def seed_securities():
    async with async_session() as session:
        existing = await session.execute(select(Security))
        if existing.scalars().first():
            return

    data = await fetch_all_securities()
    seen = set()
    async with async_session() as session:
        for item in data:
            sym = str(item.get("symbol", "")).strip().upper()
            name = str(item.get("companyName", item.get("name", ""))).strip()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            session.add(Security(symbol=sym, name=name))
        await session.commit()


async def backfill_prices():
    async with async_session() as s:
        existing = await s.execute(select(DailyPrice).limit(1))
        if existing.scalars().first():
            return

    data = await fetch_all_securities()
    symbols = sorted(set(
        str(item.get("symbol", "")).strip().upper()
        for item in data if item.get("symbol")
    ))

    async with httpx.AsyncClient(timeout=20) as client:
        async with async_session() as session:
            for sym in symbols:
                try:
                    url = f"{NEPSEMAN_BASE}/api/v1/securities/{sym}/history"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    result = resp.json()
                    prices = result.get("data", result)
                    if not isinstance(prices, list) or len(prices) < 5:
                        continue

                    prices.reverse()
                    prev_close = None
                    for p in prices:
                        d = datetime.strptime(p["businessDate"], "%Y-%m-%d").date()
                        close = float(p.get("closePrice", 0))
                        high = float(p.get("highPrice", close))
                        low = float(p.get("lowPrice", close))
                        vol = int(p.get("totalTradedQuantity", 0))
                        turnover = float(p.get("totalTradedValue", 0))
                        trade_open = prev_close if prev_close else close
                        prev_close = close

                        session.add(DailyPrice(
                            symbol=sym,
                            date=d,
                            open=trade_open,
                            high=high,
                            low=low,
                            close=close,
                            volume=vol,
                            turnover=turnover,
                        ))
                except Exception:
                    continue
            await session.commit()


async def seed():
    await init_db()
    print("Seeding securities...")
    await seed_securities()
    print("Backfilling historical prices (50 stocks, ~1 year each)...")
    await backfill_prices()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
