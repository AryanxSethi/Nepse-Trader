# NEPSE Hermes Trader — Agent Context

## Goal
Local PoC agentic trading web app for NEPSE (Nepal Stock Exchange) with Hermes 3 self-learning agent, clean UI, honest AI, fuzzy search, and sourced guide content.

## Architecture
- **Backend**: Python FastAPI + SQLite (SQLAlchemy async) on port **8001**
- **Frontend**: React + TypeScript + Vite + Tailwind v4 on port **5173**
- **AI**: Ollama with `hermes3:latest` model
- **Data**: yonepse (`shubhamnpk.github.io/yonepse`) for live data, nepseman-api for historical

## Key Fixes Applied

### Session 2
1. yonepse API key mapping (top_gainer, top_loser, top_turnover, indices)
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
Invoke-WebRequest http://localhost:5173/api/health

# Search with live prices
Invoke-WebRequest "http://localhost:5173/api/search?query=NABIL"

# All 376 companies
Invoke-WebRequest http://localhost:5173/api/companies

# Stock history (current data)
Invoke-WebRequest "http://localhost:5173/api/stocks/NABIL/history?start=2026-06-01&end=2026-07-02"

# Compare (120 prices per stock, up to July 1)
Invoke-WebRequest "http://localhost:5173/api/stocks/compare?symbols=NABIL,SCB"

# Market overview (indices, gainers, losers, active)
Invoke-WebRequest http://localhost:5173/api/market/overview

# All signals
Invoke-WebRequest http://localhost:5173/api/signals

# Guide search (curated + LLM fallback)
Invoke-WebRequest "http://localhost:5173/api/guide/search?q=how+to+start+trading"

# AI chat
Invoke-WebRequest -Method POST http://localhost:5173/api/ask -Body '{"question":"What is RSI?"}' -ContentType "application/json"
```

## Data Stats (as of 2026-07-02)
- DB: `data/nepse.db` (NOT `backend/data/nepse.db` — the latter is empty)
- Securities: 376 (in DB + live yonepse)
- DailyPrices: ~83k rows across 376 stocks (up to 2026-07-01)
- Signals: ~350 (generated via technical analysis)
- Compare endpoint: 120 prices per stock (was 60, stuck at April)
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
