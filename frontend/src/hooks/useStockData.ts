import { useQuery } from '@tanstack/react-query'
import { useMarketStatus } from './useMarketStatus'
import { fetchMarketOverview, fetchStockHistory, fetchSignals, fetchBacktest } from '../api/endpoints'
import { POLL } from '../config/constants'

/** Fetch and cache market overview data with auto-refresh. */
export function useMarketOverview() {
  const { is_open } = useMarketStatus()
  const interval = is_open ? POLL.MARKET_OVERVIEW_OPEN : false

  return useQuery({
    queryKey: ['market-overview'],
    queryFn: fetchMarketOverview,
    refetchInterval: interval,
  })
}

/** Fetch and cache stock history with auto-refresh. */
export function useStockHistory(symbol: string, start: string, end: string) {
  const { is_open } = useMarketStatus()
  const interval = is_open ? POLL.STOCK_HISTORY_OPEN : false

  return useQuery({
    queryKey: ['stock-history', symbol, start, end],
    queryFn: () => fetchStockHistory(symbol, start, end),
    enabled: !!symbol,
    refetchInterval: symbol ? interval : undefined,
  })
}

/** Fetch and cache trading signals with auto-refresh. */
export function useSignals(type?: string) {
  const { is_open } = useMarketStatus()
  const interval = is_open ? POLL.SIGNALS_OPEN : false

  return useQuery({
    queryKey: ['signals', type || 'all'],
    queryFn: () => fetchSignals(type),
    refetchInterval: interval,
  })
}

/** Fetch and cache backtest results for a symbol. */
export function useBacktest(symbol: string, fast: number, slow: number, days: number, run: boolean) {
  return useQuery({
    queryKey: ['backtest', symbol, fast, slow, days],
    queryFn: () => fetchBacktest(symbol, fast, slow, days),
    enabled: run && !!symbol,
  })
}
