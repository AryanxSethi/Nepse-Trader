"""Daily signal generation for all tracked securities.

Fetches 180 days of price data, computes indicators, and persists new
BUY/SELL/HOLD signals that differ from the latest stored signal.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, desc
from database import async_session
from models import Security, DailyPrice, Signal
from analysis.indicators import compute_indicators, compute_signal
import pandas as pd


async def generate_signals():
    """Generate signals for all securities with 30+ price records.

    Skips if today's signal matches the latest stored signal for a symbol.
    """
    now = datetime.now(timezone.utc)
    today = now.date()
    cutoff = today - timedelta(days=180)

    async with async_session() as session:
        securities = await session.execute(select(Security))
        symbols = [s.symbol for s in securities.scalars()]

        if not symbols:
            return

        all_rows = await session.execute(
            select(DailyPrice)
            .where(DailyPrice.symbol.in_(symbols), DailyPrice.date >= cutoff)
            .order_by(DailyPrice.symbol, DailyPrice.date)
        )
        all_records = all_rows.scalars().all()

        by_symbol: dict[str, list] = {}
        for r in all_records:
            by_symbol.setdefault(r.symbol, []).append(r.to_dict())

        added = False
        for sym in symbols:
            records = by_symbol.get(sym, [])
            if len(records) < 30:
                continue

            df = pd.DataFrame(records)
            indicators = compute_indicators(df)
            signal_type, confidence, reason = compute_signal(indicators)

            existing = await session.execute(
                select(Signal).where(Signal.symbol == sym).order_by(desc(Signal.generated_at))
            )
            old = existing.scalars().first()
            if old and old.signal_type == signal_type and old.generated_at.date() == today:
                continue
            session.add(Signal(
                symbol=sym,
                signal_type=signal_type,
                confidence=confidence,
                reason=reason[:500],
            ))
            added = True
        if added:
            await session.commit()
