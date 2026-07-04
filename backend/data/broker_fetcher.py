import logging

from data._http import (
    CircuitBreaker,
    FetchResult,
    retry_get_json,
)

logger = logging.getLogger('broker_fetcher')

YONEPSE_BASE = "https://shubhamnpk.github.io/yonepse"
circuit_breaker = CircuitBreaker(threshold=3, cooloff=60.0)


async def _fetch_json(path: str, source: str) -> FetchResult:
    url = f"{YONEPSE_BASE}{path}"
    if circuit_breaker.is_open(source):
        logger.warning('[%s] circuit open, skipping', source)
        return FetchResult(ok=False, source=source, error='circuit open')
    result = await retry_get_json(url, source=source)
    if result.ok:
        circuit_breaker.record_success(source)
    else:
        circuit_breaker.record_failure(source)
    return result


async def fetch_brokers() -> list[dict]:
    result = await _fetch_json("/data/other/brokers.json", "yonepse/brokers")
    if result.ok and isinstance(result.data, list):
        return result.data
    logger.warning('fetch_brokers: %s', result.error or 'non-list response')
    return []


def transform_broker(raw: dict) -> dict:
    today = raw.get("todayStats") or {}
    rating = raw.get("rating") or {}
    return {
        "code": str(raw.get("memberCode", "")),
        "name": raw.get("memberName", ""),
        "phone": raw.get("phone", ""),
        "districts": raw.get("districts", []),
        "tms_link": raw.get("tmsLink", ""),
        "branch_count": raw.get("branchCount", 0),
        "active_status": raw.get("activeStatus", ""),
        "is_dealer": raw.get("isDealer", "N") == "Y",
        "avg_rating": rating.get("averageRating"),
        "total_ratings": rating.get("totalRatings", 0),
        "thirty_days_turnover": raw.get("thirtyDaysTurnover"),
        "latest_turnover": raw.get("latestTurnover"),
        "today_total_amount": today.get("totalAmount"),
        "today_buy_amount": today.get("buyAmount"),
        "today_sell_amount": today.get("sellAmount"),
        "today_buy_qty": today.get("buyQuantity"),
        "today_sell_qty": today.get("sellQuantity"),
    }
