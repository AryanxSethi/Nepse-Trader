# NEPSE Trader — Agent Context

## Goal
Local PoC agentic trading web app for NEPSE (Nepal Stock Exchange) with AI assistant, clean UI, honest AI, fuzzy search, and sourced guide content.

## Architecture
- **Backend**: Python FastAPI + SQLite (SQLAlchemy async) on port **8001**
- **Frontend**: React + TypeScript + Vite + Tailwind v4 on port **5173**
- **AI**: Ollama with `qwen2.5:7b-instruct-q4_k_m`
- **Primary Data**: yonepse (GitHub JSON CDN — live prices, summary, indices, brokers, status)
- **Secondary Data**: Merolagani (scraped — company detail, SignalR index streaming, index history)
- **Tertiary Data**: Sharesansar (scraped — VWAP, pivots, MA signals, volume, all-indices)

## Important Build Note
- `npx tsc --noEmit` passes but **`npm run build`** (which runs `tsc -b`) is stricter — catches `erasableSyntaxOnly` violations, template literal type mismatches, and null-safety issues that `--noEmit` misses
- Always run `npm run build` before committing to ensure production-ready code

## Recent Changes (Session 2026-07-05)

### Chatbot Friendliness
- Added `TONE & CONVERSATION` section to `GUIDE_SYSTEM_PROMPT` — handles greetings, thank you, please, elaboration requests with warm follow-up
- Rich data context: build_data_context now includes prev_close, day range, turnover, trades, market_cap, and market snapshot (all 4 indices)

### Portfolio Improvements
- `SymbolSearchInput` component — autocomplete with debounced search (same pattern as SearchBar)
- Date picker (`input type="date"`) added to AddHoldingModal with default today
- Fixed `fetchPortfolio` return type — was `Promise<PortfolioHolding[]>` but backend returns `{holdings, total_invested, ...}` causing runtime crash
- Backend portfolio endpoint computes totals; frontend destructures response directly

### Search Fixes
- Fixed `fetchSearch` return type — was `Promise<SearchSuggestion[]>` (bare array) but backend returns `{suggestions: [...], symbol, start, end}` — broke all autocomplete and NLP symbol detection
- `SearchBar` and `SymbolSearchInput` now receive correct response shape

### Codebase Audit Fixes (HIGH priority)
1. **NameError on startup** — `set_security_cache` moved inside try block with empty fallback
2. **SQLite Windows path** — `DB_PATH.as_posix()` fixes backslash in connection URL
3. **Event loop blocking** — `threading.Lock` → `asyncio.Lock` everywhere in cache.py; disk I/O offloaded via `asyncio.to_thread`; 6 caller sites updated with `await`
4. **N+1 sessions in signals.py** — `generate_signals()` uses one session instead of 3 per security (400+ → 1 connection)
5. **0.00% data loss** — `is not None` checks replace `or` falsy chain in `_enrich_item`
6. **KeyError crash** — `'symbol' in p` guard before dict comprehension
7. **Missing error context** — exception logged with `%s` in index poll handler

### Codebase Audit Fixes (MEDIUM priority)
8. **useStockData.ts** — migrated all 4 hooks from raw `fetch('/api/...')` to `endpoints.ts` functions (gains timeout, error classification, centralized URLs)
9. **cache.py** — `load_live_cache` simplified (disk reads removed, returns `{}`)

### TypeScript Build Fixes
- Fixed `tsc -b` build errors across 12 files:
  1. `client.ts` — `erasableSyntaxOnly`: changed public parameter properties to class properties
  2. `Skeleton.tsx` — added explicit `string | number` union type for `width` prop
  3. `StockChart.tsx` — `any[]` → safe cast for candle data
  4. `endpoints.ts` — `fetchCompare` accepts optional `opts` for abort signal
  5. `Brokers.tsx` — removed incorrect `BrokerDetail` type annotation on `.map()` callback
  6. `Guide.tsx` — aligned response destructuring with actual API shape (`entries` → `entry`)
  7. `Home.tsx` — optional chaining for `percent_change`, `sectors`, `_fetched_at`
  8. `IPOSection.tsx` — cast API response to expected types; removed orphaned abort arg
  9. `LiveMarket.tsx` — relaxed interfaces to match nullable API fields; extracted `formatTurnover`
  10. `Trade.tsx` — switched `data?.prices?.length` to `data?.prices && data.prices.length` for proper narrowing
- Build now passes with `npm run build` (0 errors)

### Response Formatting
- All LLM responses must follow STRICT FORMAT RULES: compact lines, bold section headers, max 12 lines, disclaimer on own line
- Stock data uses single-line format: `**NABIL** | NPR 485.20 | +2.15% | Vol: 52,341`
- Technical indicators: one bullet per indicator with brief interpretation

## Test Commands
```powershell
# Health
Invoke-WebRequest http://127.0.0.1:8001/api/health

# Search
Invoke-WebRequest "http://127.0.0.1:8001/api/search?query=NABIL"

# Stock detail
Invoke-WebRequest "http://127.0.0.1:8001/api/stocks/NABIL/detail"

# Compare
Invoke-WebRequest "http://127.0.0.1:8001/api/stocks/compare?symbols=NABIL,SCB"

# Market overview
Invoke-WebRequest http://127.0.0.1:8001/api/market/overview

# Portfolio
Invoke-WebRequest http://127.0.0.1:8001/api/portfolio

# AI chat
Invoke-WebRequest -Method POST http://127.0.0.1:8001/api/ask -Body '{"question":"hello"}' -ContentType "application/json"

# Signals
Invoke-WebRequest http://127.0.0.1:8001/api/signals

# Guide search
Invoke-WebRequest "http://127.0.0.1:8001/api/guide/search?q=how+to+start+trading"
```

## Running Services (as of 2026-07-05)
- Backend (port 8001): uvicorn main:app
- Frontend (port 5173): Vite dev server
- Ollama (port 11434): `qwen2.5:7b-instruct-q4_k_m` (4.68 GB, Q4_K_M quant)

## Data Stats (as of 2026-07-05)
- DB: `backend/data/nepse.db` (resolved via `backend/app/core/config.py:DATA_DIR`)
- Securities: 376
- DailyPrices: ~83k rows
- Signals: ~350 (generated via technical analysis)
- Portfolio: user-specific (SQLite)
- LLM model: qwen2.5:7b-instruct-q4_k_m

## Recent Changes (Session 2026-07-07)

### Chart Fix: Sensitive Index = 0 & Flat Lines
- **Root cause (Sensitive = 0)**: yonepse warmup was gated by `if not LIVE_CACHE.get('current_indices')` — if disk cache already had a partial `current_indices` (NEPSE only), Sensitive Index was never seeded
- **Fix**: Always fetch yonepse indices on startup and merge into existing `current_indices` — missing sub-indices (Sensitive, Float, etc.) are added without overwriting live values
- **Root cause (flat lines)**: Both line series shared one price scale. NEPSE (~2000) and Sensitive (~350) have vastly different magnitudes, so micro-changes were invisible
- **Fix**: NEPSE uses `priceScaleId: 'right'`, Sensitive uses `priceScaleId: 'left'` with `scaleMargins: { top: 0.5, bottom: 0.05 }` — each series auto-scales independently
- **Also fixed**: Merolagani `get_live_index()` keys now normalized via `_normalize_index_name()` (same as Sharesansar path) so live values update correct index keys
- **Also fixed**: Empty-today fallback — changed `json.today ?? json.snapshots` to `json.today?.length ? json.today : json.snapshots` so `[]` properly falls through

### Full Docstring Pass (204 entities)
- **Backend**: Google-style docstrings (Args/Returns) added to all 108 undocumented functions/methods across `main.py` (47), `data/merolagani_fetcher.py` (15), `data/import_nepse_data.py` (6), `data/assets/css_wasm_funcs.py` (7), `data/fetcher_sectors.py` (3), `guide/broker_directory.py` (3), `guide/knowledge_base.py` (2), `analysis/indicators.py` (1), `models.py` (2)
- **Frontend**: JSDoc added to all 96 undocumented exports across `api/` (30), `hooks/` (8), `utils/` (4), `components/` (40), `pages/` (10), `context/` (2), `App.tsx` (1), `IndexChart.tsx` (1)
- Verifed: `python -m py_compile` on all backend files, `npx tsc -b --noEmit`, `npx oxlint` — all pass

### Other Fixes
- **Frontend**: `today` field in `fetchIndexHistory` response now handles empty arrays properly (fallback to `snapshots`)
- **Frontend**: Chart no longer shows both series on same price axis — independent left/right scales with proper `scaleMargins`

## Important Known Issues
- Port 8000 stuck in Windows TCP TIME_WAIT — use 8001
- `fetch_all_securities()` includes 376 companies; some are bonds/debentures
- Backend `--reload` flaky on Windows — kill and restart fully if changes not picked up
- `.env` file exists but `load_dotenv()` is never called — custom `OLLAMA_URL` is silently ignored
- SQLite URL uses `Path.__str__()` which on Windows produces backslashes — fixed via `asyncio.to_thread`

## Virtual Environment
- Backend runs in `backend/venv/` (Python 3.13.14)
- Activate: `backend\venv\Scripts\Activate.ps1`
- Install/update: `pip install -r backend\requirements.txt`
- Start via: `venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8001`
- `.gitignore` includes `backend/venv/`

## Quick Restart
```powershell
# Kill old
Get-Process -Name python* | Where-Object { $_.CommandLine -match "uvicorn" } | Stop-Process -Force
Get-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess | Stop-Process -Force

# Start backend (venv)
Start-Process -WindowStyle Hidden -FilePath "venv\Scripts\python" -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8001" -WorkingDirectory "backend"

# Start frontend
Set-Location frontend; npm run dev
```
