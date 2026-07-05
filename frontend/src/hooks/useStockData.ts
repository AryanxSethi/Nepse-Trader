import { useQuery } from '@tanstack/react-query'
import { useMarketStatus } from './useMarketStatus'
import { fetchMarketOverview, fetchStockHistory, fetchSignals, fetchBacktest } from '../api/endpoints'

export function useMarketOverview() {
  const { is_open } = useMarketStatus()
  const interval = is_open ? 15_000 : false

  return useQuery({
    queryKey: ['market-overview'],
    queryFn: fetchMarketOverview,
    refetchInterval: interval,
  })
}

export function useStockHistory(symbol: string, start: string, end: string) {
  const { is_open } = useMarketStatus()
  const interval = is_open ? 60_000 : false

  return useQuery({
    queryKey: ['stock-history', symbol, start, end],
    queryFn: () => fetchStockHistory(symbol, start, end),
    enabled: !!symbol,
    refetchInterval: symbol ? interval : undefined,
  })
}

export function useSignals(type?: string) {
  const { is_open } = useMarketStatus()
  const interval = is_open ? 120_000 : false

  return useQuery({
    queryKey: ['signals', type || 'all'],
    queryFn: () => fetchSignals(type),
    refetchInterval: interval,
  })
}

export function useBacktest(symbol: string, fast: number, slow: number, days: number, run: boolean) {
  return useQuery({
    queryKey: ['backtest', symbol, fast, slow, days],
    queryFn: () => fetchBacktest(symbol, fast, slow, days),
    enabled: run,
  })
}
