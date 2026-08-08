# NEPSE Trader

A real-time NEPSE stock analysis platform with technical indicators, portfolio tracking, and LLM-powered chat assistant.

## Features

- **Live Market Data** — Real-time prices, 17 indices, gainers/losers from yonepse and Merolagani
- **Technical Analysis** — RSI, MACD, SMA, ADX, VWAP, pivot levels with auto-generated BUY/SELL/HOLD signals
- **Portfolio Tracker** — Add/manage holdings with live P&L calculation
- **Stock Comparison** — Compare 2 stocks side-by-side with indicators and AI signals
- **Backtesting** — SMA crossover strategy backtester with equity curves
- **IPO Database** — Paginated IPO listings from nepalipaisa with BS/AD dates
- **LLM Chat** — Streaming AI assistant powered by local Ollama
- **Fuzzy Search** — Smart search with time-aware queries ("NABIL last 3 months")

## Architecture

```
nepse-trader/
├── backend/                  # FastAPI (Python)
│   ├── main.py               # 27+ API routes, SSE streaming
│   ├── config.py             # Environment config
│   ├── database.py           # SQLite + SQLAlchemy async
│   ├── models.py             # ORM models
│   ├── data/
│   │   ├── fetcher.py        # yonepse data fetchers (live, summary, indices, top, IPO)
│   │   ├── sharesansar_fetcher.py  # Sharesansar scraping (VWAP, pivots)
│   │   ├── merolagani_fetcher.py    # Merolagani scraping (prices, company details)
│   │   ├── nepalipaisa_fetcher.py   # nepalipaisa IPO API
│   │   ├── broker_fetcher.py        # Broker directory fetcher
│   │   ├── _http.py          # HTTP retry utility + circuit breaker
│   │   ├── cache.py          # TTLCache wrapper with disk persistence
│   │   ├── market_scheduler.py      # Background data refresh scheduler
│   │   ├── updater.py        # Daily price DB updates
│   │   ├── seeder.py         # Securities table seeder
│   │   └── ...
│   ├── analysis/
│   │   ├── indicators.py     # Technical indicator computation
│   │   ├── signals.py        # Signal generation logic
│   │   └── backtest.py       # SMA crossover backtester
│   ├── search/
│   │   └── fuzzy.py          # Fuzzy stock search + time parsing
│   └── guide/
│       ├── knowledge_base.py # Trading guide KB
│       └── broker_directory.py  # Broker directory
├── frontend/                 # React + Vite + TypeScript
│   └── src/
│       ├── components/       # Reusable UI components
│       ├── pages/            # Page components (routing)
│       ├── hooks/            # React Query hooks + custom hooks
│       └── utils/            # Formatting utilities
└── data/                     # Runtime data directory
    ├── cache/                # Disk-backed cache (auto-created)
    └── ipos.json             # Static IPO fallback data
```

## Quick Start

### Backend

```bash
cd backend
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Server starts on `http://127.0.0.1:8001`. API docs at `/docs`.

### One-Click (Windows)

```cmd
start-demo.bat
```
Starts backend, health-checks, then launches frontend.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dev server on `http://127.0.0.1:5173`. Proxies `/api` to `127.0.0.1:8001`.

### LLM Chat Setup

Install Ollama and pull the model:
```bash
ollama pull qwen2.5:7b-instruct-q4_k_m
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/market/live` | Live prices, indices, gainers/losers |
| GET | `/api/market/overview` | Market overview with summary |
| GET | `/api/market/status` | Market open/closed status |
| GET | `/api/market/index-history` | Index chart data (`today`=intraday, `snapshots`=60‑entry tail, `points`=blended) |
| GET | `/api/companies` | All listed companies with prices |
| GET | `/api/securities` | Securities list with search |
| GET | `/api/search` | Fuzzy symbol search |
| GET | `/api/stocks/{symbol}/history` | Price history + indicators |
| GET | `/api/stocks/{symbol}/detail` | Company detail (includes VWAP, pivots, MA signals) |
| GET | `/api/stocks/compare` | Multi-stock comparison |
| GET | `/api/signals` | BUY/SELL/HOLD signals |
| POST | `/api/signals/generate` | Trigger signal generation |
| POST | `/api/backtest` | Run SMA crossover backtest |
| GET | `/api/portfolio` | Portfolio (holdings, P&L) |
| POST | `/api/portfolio/holdings` | Add holding |
| PUT | `/api/portfolio/holdings/{id}` | Update holding |
| DELETE | `/api/portfolio/holdings/{id}` | Delete holding |
| GET | `/api/ipos` | Paginated IPO listings |
| GET | `/api/sectors` | Market sectors |
| GET | `/api/brokers/top` | Top brokers |
| GET | `/api/brokers/search` | Broker search |
| GET | `/api/guide/search` | Trading guide + LLM |
| POST | `/api/ask` | Streaming LLM chat |
| GET | `/api/health` | System health |

## Data Sources

| Source | Type | Role |
|--------|------|------|
| [yonepse](https://shubhamnpk.github.io/yonepse) | JSON API | Primary (live prices, summary, indices) |
| [Sharesansar](https://www.sharesansar.com) | HTML scraping | Secondary (VWAP, pivots, MA signals, real volume) |
| [Merolagani](https://merolagani.com) | HTML scraping | Tertiary (live prices, SignalR index streaming, 1Y yield) |
| [nepalipaisa](https://nepalipaisa.com) | REST API | Primary (IPO listings with pagination) |

## Error Handling & Reliability

- All HTTP calls use exponential backoff retry (1s, 2s, 4s, max 3 retries)
- Per-source circuit breakers (3 consecutive failures → 60s cooldown)
- In-memory TTLCache with disk persistence (survives restarts)
- Background scheduler with failure backoff (60s → 600s max)
- All data fetchers fall back to secondary sources on failure
- Structured `meta` object in API responses (`source`, `fetched_at`, `stale`, `error`)
- `Cache-Control` headers on static-like endpoints

## Configuration

Environment variables (`.env` or system):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct-q4_k_m` | Ollama model name |

## License

MIT
