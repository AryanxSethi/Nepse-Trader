"""Strategy backtesting engine with NEPSE-specific transaction costs.

Supports SMA crossover strategies and returns performance metrics including
Sharpe ratio, max drawdown, and win rate.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.session import async_session
from app.db.models import DailyPrice

# NEPSE trading costs (percentage)
BROKER_COMMISSION_RATE = 0.004  # 0.4%
SEBON_FEE_RATE = 0.00015       # 0.015%
STT_RATE = 0.001               # 0.1% (on sell only)


async def run_backtest(symbol: str, fast_ma: int = 20, slow_ma: int = 50, days: int = 365):
    """Run a SMA crossover backtest for *symbol* with NEPSE transaction costs.

    Returns a dict with return metrics, trade stats, and an equity curve.
    """
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)

    async with async_session() as session:
        rows = await session.execute(
            select(DailyPrice)
            .where(DailyPrice.symbol == symbol, DailyPrice.date >= cutoff)
            .order_by(DailyPrice.date)
            .limit(days)
        )
        records = [r.to_dict() for r in rows.scalars().all()]

    if len(records) < slow_ma + 10:
        return {"error": f"Not enough data for {symbol}"}

    df = pd.DataFrame(records)
    df["sma_fast"] = df["close"].rolling(window=fast_ma).mean()
    df["sma_slow"] = df["close"].rolling(window=slow_ma).mean()
    df["signal"] = 0
    df.loc[df["sma_fast"] > df["sma_slow"], "signal"] = 1
    df["position"] = df["signal"].diff()
    if df["signal"].iloc[0] == 1:
        df.loc[df.index[0], "position"] = 1

    balance = 100000
    shares = 0
    trades = 0
    wins = 0
    peak = balance
    drawdowns = []
    portfolio_values = []
    total_costs = 0

    for i, row in df.iterrows():
        if row["position"] == 1 and balance > 0:
            cost = row["close"]
            commission = cost * BROKER_COMMISSION_RATE
            sebon = cost * SEBON_FEE_RATE
            total_fees = commission + sebon
            total_costs += total_fees * (balance // row["close"])
            shares = int(balance // (cost + total_fees))
            balance -= shares * (cost + total_fees)
            trades += 1
        elif row["position"] == -1 and shares > 0:
            proceeds = shares * row["close"]
            commission = proceeds * BROKER_COMMISSION_RATE
            sebon = proceeds * SEBON_FEE_RATE
            stt = proceeds * STT_RATE
            total_fees = commission + sebon + stt
            total_costs += total_fees
            balance = proceeds - total_fees
            shares = 0
            if balance > 100000:
                wins += 1

        portfolio = balance + shares * row["close"]
        portfolio_values.append(portfolio)
        peak = max(peak, portfolio)
        dd = (peak - portfolio) / peak * 100
        drawdowns.append(dd)

    final_value = balance + shares * df["close"].iloc[-1]
    total_return = (final_value - 100000) / 100000 * 100
    buy_hold_return = (df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0] * 100

    strat_returns = pd.Series(portfolio_values).pct_change().dropna()
    sharpe = float(np.sqrt(252) * strat_returns.mean() / strat_returns.std()) if strat_returns.std() > 0 else 0
    max_dd = max(drawdowns) if drawdowns else 0
    win_rate = (wins / trades * 100) if trades > 0 else 0

    return {
        "symbol": symbol,
        "strategy": f"MA crossover ({fast_ma}/{slow_ma})",
        "total_return": round(total_return, 2),
        "buy_hold_return": round(buy_hold_return, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "win_rate": round(win_rate, 1),
        "total_trades": trades,
        "total_costs": round(total_costs, 2),
        "equity_curve": [
            {"date": r["date"], "value": round(portfolio_values[i], 2)}
            for i, r in enumerate(records)
        ][::max(1, len(records) // 100)],
    }
