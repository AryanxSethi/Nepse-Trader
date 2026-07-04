# NEPSE Hermes Trader — Agent Context

## Goal
Local PoC agentic trading web app for NEPSE (Nepal Stock Exchange) with Hermes 3 self-learning agent, clean UI, honest AI, fuzzy search, and sourced guide content.

## Architecture
- **Backend**: Python FastAPI + SQLite (SQLAlchemy async) on port **8001**
- **Frontend**: React + TypeScript + Vite + Tailwind v4 on port **5173**
- **AI**: Ollama with `hermes3:latest` model
- **Data**: yonepse (primary — live prices, summary, indices), Sharesansar (secondary — VWAP, pivots, MA signals, floorsheet, volume), Merolagani (tertiary — SignalR index streaming, 1Y yield, company details)

## Key Fixes Applied

### Session 4 (2026-07-04) — Sharesansar Integration & System Hardening
1. **Sharesansar fetcher** (`backend/data/sharesansar_fetcher.py`): Added VWAP, pivot analysis (S3-R3), moving average signals (MA5/MA20/MA180), floorsheet data, 17 indices, real volume. Circuit breaker (threshold=3, cooloff=60s). TTL cache: today-share-price 120s, indices 300s.
2. **Backend `/api/stocks/{symbol}/detail`** extended with VWAP, prev_close, volume, 180d_avg, confidence_score, pivot levels, MA signals from Sharesansar.
3. **Backend `/api/stocks/{symbol}/floorsheet`** new endpoint — transaction-level floorsheet from Sharesansar.
4. **Backend `/api/market/live`** now merges Sharesansar volume/prev_close into Merolagani prices; appends Sharesansar indices beyond SignalR coverage.
5. **NepalStock removed entirely** — 5 spots: import, global instance, ensure_css(), close(), health check removed. Was causing 401/DNS errors.
6. **2-index filter removed** — `/api/market/live` and `/api/market/overview` return all 17 indices, not just NEPSE + Sensitive.
7. **Duplicate candle fix** — live candle appended only when `market_status.is_open` (both main chart line 631 and compare endpoint line 890).
8. **N+1 query fixes** — compare_stocks and build_data_context now use single batched `SELECT ... WHERE symbol IN (...)` queries.
9. **Race condition fixes** — `asyncio.Lock` on LIVE_CACHE, `threading.Lock` on SECURITY_CACHE, `asyncio.Lock` on sharesansar global caches.
10. **LIMIT added** — signals (200), portfolio (500), stock_history (1000), floorsheet (200).
11. **Retry with exponential backoff** — merolagani_fetcher and sharesansar_fetcher: _fetch_with_retry (1s, 2s, 4s delays, max 3 retries, 5xx/connection only).
12. **DB schema** — DailyPrice: composite index `(symbol, date)` + `UniqueConstraint`.
13. **engine.dispose()** on shutdown.
14. **try/except** on signal generation and Sharesansar detail fetch to prevent 500s.
15. **Frontend AbortControllers** — 8 fetch locations (FloorsheetPanel, CompanyInfo, Trade, Guide, useMarketStatus, Portfolio, Brokers) with 5-10s timeouts.
16. **Skeleton components** — SkeletonTable, SkeletonCompanyInfo, SkeletonChart, SkeletonIndicesCarousel.
17. **Remove NepalStock noise** — all console errors and failed fetches eliminated.
18. **Disclaimers added** — Highly visible yellow warning banners on Signals page, AISuggestion, Trade confidence badge, Backtest results, ComparePanel footnote.
19. **Color fix** — Indices table uses `percent_change` (not `change`) for green/red direction.
20. **start-demo.bat** — uses `127.0.0.1` (not `localhost` — Windows IPv6 issue); port cleanup kills stale processes before starting.

### Session 3 (2026-07-02)
1. **ComparePanel**: Removed unused `useRef`/`useCallback` imports; memoized `metrics` array; simplified effect cleanup; AbortController race fix.
2. Search enrichment with live prices (ltp, percent_change)
3. Blank screen fixes (ErrorBoundary, StockChart try/catch, empty fallbacks)
4. Guide two-tier system (curated + LLM with guardrails)
5. Port 8000 → 8001 (Windows TCP TIME_WAIT)

### Session 3 (2026-07-02)
1. **ComparePanel**: Removed unused `useRef`/`useCallback` imports; memoized `metrics` array; simplified effect cleanup (no double clearTimeout); fixed race condition with AbortController
2. **QuestionInput**: Removed unused `AskResponse` type and `WarningIcon` import
3. **SearchBar**: Selected symbol stays in input, dropdown closes on Enter/click (from previous session)
4. **Backend `get_signals`**: Renamed param `type` → `signal_type` (shadowed Python built-in)
5. **Backend unused imports**: Removed `traceback`, `is_market_open`, `fetch_live_prices`, `fetch_market_summary`, `get_sector_for_symbol` from `main.py`; `Security`/`compute_indicators`/`compute_signal` from `updater.py`; `timedelta` from `fetcher.py`; `date` from `seeder.py`; `datetime`/`date_parse` from `fuzzy.py`; `cdx` from `nepalstock_fetcher.py`
6. **Indicators.py**: Re-added `import pandas as pd` (needed for type hint `pd.DataFrame`)
7. **Trade.tsx**: Extracted `86400000` → `MS_PER_DAY` constant
8. **BrokerTable.tsx**: Removed unused `CompanyIcon` import
9. **WinnerLoserCard.tsx**: Moved `colorMap`/`headerIconMap` to module level (avoid recreation per render)
10. **SignalTable.tsx**: Changed key from `symbol-index` to just `symbol`
11. **Brokers.tsx**: Typed `any` → `BrokerDetail` for broker mapping; typed `(b as Record<string, number>)` for dynamic key access
12. **HermesSidebar.tsx**: Added `CompanyEntry` interface; removed `any` types
13. **IPOSection.tsx**: Added AbortController, user-visible `fetchError` state, `WarningIcon`
14. **Compare data staleness fixed**: Backend restart picks up `records[::-1]` (was `records[-60:][::-1]` dropping newest 60 records); compare endpoint now returns 120 prices up to July 1 (was stuck at April 2)

## Running Services (as of 2026-07-02)
- Backend (port 8001): uvicorn main:app (venv)
- Frontend (port 5173): Vite dev server
- Ollama (port 11434): hermes3 model

## Test Commands
```powershell
# Health
Invoke-WebRequest http://127.0.0.1:5173/api/health

# Search with live prices
Invoke-WebRequest "http://127.0.0.1:5173/api/search?query=NABIL"

# All 376 companies
Invoke-WebRequest http://127.0.0.1:5173/api/companies

# Stock history (current data)
Invoke-WebRequest "http://127.0.0.1:5173/api/stocks/NABIL/history?start=2026-06-01&end=2026-07-02"

# Stock detail with Sharesansar data (VWAP, pivots, MA signals)
Invoke-WebRequest "http://127.0.0.1:5173/api/stocks/NABIL/detail"

# Floorsheet (transaction-level trade history)
Invoke-WebRequest "http://127.0.0.1:5173/api/stocks/NABIL/floorsheet"

# Compare (120 prices per stock)
Invoke-WebRequest "http://127.0.0.1:5173/api/stocks/compare?symbols=NABIL,SCB"

# Market overview (all 17 indices, gainers, losers, active)
Invoke-WebRequest http://127.0.0.1:5173/api/market/overview

# All signals
Invoke-WebRequest http://127.0.0.1:5173/api/signals

# Guide search (curated + LLM fallback)
Invoke-WebRequest "http://127.0.0.1:5173/api/guide/search?q=how+to+start+trading"

# AI chat
Invoke-WebRequest -Method POST http://127.0.0.1:5173/api/ask -Body '{"question":"What is RSI?"}' -ContentType "application/json"
```

## Data Stats (as of 2026-07-04)
- DB: `data/nepse.db` (NOT `backend/data/nepse.db` — the latter is empty)
- Securities: 376 (in DB + live yonepse)
- DailyPrices: ~83k rows across 376 stocks (up to 2026-07-01)
- Signals: ~350 (generated via technical analysis)
- Compare endpoint: 120 prices per stock, batched query
- Sharesansar: 17 indices, ~200 stocks with VWAP/pivot/MA data
- Backend on port 8001: fresh restart (cleared pycache)

## Important Known Issues
- Port 8000 stuck in Windows TCP TIME_WAIT — don't use, use 8001
- `fetch_all_securities()` (nepse_data.json) includes 376 companies; some are bonds/debentures
- Backend `--reload` flaky on Windows — kill and restart fully if changes not picked up
- Two DB files exist: `data/nepse.db` (real data) and `backend/data/nepse.db` (empty). `config.py` points to `data/nepse.db`

## Quick Restart
```powershell
# Kill old
Get-Process -Name python* | Where-Object { $_.CommandLine -match "uvicorn" } | Stop-Process -Force
Get-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess | Stop-Process -Force

# Start backend
Start-Process -WindowStyle Hidden -FilePath "venv/Scripts/python.exe" -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8001" -WorkingDirectory "backend"

# Start frontend
Start-Process -WindowStyle Hidden -FilePath "frontend/node_modules/.bin/vite.cmd" -ArgumentList "--host" -WorkingDirectory "frontend"
```
