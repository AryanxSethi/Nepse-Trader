"""Stock routes — history, detail, compare."""

import asyncio
import logging
from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.analysis.indicators import compute_indicators, compute_signal
from app.db.models import DailyPrice, Security
from app.db.session import async_session
from app.providers.sectors import get_sector_for_symbol
from app.services.live import _fetch_live_all
from app.services.scheduler import get_market_status
from app.services.state import merolagani_fetcher, sharesansar_fetcher
from app.services.stocks import _fetch_yonepse_history, _get_live_candle

router = APIRouter()
logger = logging.getLogger('routers.stocks')


@router.get("/api/stocks/{symbol}/history")
async def stock_history(symbol: str, start: str = "", end: str = "") -> dict:
    """GET /api/stocks/{symbol}/history — return daily price history with technical indicators and signal."""
    sym = symbol.upper()
    if not sym or len(sym) > 30:
        raise HTTPException(status_code=400, detail="Invalid symbol")
    today = date.today()
    try:
        start_date = date.fromisoformat(start) if start else today - timedelta(days=90)
        end_date = date.fromisoformat(end) if end else today
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start must be before or equal to end")

    async with async_session() as session:
        rows = await session.execute(
            select(DailyPrice)
            .where(DailyPrice.symbol == sym, DailyPrice.date >= start_date, DailyPrice.date <= end_date)
            .order_by(DailyPrice.date)
            .limit(1000)
        )
        records = [r.to_dict() for r in rows.scalars().all()]

    if not records:
        return {"prices": [], "indicators": {}, "signal": None}

    try:
        market_status = get_market_status()
        today_candle = await _get_live_candle(sym)
        if today_candle and market_status.get('is_open'):
            if records and records[-1].get("date") == today.isoformat():
                records[-1] = today_candle
            else:
                records.append(today_candle)

        df = pd.DataFrame(records)
        indicators = compute_indicators(df)
        sig_type, confidence, reason = compute_signal(indicators)
    except Exception as e:
        logger.warning("Indicator computation failed for %s: %s", sym, e)
        return {"prices": records, "indicators": {}, "signal": {"type": "HOLD", "confidence": 50, "reason": "Insufficient data for technical analysis"}}

    return {
        "prices": records,
        "indicators": {k: v for k, v in indicators.items() if v is not None},
        "signal": {"type": sig_type, "confidence": confidence, "reason": reason},
    }


@router.get("/api/stocks/{symbol}/detail")
async def stock_detail(symbol: str) -> dict:
    """GET /api/stocks/{symbol}/detail — return company detail with Sharesansar enrichment (pivot, moving averages, 52W range)."""
    if not symbol or len(symbol) > 30:
        raise HTTPException(status_code=400, detail="Invalid symbol")
    detail = await merolagani_fetcher.get_company_detail(symbol)
    if not detail:
        detail = {}

    try:
        ss_price, ss_detail = await asyncio.gather(
            sharesansar_fetcher.get_today_share_price_for_symbol(symbol),
            sharesansar_fetcher.get_company_detail(symbol),
            return_exceptions=True,
        )
        ss_price_data = {} if isinstance(ss_price, Exception) else (ss_price or {})
        ss_detail_data = {} if isinstance(ss_detail, Exception) else (ss_detail or {})
    except Exception as e:
        logger.warning("Sharesansar detail fetch failed for %s: %s", symbol, e)
        ss_price_data = {}
        ss_detail_data = {}

    if ss_price_data.get('vwap') is not None:
        detail['vwap'] = str(ss_price_data['vwap'])
    if ss_price_data.get('prev_close') is not None:
        detail['prev_close'] = str(ss_price_data['prev_close'])
    if ss_price_data.get('volume') is not None:
        detail['volume'] = str(int(ss_price_data['volume']))
    if ss_price_data.get('avg_180d') is not None:
        detail['180d_avg'] = str(ss_price_data['avg_180d'])
    if ss_price_data.get('avg_120d') is not None:
        if not detail.get('120d_avg'):
            detail['120d_avg'] = str(ss_price_data['avg_120d'])
    if ss_price_data.get('confidence_score') is not None:
        detail['confidence_score'] = ss_price_data['confidence_score']
    if ss_price_data.get('high_52w') is not None:
        if not detail.get('52w_high'):
            detail['52w_high'] = str(ss_price_data['high_52w'])
    if ss_price_data.get('low_52w') is not None:
        if not detail.get('52w_low'):
            detail['52w_low'] = str(ss_price_data['low_52w'])

    pivot = ss_detail_data.get('pivot')
    if pivot:
        for k, v in pivot.items():
            detail[f'pivot_{k}'] = str(v)
    moving = ss_detail_data.get('moving')
    if moving:
        for period_key, period_data in moving.items():
            if isinstance(period_data, dict):
                detail[f'{period_key}_signal'] = period_data.get('signal')
                if period_data.get('value') is not None:
                    detail[f'{period_key}_value'] = str(period_data['value'])

    async with async_session() as session:
        result = await session.execute(
            select(Security).where(Security.symbol == symbol.upper())
        )
        sec = result.scalar_one_or_none()
        if sec and sec.sector and not detail.get("sector"):
            detail["sector"] = sec.sector
    if not detail.get("sector"):
        s = get_sector_for_symbol(symbol.upper())
        if s:
            detail["sector"] = s
    return detail


@router.get("/api/stocks/compare")
async def compare_stocks(symbols: str = "") -> dict:
    """GET /api/stocks/compare — compare technical indicators and prices for up to 5 symbols.

    Args:
        symbols: Comma-separated list of stock symbols.

    Returns:
        Comparison data including LTP, change, volume, price history, and indicators per symbol.
    """
    if not symbols:
        raise HTTPException(status_code=400, detail="Provide comma-separated symbols")

    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if len(sym_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 symbols")
    if len(sym_list) > 5:
        sym_list = sym_list[:5]
    if any(len(s) > 30 for s in sym_list):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    live = await _fetch_live_all()
    live_map = {c.get("symbol", "").upper(): c for c in live}

    records_by_symbol = {}
    try:
        async with async_session() as session:
            rows = await session.execute(
                select(DailyPrice)
                .where(DailyPrice.symbol.in_(sym_list))
                .order_by(DailyPrice.date)
            )
            for r in rows.scalars().all():
                records_by_symbol.setdefault(r.symbol, []).append(r.to_dict())
    except Exception as e:
        logger.warning("Failed to batch query daily prices: %s", e)

    market_status = get_market_status()

    async def _process_sym(sym: str) -> dict:
        """Fetch prices and compute indicators for a single comparison symbol."""
        l = live_map.get(sym, {})
        item = {
            "symbol": sym,
            "name": l.get("name", ""),
            "ltp": l.get("ltp"),
            "change": l.get("change"),
            "percent_change": l.get("percent_change"),
            "volume": l.get("volume"),
            "turnover": l.get("turnover"),
            "market_cap": l.get("market_cap"),
        }
        try:
            records = records_by_symbol.get(sym, [])
            if len(records) < 2:
                records = await _fetch_yonepse_history(sym, 60)
            if market_status.get('is_open'):
                today_candle = await _get_live_candle(sym)
                if today_candle and (not records or records[-1].get("date") != date.today().isoformat()):
                    records.append(today_candle)
            if len(records) >= 2:
                records.sort(key=lambda r: r.get("date", ""))
                item["prices"] = records
            if len(records) >= 20:
                df = pd.DataFrame(records)
                indicators = compute_indicators(df)
                sig_type, confidence, reason = compute_signal(indicators)
                item["rsi"] = indicators.get("rsi")
                item["macd"] = indicators.get("macd")
                item["macd_signal"] = indicators.get("macd_signal")
                item["sma20"] = indicators.get("sma20")
                item["sma50"] = indicators.get("sma50")
                item["adx"] = indicators.get("adx")
                item["trend"] = indicators.get("trend")
                item["signal_type"] = sig_type
                item["signal_confidence"] = confidence
        except Exception as e:
            logger.warning("Failed to compute indicators for %s: %s", sym, e)
        return item

    result = await asyncio.gather(*[_process_sym(sym) for sym in sym_list])
    return {"symbols": sym_list, "comparison": result}