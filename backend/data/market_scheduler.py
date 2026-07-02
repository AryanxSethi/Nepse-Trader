import asyncio
import logging
from datetime import datetime, date, time, timedelta, timezone

from data.fetcher import (
    fetch_live_prices, fetch_market_summary, fetch_top_stocks,
    fetch_indices, fetch_market_status,
)

logger = logging.getLogger("scheduler")

NPT = timezone(timedelta(hours=5, minutes=45))

NEPSE_HOLIDAYS_2026 = {
    date(2026, 1, 11), date(2026, 1, 15), date(2026, 1, 19), date(2026, 1, 30),
    date(2026, 2, 15), date(2026, 2, 18), date(2026, 2, 19),
    date(2026, 3, 2), date(2026, 3, 4), date(2026, 3, 5), date(2026, 3, 6),
    date(2026, 3, 8), date(2026, 3, 18), date(2026, 3, 27),
    date(2026, 4, 14),
    date(2026, 5, 1), date(2026, 5, 29),
    date(2026, 8, 28), date(2026, 9, 4), date(2026, 9, 18),
    date(2026, 10, 11), date(2026, 10, 18), date(2026, 10, 19), date(2026, 10, 20),
    date(2026, 11, 8), date(2026, 11, 9), date(2026, 11, 10), date(2026, 11, 15),
    date(2026, 12, 25),
}

MARKET_OPEN = time(11, 0)
MARKET_CLOSE = time(15, 0)
PRICE_REFRESH_SEC = 300
SUMMARY_REFRESH_SEC = 1800
CHECK_INTERVAL_SEC = 60


def is_market_day(today: date) -> bool:
    if today in NEPSE_HOLIDAYS_2026:
        return False
    return today.weekday() < 5


def is_market_open(now: datetime) -> bool:
    if not is_market_day(now.date()):
        return False
    market_start = datetime.combine(now.date(), MARKET_OPEN, tzinfo=NPT)
    market_end = datetime.combine(now.date(), MARKET_CLOSE, tzinfo=NPT)
    return market_start <= now < market_end


def next_market_open(from_time: datetime) -> datetime:
    today_open = datetime.combine(from_time.date(), MARKET_OPEN, tzinfo=NPT)
    if is_market_day(from_time.date()) and from_time < today_open:
        return today_open
    current = from_time
    for _ in range(14):
        current += timedelta(days=1)
        if is_market_day(current.date()):
            return datetime.combine(current.date(), MARKET_OPEN, tzinfo=NPT)
    return today_open + timedelta(days=1)


def get_market_status(now: datetime | None = None) -> dict:
    if now is None:
        now = datetime.now(NPT)
    is_open = is_market_open(now)
    next_open = next_market_open(now)
    next_close = None
    if is_open:
        next_close = datetime.combine(now.date(), MARKET_CLOSE, tzinfo=NPT)
    return {
        "is_open": is_open,
        "as_of": now.isoformat(),
        "next_open": next_open.isoformat(),
        "next_close": next_close.isoformat() if next_close else None,
    }


async def refresh_all(force_status: bool = False):
    results = await asyncio.gather(
        fetch_live_prices(),
        fetch_market_summary(),
        fetch_top_stocks(),
        fetch_indices(),
        fetch_market_status() if force_status else asyncio.sleep(0),
        return_exceptions=True,
    )
    status_ok = 0
    for r in results:
        if not isinstance(r, Exception):
            status_ok += 1
    return status_ok


class MarketScheduler:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._task: asyncio.Task | None = None
        self._last_price_refresh: datetime | None = None
        self._last_summary_refresh: datetime | None = None
        self._consecutive_failures = 0
        self._last_good_timestamps: dict[str, datetime | None] = {
            'prices': None,
            'summary': None,
            'top': None,
            'indices': None,
        }

    def start(self):
        if self._task is None or self._task.done():
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.error("Cannot start scheduler: no running event loop")
                return
            self._task = loop.create_task(self._run())

    async def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def get_backoff_seconds(self) -> int:
        if self._consecutive_failures == 0:
            return CHECK_INTERVAL_SEC
        backoff_seconds = 60 * (2 ** min(self._consecutive_failures - 1, 4))
        return min(backoff_seconds, 600)

    def get_last_good_timestamps(self) -> dict:
        return {
            k: v.isoformat() if v else None
            for k, v in self._last_good_timestamps.items()
        }

    async def _run(self):
        logger.info("Market scheduler started")
        while True:
            try:
                now = datetime.now(NPT)
                open_now = is_market_open(now)

                if open_now:
                    needs_price = (
                        self._last_price_refresh is None
                        or (now - self._last_price_refresh).total_seconds() >= PRICE_REFRESH_SEC
                    )
                    needs_summary = (
                        self._last_summary_refresh is None
                        or (now - self._last_summary_refresh).total_seconds() >= SUMMARY_REFRESH_SEC
                    )

                    if needs_price or needs_summary:
                        ok = await refresh_all(force_status=needs_summary)
                        if ok >= 3:
                            self._consecutive_failures = 0
                            now = datetime.now(NPT)
                            if needs_price:
                                self._last_price_refresh = now
                                self._last_good_timestamps['prices'] = now
                            if needs_summary:
                                self._last_summary_refresh = now
                                self._last_good_timestamps['summary'] = now
                                self._last_good_timestamps['top'] = now
                                self._last_good_timestamps['indices'] = now
                            logger.info("Refreshed %d data sources at %s NPT", ok, now.strftime('%H:%M'))
                        else:
                            self._consecutive_failures += 1
                            backoff = self.get_backoff_seconds()
                            logger.warning(
                                "Scheduler refresh partial (%d/4 ok), consecutive=%d, next check in %ds",
                                ok, self._consecutive_failures, backoff,
                            )
                            await asyncio.sleep(backoff)
                            continue
                else:
                    if self._last_price_refresh is not None or self._last_summary_refresh is not None:
                        logger.info("Market closed — pausing refreshes")
                        self._last_price_refresh = None
                        self._last_summary_refresh = None
                    self._consecutive_failures = 0

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Scheduler error: %s", e)
                self._consecutive_failures += 1

            sleep_secs = self.get_backoff_seconds() if self._consecutive_failures > 0 else CHECK_INTERVAL_SEC
            await asyncio.sleep(sleep_secs)
