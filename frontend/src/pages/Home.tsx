import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import SearchBar from '../components/SearchBar'
import WinnerLoserCard from '../components/WinnerLoserCard'
import MarketSummaryBar from '../components/MarketSummaryBar'
import FloatingChat from '../components/FloatingChat'
import { SkeletonCard } from '../components/Skeleton'
import { useMarketOverview } from '../hooks/useStockData'
import { useMarketStatus } from '../hooks/useMarketStatus'
import { usePageTitle } from '../hooks/usePageTitle'
import { formatTurnover } from '../utils/format'
import { PageTransition } from '../components/Navbar'
import { formatNPR, formatChange } from '../utils/format'
import { WarningIcon, TrendingUpIcon, TrendingDownIcon, ChartIcon, ArrowRightIcon } from '../components/Icons'

function timeAgo(iso: string | null): string {
  if (!iso) return ''
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}


/** Main market overview page with indices, summary, gainers/losers, and chart. */
export default function Home() {
  usePageTitle('Market Overview')
  const navigate = useNavigate()
  const { data, isLoading, error, refetch } = useMarketOverview()
  const marketStatus = useMarketStatus()

  const handleSearch = useCallback((symbol: string) => {
    navigate(`/trade?symbol=${symbol}`)
  }, [navigate])

  const handleStockClick = useCallback((symbol: string) => {
    navigate(`/trade?symbol=${symbol}`)
  }, [navigate])

  return (
    <PageTransition>
      <div className="max-w-5xl mx-auto px-4 py-6 space-y-4">
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-2">
            <TrendingUpIcon size={22} className="text-accent" />
            <h1 className="text-2xl font-bold text-text">Market Overview</h1>
          </div>
          <p className="text-sm text-text-muted">
            Nepal Stock Exchange &mdash; {marketStatus.is_open ? 'Live' : 'Last'} update
          </p>
        </div>

        {data?.indices && data.indices.length > 0 && (
          <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
              <TrendingUpIcon size={16} className="text-accent" />
              <h3 className="text-sm font-semibold text-text">Indices</h3>
            </div>
            <div className="overflow-y-auto max-h-[400px]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface-card">
                  <tr className="border-b border-border text-text-muted text-[11px]">
                    <th className="text-left px-4 py-2 font-medium">Name</th>
                    <th className="text-right px-4 py-2 font-medium">Value</th>
                    <th className="text-right px-4 py-2 font-medium">Change</th>
                    <th className="text-right px-4 py-2 font-medium">% Chg</th>
                  </tr>
                </thead>
                <tbody>
                  {data.indices.map((idx: { name: string; value: number; change: number; percent_change?: number }) => {
                    const isPos = (idx.percent_change ?? idx.change ?? 0) >= 0
                    return (
                      <tr key={idx.name} className="border-b border-border/50 hover:bg-surface-hover/50 transition-colors">
                        <td className="px-4 py-2.5 text-text font-medium text-xs truncate max-w-[160px]">{idx.name}</td>
                        <td className="px-4 py-2.5 text-right font-mono-nums text-text">{formatNPR(idx.value, 2)}</td>
                        <td className={`px-4 py-2.5 text-right font-mono-nums ${isPos ? 'text-green' : 'text-red'}`}>
                          <span className="flex items-center justify-end gap-1">
                            {isPos ? <TrendingUpIcon size={10} /> : <TrendingDownIcon size={10} />}
                            {formatChange(idx.change)}
                          </span>
                        </td>
                        <td className={`px-4 py-2.5 text-right font-mono-nums ${isPos ? 'text-green' : 'text-red'}`}>
                          {idx.percent_change != null ? `${isPos ? '+' : ''}${Number(idx.percent_change).toFixed(2)}%` : '\u2014'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {data?.summary && (
          <MarketSummaryBar
            summary={data.summary}
            lastUpdated={timeAgo(data._fetched_at ?? null) || timeAgo(marketStatus.as_of)}
          />
        )}

        <div className="flex justify-center">
          <SearchBar onSearch={handleSearch} placeholder="Search stock symbol or name..." />
        </div>

        {error && (
          <div className="rounded-xl bg-red/10 border border-red/20 p-4 flex items-start gap-3">
            <WarningIcon size={18} className="text-red shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red">
                Market data currently unavailable. NEPSE may be closed or the data source unreachable.
              </p>
              <button
                onClick={() => refetch()}
                className="mt-2 text-xs text-accent hover:text-accent-hover underline"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <WinnerLoserCard
            title="Top Gainers"
            items={data?.top_gainers || []}
            type="gainers"
            onSelect={handleStockClick}
            loading={isLoading}
          />
          <WinnerLoserCard
            title="Top Losers"
            items={data?.top_losers || []}
            type="losers"
            onSelect={handleStockClick}
            loading={isLoading}
          />
          <WinnerLoserCard
            title="Most Active"
            items={data?.most_active || []}
            type="active"
            onSelect={handleStockClick}
            loading={isLoading}
          />
        </div>

        <div className="text-center">
          <button
            onClick={() => navigate('/market')}
            className="inline-flex items-center gap-1.5 text-xs text-accent hover:text-accent-hover font-medium transition-colors"
          >
            <span>View Full Market</span>
            <ArrowRightIcon size={14} />
          </button>
        </div>

        {data?.sectors && data.sectors.length > 0 && (
          <div className="rounded-xl bg-surface-card border border-border p-4">
            <div className="flex items-center gap-2 mb-3">
              <ChartIcon size={16} className="text-accent" />
              <h3 className="text-sm font-semibold text-text">Sector Turnover</h3>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {data.sectors.slice(0, 10).map((s: { name: string; turnover: number }) => {
                const maxTurnover = Math.max(...(data.sectors ?? []).slice(0, 10).map((x: { turnover: number }) => x.turnover))
                const pct = maxTurnover > 0 ? (s.turnover / maxTurnover) * 100 : 0
                return (
                  <div key={s.name} className="bg-surface-hover rounded-lg p-2">
                    <p className="text-[10px] text-text-muted truncate">{s.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 h-1.5 bg-surface-card rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-medium text-text shrink-0">{formatTurnover(s.turnover)}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <SkeletonCard lines={5} />
            <SkeletonCard lines={5} />
            <SkeletonCard lines={5} />
          </div>
        )}
      </div>
      <FloatingChat />
    </PageTransition>
  )
}
