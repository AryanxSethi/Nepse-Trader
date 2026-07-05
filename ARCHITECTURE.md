# NEPSE Trader — System Architecture

## Overview

NEPSE Trader is a full-stack web application for analyzing the Nepal Stock Exchange (NEPSE). It aggregates real-time and historical market data from multiple sources, computes technical indicators, generates trading signals, and provides an AI-powered chatbot for natural language querying.

The system follows a **fan-out / fallback** architecture: one primary source (Yonepse), two secondary scraped sources (Merolagani, Sharesansar), a local SQLite database for persistence, and a local LLM (Ollama) for AI responses.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                           │
│  (React + TypeScript + TanStack Query + Framer Motion)  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ LiveMarket│ │ Trade    │ │ Portfolio│ │ Chatbot    │ │
│  │ Page     │ │ Page     │ │ Page     │ │ (Floating) │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬─────┘ │
│       │            │            │               │       │
│  ┌────▼────────────▼────────────▼───────────────▼─────┐ │
│  │             api/client.ts (typed fetch wrapper)     │ │
│  │          AbortController + 30s timeout + 3 errors   │ │
│  └─────────────────────┬───────────────────────────────┘ │
│                        │ HTTP                             │
└────────────────────────┼─────────────────────────────────┘
                         │
                    Vite proxy (/api → 127.0.0.1:8001)
                         │
┌────────────────────────▼─────────────────────────────────┐
│               FastAPI Backend (Python)                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │              main.py (API router)                │    │
│  │  ┌────────┐ ┌──────────┐ ┌───────┐ ┌─────────┐  │    │
│  │  │ Market │ │ Stocks   │ │Portf. │ │ Chat    │  │    │
│  │  │ Routes │ │ Routes   │ │Routes │ │ Routes  │  │    │
│  │  └───┬────┘ └────┬─────┘ └───┬───┘ └────┬────┘  │    │
│  │      │           │           │          │         │    │
│  └──────┼───────────┼───────────┼──────────┼─────────┘    │
│         │           │           │          │               │
│  ┌──────▼───────────▼───────────▼──────────▼──────────┐   │
│  │              Data Sources Layer                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐           │   │
│  │  │ Yonepse  │ │Merolagani│ │Sharesansar│           │   │
│  │  │(PRIMARY) │ │(SECOND.) │ │(TERTIARY)│           │   │
│  │  │ GitHub   │ │ Scraped  │ │ Scraped  │           │   │
│  │  │   CDN    │ │+SignalR  │ │          │           │   │
│  │  └──────────┘ └──────────┘ └──────────┘           │   │
│  │  ┌──────────────────────────────────────────────┐ │   │
│  │  │              Cache Layer                      │ │   │
│  │  │  TTLCache + asyncio.Lock + disk persistence  │ │   │
│  │  └──────────────────────────────────────────────┘ │   │
│  │  ┌──────────────────────────────────────────────┐ │   │
│  │  │          SQLite (aiosqlite)                   │ │   │
│  │  │  daily_prices | signals | portfolio_holdings  │ │   │
│  │  │  index_history | backtest_results             │ │   │
│  │  └──────────────────────────────────────────────┘ │   │
│  └───────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────┐    │
│  │           LLM Integration Layer           │    │
│  │  ┌──────────────────────┐                │    │
│  │  │ Ollama (local)       │                │    │
│  │  │ qwen2.5:7b           │                │    │
│  │  └──────────────────────┘                │    │
│  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Data Sources (Priority Order)

| Source | Type | Priority | Reliability | Provides | Circuit Breaker |
|--------|------|----------|-------------|----------|-----------------|
| **Yonepse** | GitHub JSON CDN | PRIMARY | Always up (CDN) | Live prices, indices, top stocks, summary, brokers, market status | None (CDN) |
| **Merolagani** | Scraped HTML + SignalR | SECONDARY | Unstable (IIS rate-limits) | Company detail (sector, 52W, 120D avg, yield), index history | 3 failures → 60s cooldown |
| **Sharesansar** | Scraped HTML | TERTIARY | Moderate | Company detail fallback, pivot/MA/VWAP, floorsheet, all-indices | Instance-level, TTL caches |
| **SQLite / Disk** | Local DB + JSON files | LAST RESORT | Always available | Historical prices, portfolio, signals, backtest results | N/A |

### Fallback Chain

```
Live prices:         Yonepse → Merolagani merge → Sharesansar → disk cache
Company detail:      Merolagani (if circuit open? → Sharesansar → None
Index streaming:     Merolagani (SignalR) → Yonepse (poll) → None
LLM response:        Ollama (local) → Hardcoded fallback
Market status:       Yonepse → {is_open: false, last_checked: None}
Portfolio:           SQLite → Error banner → Retry button
```

---

## Backend Architecture

### Technology Stack

- **Framework**: FastAPI (Python 3.13)
- **Database**: SQLite via aiosqlite + SQLAlchemy async
- **HTTP Client**: httpx (async)
- **HTML Parsing**: BeautifulSoup4
- **Caching**: cachetools.TTLCache + disk JSON persistence
- **Technical Analysis**: pandas, numpy (RSI, MACD, SMA, ADX)
- **LLM**: Ollama (local)

### File Structure

```
backend/
├── main.py                          # API router, LLM streaming, data context builder
├── config.py                        # Centralized URLs, timeouts, model names, user agents
├── database.py                      # SQLAlchemy engine + session factory
├── models.py                        # ORM models (Security, DailyPrice, Signal, etc.)
├── data/
│   ├── fetcher.py                   # Yonepse HTTP fetcher (module-level circuit breaker)
│   ├── merolagani_fetcher.py        # Merolagani scraper + SignalR index stream
│   ├── sharesansar_fetcher.py       # Sharesansar scraper (detail, floorsheet, indices)
│   ├── broker_fetcher.py            # Yonepse broker list fetcher
│   ├── cache.py                     # TTLCache with asyncio.Lock + disk persistence
│   ├── market_scheduler.py          # Background scheduler for periodic data refresh
│   ├── seeder.py                    # Backfill historical prices
│   └── updater.py                   # Daily price update logic
├── analysis/
│   ├── indicators.py                # Technical indicator computation (RSI, MACD, SMA, ADX)
│   ├── signals.py                   # Signal generation from indicators
│   └── backtest.py                  # Backtesting engine
└── search/
    └── fuzzy.py                     # Fuzzy symbol search + NLP intent detection
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/market/live` | GET | Merged live prices (Yonepse + Sharesansar fields) |
| `/api/market/overview` | GET | Indices, top gainers/losers, market summary |
| `/api/market/status` | GET | Market open/closed status |
| `/api/market/index-history` | GET | Historical index snapshots |
| `/api/stocks/{symbol}/detail` | GET | Company detail + technical indicators |
| `/api/stocks/{symbol}/history` | GET | Historical daily prices |
| `/api/stocks/{symbol}/floorsheet` | GET | Recent floorsheet transactions |
| `/api/stocks/compare` | GET | Side-by-side stock comparison |
| `/api/search` | GET | Fuzzy symbol search + NLP intent |
| `/api/signals` | GET | Generated trading signals |
| `/api/backtest` | POST | Run backtest simulation |
| `/api/portfolio` | GET | User's portfolio holdings |
| `/api/portfolio/holdings` | POST | Add holding |
| `/api/portfolio/holdings/{id}` | PUT/DELETE | Update/delete holding |
| `/api/brokers/top` | GET | Top brokers by turnover |
| `/api/brokers/search` | GET | Broker directory search |
| `/api/ask` | POST | LLM chatbot (streaming SSE) |
| `/api/guide/search` | GET | Guide + FAQ search |
| `/api/health` | GET | System health check |

### Error Handling Strategy

- **Circuit Breaker**: Each fetcher has a circuit breaker (3 failures → 60s cooldown). POST operations in Sharesansar fetcher are also covered.
- **Retry**: Exponential backoff (2^attempt seconds) for transient HTTP errors.
- **Exception Context**: All exceptions include source identifier and operation in log message.
- **Graceful Degradation**: Every endpoint returns empty/default data rather than 500 on source failure.
- **User Feedback**: Frontend displays error banners with retry buttons; never silently fails.
- **AbortController**: All frontend data fetches have AbortController with timeout for cancellation.

### Caching Layers

1. **In-memory TTLCache**: Live prices (30s), IPOs (60s), data context (30s)
2. **Disk persistence**: Cache snapshots survive server restarts (prewarmed on startup)
3. **SQLite**: Historical prices, portfolio, signals persist indefinitely
4. **Locks**: All cache operations use `asyncio.Lock` — never blocks the event loop

---

## Frontend Architecture

### Technology Stack

- **Framework**: React 19, TypeScript
- **Routing**: React Router v7
- **State/Data Fetching**: TanStack Query v5
- **Animation**: Framer Motion
- **Charts**: lightweight-charts (TradingView)
- **Build**: Vite 6
- **Linting**: oxlint

### File Structure

```
frontend/src/
├── api/
│   ├── client.ts           # Typed fetch wrapper (AbortController, timeouts, error classes)
│   └── endpoints.ts         # All API endpoint functions + TypeScript interfaces
├── components/
│   ├── SearchBar.tsx        # Stock search with autocomplete dropdown
│   ├── SymbolSearchInput.tsx # Reusable symbol search (used in Portfolio modal)
│   ├── FloorsheetPanel.tsx  # Expandable floorsheet table
│   ├── ComparePanel.tsx     # Side-by-side stock comparison
│   ├── FloatingChat.tsx     # Chatbot bubble + chat interface
│   ├── StockChart.tsx       # Candlestick/line chart with indicators
│   ├── CompanyInfo.tsx      # Company detail panel
│   └── ... (20+ more)
├── config/
│   └── constants.ts         # Centralized constants (poll intervals, timeouts, API_BASE)
├── hooks/
│   ├── useStockData.ts      # TanStack Query hooks for market data
│   ├── useMarketStatus.ts   # Market open/closed polling
│   ├── useLLMQuery.ts          # LLM streaming + chat history
│   └── ... (5+ more)
├── pages/
│   ├── LiveMarket.tsx       # Real-time market dashboard
│   ├── Trade.tsx            # Stock detail + chart + floorsheet
│   ├── Portfolio.tsx        # User portfolio with add/edit/delete
│   ├── Brokers.tsx          # Broker ranking + search
│   ├── Guide.tsx            # Educational guide + FAQ
│   └── ... (4+ more)
├── types/
│   └── index.ts             # Shared TypeScript interfaces
├── utils/
│   └── format.ts            # Number formatting (NPR, percentage, etc.)
└── App.tsx                  # Router + layout + theme
```

### Data Fetching Pattern

```
Component → endpoint function → api/client.ts → fetch + AbortController
                                 ↓
                 apiGet/apiPost (typed generic)
                                 ↓
                  res.json() as Promise<T>
                                 ↓
              Returns typed response to component
```

All hooks use TanStack Query for caching, dedup, refetch intervals, and error state. Every mutable operation uses `useMutation` with optimistic updates.

### Error Handling

- **API Client**: 3 error classes (`ApiError`, `NetworkError`, `TimeoutError`)
- **AbortController**: User-initiated or auto-timeout (default 30s)
- **ErrorBanner**: Reusable dismissible/retryable error bar
- **Loading states**: Shimmer skeletons for initial load
- **Empty states**: Yellow warning with descriptive message
- **Error states**: Red warning with error details + optional retry

---

## LLM Integration

### Flow

```
1. User asks question
2. NLP detects intent + symbols (fuzzy search)
3. build_data_context() fetches live data, indicators, company detail
4. Data injected into system prompt as PROVIDED DATA
5. LLM generates response using data context
6. Response streamed via SSE (server-sent events)
```

### Model Selection

| Model | Role | Quality | Fallback |
|-------|------|---------|----------|
| `qwen2.5:7b-instruct-q4_k_m` | Primary (Ollama local) | Good instruction following | — |

### Prompt Design

The `GUIDE_SYSTEM_PROMPT` includes:
- Scope (NEPSE only)
- Tone (friendly, warm, approachable)
- Guidelines (data accuracy, no guessing, disclaimer required)
- Strict format rules (compact lines, max 12 lines, bold headers)
- Hallucination guard: "If a metric is not in the data, say not available"

### Conversation History

- Stored in browser `localStorage` under `nepse-chat-history`
- Last 6 messages sent with each request
- Cleared on "New Chat" action

---

## Database Schema

```sql
Security
  symbol TEXT PRIMARY KEY
  name TEXT NOT NULL
  sector TEXT

DailyPrice
  id INTEGER PRIMARY KEY
  symbol TEXT NOT NULL           -- FK → Security.symbol
  date TEXT NOT NULL             -- YYYY-MM-DD
  open REAL
  high REAL
  low REAL
  close REAL
  volume INTEGER
  UNIQUE(symbol, date)

Signal
  id INTEGER PRIMARY KEY
  symbol TEXT NOT NULL
  signal_type TEXT NOT NULL      -- BUY | SELL | HOLD
  confidence REAL
  reason TEXT
  generated_at DATETIME DEFAULT NOW

PortfolioHolding
  id INTEGER PRIMARY KEY
  symbol TEXT NOT NULL
  quantity INTEGER NOT NULL
  avg_cost REAL NOT NULL
  buy_date DATE
  notes TEXT
  created_at DATETIME DEFAULT NOW

BacktestResult
  id INTEGER PRIMARY KEY
  symbol TEXT
  fast_ma INTEGER
  slow_ma INTEGER
  days INTEGER
  result JSON
  created_at DATETIME DEFAULT NOW

IndexHistory
  id INTEGER PRIMARY KEY
  index_name TEXT
  date TEXT
  open REAL
  high REAL
  low REAL
  close REAL
  UNIQUE(index_name, date)
```

---

## Key Design Decisions

1. **Yonepse first, scrape only when needed**: The CDN-served JSON is always up and free. Scraping (Merolagani, Sharesansar) is only used for fields Yonepse doesn't provide.

2. **Circuit breakers prevent cascade failures**: If a source is down, the system degrades gracefully rather than timing out.

3. **`asyncio.Lock` over `threading.Lock`**: All cache operations use async locks so the event loop is never blocked.

4. **All fetchers are instance classes, not modules**: Encapsulated state, separate circuit breakers, testable.

5. **`127.0.0.1` not `localhost`**: Windows IPv6 resolution of `localhost` to `::1` causes connection issues.

6. **No NepalStock**: It was removed — unreliable and redundant with Yonepse.

7. **Frontend API calls go through typed wrapper**: Every fetch goes through `api/client.ts` → `api/endpoints.ts` → component. Raw `fetch` is never called in pages (exceptions: SSE streaming in chat which needs special handling).

8. **SQLite with async driver**: aiosqlite allows concurrent reads without thread pool blocking.

9. **LLM runs locally**: Ollama with `qwen2.5:7b` eliminates API costs and keeps sensitive data local.

---

## Performance Considerations

- **TTL caches**: Live prices cache 30s, IPO data 60s, data context 30s
- **Scheduler**: Refresh prices every 30s, summary/top/indices every 300s during market hours
- **N+1 prevention**: Single DB session for signal generation (fixed from 400+ to 1)
- **Batch queries**: Portfolio holdings enrich prices in batch (1 API call for all symbols)
- **Index polling**: Index history polled every 15s via SignalR or Yonepse fallback
- **AbortController**: 30s timeout on all frontend API calls, 10s on floorsheet

---

## Security & Privacy

- **No API keys in code**: All configuration is local, no third-party API keys required
- **Local LLM**: All stock data stays on-device; no data sent to third parties
- **No user authentication**: Portfolio stored in local SQLite; no multi-user support
- **CORS**: Not configured (Vite proxy handles same-origin in dev)
- **Rate limiting**: Not implemented (external sources have their own limits)
