import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from database import async_session
from models import DailyPrice


async def run_backtest(symbol: str, fast_ma: int = 20, slow_ma: int = 50, days: int = 365):
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)

    async with async_session() as session:
        rows = await session.execute(
            select(DailyPrice)
            .where(DailyPrice.symbol == symbol, DailyPrice.date >= cutoff)
            .order_by(DailyPrice.date)
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
    # Enter position on first signal day
    if df["signal"].iloc[0] == 1:
        df["position"].iloc[0] = 1

    balance = 100000
    shares = 0
    trades = 0
    wins = 0
    peak = balance
    drawdowns = []
    portfolio_values = []

    for i, row in df.iterrows():
        if row["position"] == 1 and balance > 0:
            shares = int(balance // row["close"])
            balance -= shares * row["close"]
            trades += 1
        elif row["position"] == -1 and shares > 0:
            balance = shares * row["close"]
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
        "equity_curve": [
            {"date": r["date"], "value": round(portfolio_values[i], 2)}
            for i, r in enumerate(records)
        ][::max(1, len(records) // 100)],
    }
