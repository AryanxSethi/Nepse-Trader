import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMarketStatus } from '../hooks/useMarketStatus'
import { usePageTitle } from '../hooks/usePageTitle'
import { PageTransition } from '../components/Navbar'
import FloatingChat from '../components/FloatingChat'
import ErrorBanner from '../components/ErrorBanner'
import RefreshIndicator from '../components/RefreshIndicator'
import { SkeletonCard, SkeletonChart } from '../components/Skeleton'
import { TrendingUpIcon, TrendingDownIcon, SearchIcon } from '../components/Icons'
import { formatTurnover } from '../utils/format'
import { formatNPR, formatPercent, formatChange } from '../utils/format'
import { fetchMarketLive } from '../api/endpoints'
import { POLL } from '../config/constants'
import IndexChart from '../components/IndexChart'

interface IndexData {
  name: string
  value: number | null
  change: number | null
  percent_change: number | null
}

interface StockPrice {
  symbol: string
  ltp: number | null
  percent_change: number | null
  volume?: number | null
  turnover?: number | null
}

type SortKey = 'symbol' | 'ltp' | 'percent_change' | 'volume' | 'turnover'

const INDEX_PRIORITY = ['NEPSE', 'Sensitive Index', 'Float Index']

function sortIndices(indices: IndexData[]): IndexData[] {
  return [...indices].sort((a, b) => {
    const ai = INDEX_PRIORITY.indexOf(a.name)
    const bi = INDEX_PRIORITY.indexOf(b.name)
    if (ai !== -1 && bi !== -1) return ai - bi
    if (ai !== -1) return -1
    if (bi !== -1) return 1
    return a.name.localeCompare(b.name)
  })
}


/** Live market page with real-time indices, stock prices, and index chart. */
export default function LiveMarket() {
  const navigate = useNavigate()
  const [indices, setIndices] = useState<IndexData[]>([])
  const [prices, setPrices] = useState<StockPrice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [fetchedAt, setFetchedAt] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('turnover')
  const [sortAsc, setSortAsc] = useState(false)

  usePageTitle('Live Market')
  const marketStatus = useMarketStatus()

  const fetchData = useCallback(async () => {
    try {
      const json = await fetchMarketLive()
      setIndices(sortIndices(json.indices || []))
      setPrices(json.prices || [])
      setError(null)
      setFetchedAt(new Date().toISOString())
    } catch {
      setError('Failed to load market data. Check your connection.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    let id: ReturnType<typeof setInterval> | null = null
    if (marketStatus.is_open) {
      id = setInterval(fetchData, POLL.MARKET_OVERVIEW_OPEN)
    }
    return () => { if (id) clearInterval(id) }
  }, [fetchData, marketStatus.is_open])

  const filtered = useMemo(() => {
    let items = prices
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      items = items.filter((p) => p.symbol.toLowerCase().includes(q))
    }
    const sorted = [...items].sort((a, b) => {
      const aVal = a[sortKey] ?? 0
      const bVal = b[sortKey] ?? 0
      if (typeof aVal === 'string') {
        return sortAsc ? aVal.localeCompare(bVal as string) : (bVal as string).localeCompare(aVal as string)
      }
      return sortAsc ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
    })
    return sorted
  }, [prices, search, sortKey, sortAsc])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(key === 'symbol')
    }
  }

  const sortArrow = (key: SortKey) => {
    if (sortKey !== key) return ''
    return sortAsc ? ' \u25B2' : ' \u25BC'
  }

  if (loading) {
    return (
      <PageTransition>
        <div className="max-w-6xl mx-auto px-4 py-6 space-y-4">
          <div className="h-8 w-48" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[1,2,3,4].map(i => <SkeletonCard key={i} lines={2} />)}
          </div>
          <SkeletonChart height={380} />
        </div>
      </PageTransition>
    )
  }

  return (
    <PageTransition>
      <div className="max-w-6xl mx-auto px-4 py-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUpIcon size={20} className="text-accent" />
            <h1 className="text-xl font-bold text-text">Live Market</h1>
          </div>
          <RefreshIndicator fetchedAt={fetchedAt} />
        </div>

        {!marketStatus.is_open && !loading && (
          <div className="rounded-xl bg-amber/10 border border-amber/20 p-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-medium text-amber">Market Closed</span>
              <span className="text-[10px] text-text-muted">Last updated: {fetchedAt ? new Date(fetchedAt).toLocaleTimeString() : '\u2014'}</span>
            </div>
          </div>
        )}

        {error && <ErrorBanner message={error} onRetry={fetchData} />}

        {indices.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {indices.map((idx) => (
              <div key={idx.name} className="rounded-xl bg-surface-card border border-border p-3">
                <p className="text-[11px] text-text-muted truncate">{idx.name}</p>
                <p className="text-lg font-bold text-text mt-1">{formatNPR(idx.value, 2)}</p>
                <p className={`text-xs font-medium mt-0.5 ${(idx.percent_change ?? idx.change ?? 0) >= 0 ? 'text-green' : 'text-red'}`}>
                  {formatChange(idx.change)}
                  <span className="ml-1">{(idx.percent_change ?? 0) >= 0 ? '+' : ''}{idx.percent_change?.toFixed(2)}%</span>
                </p>
              </div>
            ))}
          </div>
        )}

        <IndexChart />

        <div className="relative">
          <SearchIcon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by symbol..."
            className="w-full bg-surface-card border border-border rounded-xl pl-9 pr-4 py-2.5 text-sm text-text placeholder-text-muted/40 outline-none focus:border-accent/50 transition-colors"
          />
        </div>

        <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-hover/50">
                  <th onClick={() => toggleSort('symbol')} className="text-left px-4 py-2.5 text-[11px] font-semibold text-text-muted uppercase tracking-wider cursor-pointer hover:text-text select-none">
                    Symbol{sortArrow('symbol')}
                  </th>
                  <th onClick={() => toggleSort('ltp')} className="text-right px-4 py-2.5 text-[11px] font-semibold text-text-muted uppercase tracking-wider cursor-pointer hover:text-text select-none">
                    LTP{sortArrow('ltp')}
                  </th>
                  <th onClick={() => toggleSort('percent_change')} className="text-right px-4 py-2.5 text-[11px] font-semibold text-text-muted uppercase tracking-wider cursor-pointer hover:text-text select-none">
                    % Change{sortArrow('percent_change')}
                  </th>
                  <th onClick={() => toggleSort('volume')} className="text-right px-4 py-2.5 text-[11px] font-semibold text-text-muted uppercase tracking-wider cursor-pointer hover:text-text select-none hidden sm:table-cell">
                    Volume{sortArrow('volume')}
                  </th>
                  <th onClick={() => toggleSort('turnover')} className="text-right px-4 py-2.5 text-[11px] font-semibold text-text-muted uppercase tracking-wider cursor-pointer hover:text-text select-none hidden md:table-cell">
                    Turnover{sortArrow('turnover')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p, i) => {
                  const isPositive = (p.percent_change ?? 0) >= 0
                  return (
                    <tr
                      key={`${p.symbol}-${i}`}
                      onClick={() => navigate(`/trade?symbol=${p.symbol}`)}
                      className="border-b border-border/50 hover:bg-surface-hover/50 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-2.5">
                        <span className="text-sm font-semibold text-text">{p.symbol}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono-nums text-text">
                        {formatNPR(p.ltp)}
                      </td>
                      <td className={`px-4 py-2.5 text-right font-mono-nums font-medium ${isPositive ? 'text-green' : 'text-red'}`}>
                        <span className="flex items-center justify-end gap-1">
                          {isPositive ? <TrendingUpIcon size={12} /> : <TrendingDownIcon size={12} />}
                          {formatPercent(p.percent_change, 2)}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono-nums text-text-muted hidden sm:table-cell">
                        {p.volume?.toLocaleString() ?? '\u2014'}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono-nums text-text-muted hidden md:table-cell">
                        {formatTurnover(p.turnover)}
                      </td>
                    </tr>
                  )
                })}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-sm text-text-muted">
                      {search ? `No stocks matching "${search}"` : 'No market data available'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <FloatingChat />
    </PageTransition>
  )
}
