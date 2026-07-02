import { useQuery } from '@tanstack/react-query'
import { useMarketStatus } from './useMarketStatus'

const API = '/api'

export function useMarketOverview() {
  const { is_open } = useMarketStatus()
  const interval = is_open ? 30_000 : 3_600_000

  return useQuery({
    queryKey: ['market-overview'],
    queryFn: async () => {
      const res = await fetch(`${API}/market/overview`)
      if (!res.ok) throw new Error('Market data unavailable')
      return res.json()
    },
    refetchInterval: interval,
  })
}

export function useStockHistory(symbol: string, start: string, end: string) {
  const { is_open } = useMarketStatus()
  const interval = is_open ? 60_000 : 3_600_000

  return useQuery({
    queryKey: ['stock-history', symbol, start, end],
    queryFn: async () => {
      const params = new URLSearchParams({ start, end })
      const res = await fetch(`${API}/stocks/${symbol}/history?${params}`)
      if (!res.ok) throw new Error('Stock data unavailable')
      return res.json()
    },
    enabled: !!symbol,
    refetchInterval: symbol ? interval : undefined,
  })
}

export function useSearch(query: string) {
  return useQuery({
    queryKey: ['search', query],
    queryFn: async () => {
      if (!query.trim()) return { results: [], suggestions: [] }
      const res = await fetch(`${API}/search?query=${encodeURIComponent(query)}`)
      if (!res.ok) throw new Error('Search failed')
      return res.json()
    },
    enabled: query.length > 0,
  })
}

export function useSignals(type?: string) {
  const { is_open } = useMarketStatus()
  const interval = is_open ? 120_000 : 3_600_000

  return useQuery({
    queryKey: ['signals', type],
    queryFn: async () => {
      const params = type ? `?signal_type=${type}` : ''
      const res = await fetch(`${API}/signals${params}`)
      if (!res.ok) throw new Error('Signals unavailable')
      return res.json()
    },
    refetchInterval: interval,
  })
}

export function useBacktest(symbol: string, fast: number, slow: number, days: number, run: boolean) {
  return useQuery({
    queryKey: ['backtest', symbol, fast, slow, days],
    queryFn: async () => {
      const params = new URLSearchParams({ symbol, fast_ma: String(fast), slow_ma: String(slow), days: String(days) })
      const res = await fetch(`${API}/backtest?${params}`, { method: 'POST' })
      if (!res.ok) throw new Error('Backtest failed')
      return res.json()
    },
    enabled: run,
  })
}
