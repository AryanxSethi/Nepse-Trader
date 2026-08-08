import { apiGet, apiPost, apiDelete, apiPut } from './client'
import { API_BASE } from '../config/constants'
import { TIMEOUT } from '../config/constants'
import type {
  MarketOverview,
  MarketStatus,
  StockData,
  SignalRow,
  BacktestData,
  Broker,
  BrokerDetail,
  SearchSuggestion,
  IpoDetail,
  GuideEntry,
  Stock,
} from '../types'

export interface CompareItem {
  symbol: string
  name: string
  ltp: number | null
  change: number | null
  percent_change: number | null
  volume: number | null
  turnover: number | null
  market_cap: number | null
  rsi: number | null
  macd: number | null
  macd_signal: number | null
  sma20: number | null
  sma50: number | null
  adx: number | null
  trend: string | null
  signal_type: string | null
  signal_confidence: number | null
  prices?: { date: string; close: number }[]
}

export interface StockDetail {
  sector?: string
  market_price?: string
  percent_change?: string
  last_traded_on?: string
  '52w_high'?: string
  '52w_low'?: string
  '120d_avg'?: string
  '1y_yield'?: string
  vwap?: string
  prev_close?: string
  volume?: string
  avg_180d?: string
  confidence_score?: string
  pivot_s3?: string
  pivot_s2?: string
  pivot_s1?: string
  pivot_pp?: string
  pivot_r1?: string
  pivot_r2?: string
  pivot_r3?: string
  ma5_signal?: string
  ma20_signal?: string
  ma180_signal?: string
  [key: string]: string | undefined
}

export interface PortfolioHolding {
  id: number
  symbol: string
  quantity: number
  avg_cost: number
  ltp: number | null
  change: number | null
  invested: number
  current_value: number | null
  pnl: number | null
  notes: string
  created_at: string
}

// --- Market ---

/** Fetch market overview data (indices, summary). */
export function fetchMarketOverview(opts?: { signal?: AbortSignal }): Promise<MarketOverview> {
  return apiGet(`${API_BASE}/market/overview`, opts)
}

export interface LivePriceEntry {
  symbol: string
  ltp: number | null
  percent_change: number | null
  volume?: number | null
  prev_close?: number | null
  [key: string]: unknown
}

export interface LiveIndexEntry {
  name: string
  value: number | null
  change: number | null
  percent_change: number | null
}

/** Fetch live market prices and indices. */
export function fetchMarketLive(opts?: { signal?: AbortSignal }): Promise<{ prices: LivePriceEntry[]; indices: LiveIndexEntry[]; timestamp: string | null }> {
  return apiGet(`${API_BASE}/market/live`, opts)
}

export interface IndexSnapshot {
  time: number
  values: Record<string, number>
}

/** Fetch index history snapshots for charting. */
export function fetchIndexHistory(opts?: { signal?: AbortSignal }): Promise<{ snapshots: IndexSnapshot[]; points: (IndexSnapshot | { time: number; value: number })[]; today: IndexSnapshot[]; current: unknown; indices: unknown; last_updated: number | null }> {
  return apiGet(`${API_BASE}/market/index-history`, opts)
}

// --- Companies & Securities ---

/** Fetch company list with optional LTP/change. */
export function fetchCompanies(opts?: { signal?: AbortSignal }): Promise<{ symbol: string; name: string; ltp?: number; percent_change?: number }[]> {
  return apiGet(`${API_BASE}/companies`, opts)
}

/** Fetch all securities (full stock list). */
export function fetchSecurities(opts?: { signal?: AbortSignal }): Promise<Stock[]> {
  return apiGet(`${API_BASE}/securities`, opts)
}

export interface SearchResponse {
  suggestions: SearchSuggestion[]
  symbol?: string
  start?: string
  end?: string
}

/** Search stocks, companies, or symbols. */
export function fetchSearch(query: string, opts?: { signal?: AbortSignal }): Promise<SearchResponse> {
  return apiGet(`${API_BASE}/search?query=${encodeURIComponent(query)}`, opts)
}

// --- Stocks ---

/** Fetch historical price data for a stock. */
export function fetchStockHistory(symbol: string, start: string, end: string, opts?: { signal?: AbortSignal }): Promise<StockData> {
  return apiGet(`${API_BASE}/stocks/${symbol}/history?start=${start}&end=${end}`, opts)
}

/** Fetch detailed info and fundamentals for a stock. */
export function fetchStockDetail(symbol: string, opts?: { signal?: AbortSignal }): Promise<StockDetail> {
  return apiGet(`${API_BASE}/stocks/${encodeURIComponent(symbol)}/detail`, opts)
}

/** Compare multiple stocks side by side. */
export function fetchCompare(symbols: string[], opts?: { signal?: AbortSignal }): Promise<{ comparison: CompareItem[] }> {
  return apiGet(`${API_BASE}/stocks/compare?symbols=${symbols.join(',')}`, { signal: opts?.signal, timeout: TIMEOUT.COMPARE })
}

// --- Signals ---

/** Fetch trading signals, optionally filtered by type. */
export function fetchSignals(type?: string, opts?: { signal?: AbortSignal }): Promise<SignalRow[]> {
  const params = type ? `?signal_type=${type}` : ''
  return apiGet(`${API_BASE}/signals${params}`, opts)
}

/** Trigger on-demand signal generation. */
export function triggerSignalGeneration(): Promise<{ status: string }> {
  return apiPost(`${API_BASE}/signals/generate`)
}

// --- Backtest ---

/** Run a backtest for a symbol with MA crossover strategy. */
export function fetchBacktest(symbol: string, fast: number, slow: number, days: number): Promise<BacktestData> {
  return apiPost(`${API_BASE}/backtest?symbol=${symbol}&fast_ma=${fast}&slow_ma=${slow}&days=${days}`, undefined, {
    timeout: 30000,
  })
}

// --- Portfolio ---

export interface PortfolioResponse {
  holdings: PortfolioHolding[]
  total_invested: number
  total_value: number
  total_pl: number
  total_pl_percent: number
}

/** Fetch user portfolio with holdings and summary. */
export function fetchPortfolio(opts?: { signal?: AbortSignal }): Promise<PortfolioResponse> {
  return apiGet(`${API_BASE}/portfolio`, opts)
}

export interface HoldingResponse {
  id: number
  symbol: string
  quantity: number
  avg_cost: number
  [key: string]: unknown
}

export interface StatusResponse {
  status: string
}

export interface IpoPager {
  pageNo: number
  itemsPerPage: number
  totalNextPages: number
  totalPages: number
}

/** Add a new holding to the portfolio. */
export function addHolding(symbol: string, quantity: number, avgCost: number, buyDate?: string, notes?: string): Promise<HoldingResponse> {
  let url = `${API_BASE}/portfolio/holdings?symbol=${symbol}&quantity=${quantity}&avg_cost=${avgCost}`
  if (buyDate) url += `&buy_date=${buyDate}`
  if (notes) url += `&notes=${notes}`
  return apiPost(url)
}

/** Update an existing portfolio holding. */
export function updateHolding(id: number, quantity: number, avgCost: number, notes?: string): Promise<HoldingResponse> {
  return apiPut(`${API_BASE}/portfolio/holdings/${id}?quantity=${quantity}&avg_cost=${avgCost}${notes ? `&notes=${notes}` : ''}`)
}

/** Delete a holding from the portfolio. */
export function deleteHolding(id: number): Promise<StatusResponse> {
  return apiDelete(`${API_BASE}/portfolio/holdings/${id}`)
}

// --- IPOs ---

/** Fetch IPO listings with pagination. */
export function fetchIpos(page: number = 1, perPage: number = 20, opts?: { signal?: AbortSignal }): Promise<{ data: IpoDetail[]; pager: IpoPager }> {
  return apiGet(`${API_BASE}/ipos?page=${page}&per_page=${perPage}`, opts)
}

// --- Brokers ---

/** Fetch top brokers by transaction volume. */
export function fetchBrokerTop(period: string = "monthly", limit: number = 20): Promise<{ brokers: BrokerDetail[] }> {
  return apiGet(`${API_BASE}/brokers/top?period=${period}&limit=${limit}`)
}

/** Search brokers by name or code. */
export function fetchBrokerSearch(query: string): Promise<{ brokers: Broker[] }> {
  return apiGet(`${API_BASE}/brokers/search?q=${encodeURIComponent(query)}`)
}

// --- Market ---

/** Fetch current market open/close status. */
export function fetchMarketStatus(signal?: AbortSignal): Promise<MarketStatus> {
  return apiGet(`${API_BASE}/market/status`, { signal, timeout: TIMEOUT.STATUS })
}

// --- Guide ---

/** Search the investor guide for entries. */
export function fetchGuideSearch(query: string, opts?: { signal?: AbortSignal }): Promise<{ entries: GuideEntry[]; llm_answer?: string }> {
  return apiGet(`${API_BASE}/guide/search?q=${encodeURIComponent(query)}`, opts)
}

// --- Health ---

/** Check API server health. */
export function fetchHealth(): Promise<{ status: string }> {
  return apiGet(`${API_BASE}/health`)
}
