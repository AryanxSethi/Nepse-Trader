"""Backtest route — SMA crossover strategy backtesting."""

from fastapi import APIRouter, HTTPException

from app.analysis.backtest import run_backtest

router = APIRouter()


def validate_params(symbol: str, fast_ma: int, slow_ma: int, days: int) -> None:
    """Reject invalid backtest parameters with a 400 instead of a downstream crash."""
    if not symbol or len(symbol) > 30:
        raise HTTPException(status_code=400, detail="Invalid symbol")
    if not (2 <= fast_ma <= 250):
        raise HTTPException(status_code=400, detail="fast_ma must be between 2 and 250")
    if not (2 <= slow_ma <= 250):
        raise HTTPException(status_code=400, detail="slow_ma must be between 2 and 250")
    if fast_ma >= slow_ma:
        raise HTTPException(status_code=400, detail="fast_ma must be less than slow_ma")
    if not (30 <= days <= 5000):
        raise HTTPException(status_code=400, detail="days must be between 30 and 5000")


@router.post("/api/backtest")
async def backtest(symbol: str = "NABIL", fast_ma: int = 20, slow_ma: int = 50, days: int = 365) -> dict:
    """POST /api/backtest — run a moving-average crossover backtest for a given symbol and parameters.

    Args:
        symbol: Stock symbol to backtest (default: NABIL).
        fast_ma: Fast moving average period (default: 20).
        slow_ma: Slow moving average period (default: 50).
        days: Number of days of historical data to use (default: 365).

    Returns:
        Backtest results including trades, win rate, and total return.
    """
    validate_params(symbol, fast_ma, slow_ma, days)
    result = await run_backtest(symbol, fast_ma, slow_ma, days)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result