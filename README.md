# NEPSE Hermes Trader

A real-time NEPSE stock analysis platform with technical indicators, portfolio tracking, and LLM-powered chat assistant.

## Features

- **Live Market Data** — Real-time prices, indices, gainers/losers from yonepse and Merolagani
- **Technical Analysis** — RSI, MACD, SMA, ADX, Bollinger Bands with auto-generated BUY/SELL/HOLD signals
- **Portfolio Tracker** — Add/manage holdings with live P&L calculation
- **Stock Comparison** — Compare 2 stocks side-by-side with indicators
- **Backtesting** — SMA crossover strategy backtester with equity curves
- **IPO Database** — Paginated IPO listings from nepalipaisa with BS/AD dates
- **LLM Chat** — Streaming AI assistant using OpenRouter (primary) or local Ollama (fallback)
- **Fuzzy Search** — Smart search with time-aware queries ("NABIL last 3 months")

## Architecture

```
nepse-hermes-trader/
├── backend/                  # FastAPI (Python)
│   ├── main.py               # 27+ API routes, SSE streaming
│   ├── config.py             # Environment config
│   ├── database.py           # SQLite + SQLAlchemy async
│   ├── models.py             # ORM models
│   ├── data/
│   │   ├── fetcher.py        # yonepse data fetchers (live, summary, indices, top, IPO)
│   │   ├── nepalstock_fetcher.py    # NepalStock API with CSS descrambling
│   │   ├── merolagani_fetcher.py    # Merolagani scraping
│   │   ├── nepalipaisa_fetcher.py   # nepalipaisa IPO API
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
pip install -r requirements.txt
python main.py
```

Server starts on `http://localhost:8001`. API docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dev server on `http://localhost:5173`. Proxies `/api` to `localhost:8001`.

### LLM Chat Setup

1. **Ollama (free, default):** Install Ollama, pull Hermes 3:
   ```bash
   ollama pull hermes3
   ```

2. **OpenRouter (optional, recommended):**
   ```bash
   export OPENROUTER_KEY="sk-or-..."
   export OPENROUTER_MODEL="nousresearch/hermes-3-llama-3.1-8b"
   ```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/market/live` | Live prices, indices, gainers/losers |
| GET | `/api/market/overview` | Market overview with summary |
| GET | `/api/market/status` | Market open/closed status |
| GET | `/api/market/index-history` | NEPSE index chart data |
| GET | `/api/companies` | All listed companies with prices |
| GET | `/api/securities` | Securities list with search |
| GET | `/api/search` | Fuzzy symbol search |
| GET | `/api/stocks/{symbol}/history` | Price history + indicators |
| GET | `/api/stocks/{symbol}/detail` | Company detail |
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

| Source | Type | Reliability |
|--------|------|-------------|
| [yonepse](https://shubhamnpk.github.io/yonepse) | JSON API | Primary (live prices, summary, indices) |
| [NepalStock](https://www.nepalstock.com.np) | REST API + CSS descrambling | Fallback (live prices, market status) |
| [Merolagani](https://merolagani.com) | HTML scraping | Fallback (live prices, summary, company detail) |
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
| `OLLAMA_MODEL` | `hermes3` | Ollama model name |
| `OPENROUTER_KEY` | `""` | OpenRouter API key |
| `OPENROUTER_MODEL` | `nousresearch/hermes-3-llama-3.1-8b` | OpenRouter model |

## License

MIT
