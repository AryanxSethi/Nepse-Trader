from datetime import datetime, timedelta, timezone
from sqlalchemy import select, desc
from database import async_session
from models import Security, DailyPrice, Signal
from analysis.indicators import compute_indicators, compute_signal
import pandas as pd


async def generate_signals():
    now = datetime.now(timezone.utc)
    today = now.date()
    cutoff = today - timedelta(days=180)

    async with async_session() as session:
        securities = await session.execute(select(Security))
        symbols = [(s.symbol, s.name) for s in securities.scalars()]

        for sym, name in symbols:
            rows = await session.execute(
                select(DailyPrice)
                .where(DailyPrice.symbol == sym, DailyPrice.date >= cutoff)
                .order_by(DailyPrice.date)
            )
            records = rows.scalars().all()

            if len(records) < 30:
                continue

            df = pd.DataFrame([r.to_dict() for r in records])
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
            await session.commit()
