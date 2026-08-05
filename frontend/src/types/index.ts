export interface Stock {
  symbol: string
  name: string
  sector?: string
}

export interface PricePoint {
  symbol: string
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  turnover?: number
}

export interface Indicators {
  close?: number
  rsi?: number
  macd?: number
  macd_signal?: number
  macd_hist?: number
  bb_upper?: number
  bb_middle?: number
  bb_lower?: number
  atr?: number
  adx?: number
  ema12?: number
  ema26?: number
  sma20?: number
  sma50?: number
  trend?: string
  volume_avg?: number
  volume_recent?: number
}

export interface SignalResult {
  type: string
  confidence: number
  reason: string
}

export interface StockData {
  prices: PricePoint[]
  indicators: Indicators
  signal: SignalResult | null
}

export interface SignalRow {
  symbol: string
  signal_type: string
  confidence: number
  reason: string
  generated_at: string
}

export interface BacktestData {
  symbol: string
  strategy: string
  total_return: number
  buy_hold_return: number
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  total_trades: number
  total_costs: number
  equity_curve: { date: string; value: number }[]
}

export interface GuideEntry {
  id: string
  keywords: string[]
  title: string
  content: string[]
  sources: { name: string; url: string }[]
}

export interface Broker {
  code: string
  name: string
  address: string
  phone: string
  districts?: string[]
  tms_link?: string
  branch_count?: number
  active_status?: string
  thirty_days_turnover?: number
  latest_turnover?: number
}

export interface BrokerDetail {
  rank: number
  code: string
  name: string
  phone: string
  districts: string[]
  tms_link: string
  branch_count: number
  active_status: string
  thirty_days_turnover: number
  latest_turnover: number
}

export interface SectorInfo {
  name: string
  stockCount: number
}

export interface IpoDetail {
  company: string
  symbol: string
  issue_size: string
  open_date: string
  open_date_bs: string
  close_date: string
  close_date_bs: string
  price_range: string
  status: string
  share_type: string
  share_registrar: string
  rating: string
  sector: string
  min_units: string
  max_units: string
  price_per_unit: string
  ipo_id?: number
}

export interface SearchSuggestion {
  symbol: string
  name: string
  match_type: string
  score: number
  ltp?: number
  percent_change?: number
}

export interface GainerLoserItem {
  symbol: string
  change?: number
  ltp?: number
  percent_change?: number
}

export interface MarketOverview {
  indices: { name: string; value: number; change: number; percent_change?: number }[]
  summary: { turnover: number | null; trades: number | null; scrips: number | null; market_cap: number | null }
  top_gainers: GainerLoserItem[]
  top_losers: GainerLoserItem[]
  most_active: { symbol: string; turnover: number; price?: number; ltp?: number }[]
  sectors?: { name: string; turnover: number }[]
  _fetched_at?: string
}

export interface MarketStatus {
  is_open: boolean
  as_of: string
  next_open: string
  next_close: string | null
}
