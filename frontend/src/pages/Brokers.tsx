import { useState, useEffect, useCallback } from 'react'
import { PageTransition } from '../components/Navbar'
import { SearchIcon, CompanyIcon, WarningIcon } from '../components/Icons'
import { SkeletonBlock } from '../components/Skeleton'
import type { BrokerDetail } from '../types'

interface BrokerData {
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

function formatTurnover(n: number): string {
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`
  if (n >= 1e7) return `${(n / 1e7).toFixed(2)}Cr`
  if (n >= 1e5) return `${(n / 1e5).toFixed(2)}L`
  return n.toLocaleString()
}

export default function Brokers() {
  const [brokers, setBrokers] = useState<BrokerData[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [period, setPeriod] = useState<'daily' | 'weekly' | 'monthly'>('monthly')
  const [fetchError, setFetchError] = useState('')

  const fetchBrokers = useCallback(async (q: string, p: string) => {
    setLoading(true)
    setFetchError('')
    try {
      if (q) {
        const res = await fetch(`/api/brokers/search?q=${encodeURIComponent(q)}`)
        if (!res.ok) throw new Error(`API error: ${res.status}`)
        const data = await res.json()
        setBrokers((data.brokers || []).map((b: BrokerDetail, i: number) => ({ ...b, rank: i + 1 })))
      } else {
        const res = await fetch(`/api/brokers/top?period=${p}&limit=50`)
        if (!res.ok) throw new Error(`API error: ${res.status}`)
        const data = await res.json()
        setBrokers(data.brokers || [])
      }
    } catch (e) {
      console.error('Brokers fetch failed:', e)
      setFetchError(e instanceof Error ? e.message : 'Failed to load broker data')
      setBrokers([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchBrokers(query, period), 200)
    return () => clearTimeout(t)
  }, [query, period, fetchBrokers])

  const turnoverKey = period === 'daily' ? 'latest_turnover' : 'thirty_days_turnover'
  const turnoverLabel = period === 'daily' ? 'Today' : period === 'weekly' ? 'Weekly Avg' : '30-Day'
  const rankLabel = period === 'daily' ? 'Today' : period === 'weekly' ? 'This Week' : 'This Month'
  const periods: { key: 'daily' | 'weekly' | 'monthly'; label: string }[] = [
    { key: 'daily', label: 'Daily' },
    { key: 'weekly', label: 'Weekly' },
    { key: 'monthly', label: 'Monthly' },
  ]

  return (
    <PageTransition>
      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        <div className="flex items-center gap-3">
          <CompanyIcon size={22} className="text-accent" />
          <div>
            <h1 className="text-2xl font-bold text-text">Brokers</h1>
            <p className="text-sm text-text-muted">92 NEPSE member brokers</p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
          <div className="relative flex-1 max-w-md">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, broker code, or district..."
              className="w-full bg-surface-card text-text text-sm rounded-lg pl-9 pr-4 py-2.5 border border-border outline-none focus:border-accent/50 transition-colors placeholder-text-muted/40"
            />
            <SearchIcon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          </div>
          <div className="flex items-center gap-1 bg-surface-card border border-border rounded-lg p-0.5">
            {periods.map((p) => (
              <button
                key={p.key}
                onClick={() => setPeriod(p.key)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  period === p.key ? 'bg-accent text-white' : 'text-text-muted hover:text-text'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {fetchError && (
          <div className="rounded-xl bg-red/10 border border-red/20 p-4 flex items-start gap-3">
            <WarningIcon size={18} className="text-red shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red">Failed to load broker data</p>
              <p className="text-xs text-red/70 mt-0.5">{fetchError}</p>
              <button
                onClick={() => fetchBrokers(query, period)}
                className="mt-2 text-xs text-accent hover:text-accent-hover underline"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <SkeletonBlock key={i} height={48} />
            ))}
          </div>
        ) : brokers.length === 0 && !fetchError ? (
          <div className="rounded-xl bg-surface-card border border-border flex items-center justify-center h-48">
            <p className="text-sm text-text-muted">No brokers found</p>
          </div>
        ) : (
          <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-hover/50">
                  <tr className="border-b border-border text-text-muted text-xs">
                    <th className="text-left px-4 py-3 font-medium w-12">{rankLabel} Rank</th>
                    <th className="text-left px-4 py-3 font-medium">#</th>
                    <th className="text-left px-4 py-3 font-medium">Broker Name</th>
                    <th className="text-left px-4 py-3 font-medium">Districts</th>
                    <th className="text-right px-4 py-3 font-medium">{turnoverLabel} Turnover</th>
                    <th className="text-center px-4 py-3 font-medium">Branches</th>
                    <th className="text-center px-4 py-3 font-medium">Status</th>
                    <th className="text-center px-4 py-3 font-medium">TMS</th>
                  </tr>
                </thead>
                <tbody>
                  {brokers.map((b) => {
                    const isTop3 = b.rank <= 3 && !query
                    const rankDisplay = b.rank === 1 ? '#1' : b.rank === 2 ? '#2' : b.rank === 3 ? '#3' : `#${b.rank}`
                    return (
                      <tr
                        key={b.code}
                        className={`border-b border-border/50 hover:bg-surface-hover/50 transition-colors ${
                          isTop3 ? 'bg-yellow/5' : ''
                        }`}
                      >
                        <td className={`px-4 py-3 font-mono-nums text-xs ${isTop3 ? 'text-yellow font-bold' : 'text-text'}`}>
                          {rankDisplay}
                        </td>
                        <td className="px-4 py-3 text-text-muted font-mono-nums">{b.code}</td>
                        <td className="px-4 py-3 text-text font-medium">{b.name}</td>
                        <td className="px-4 py-3 text-text-muted text-xs">
                          {b.districts?.slice(0, 3).join(', ')}{b.districts?.length > 3 ? ` +${b.districts.length - 3}` : ''}
                        </td>
                        <td className="px-4 py-3 text-right text-text font-mono-nums text-xs font-medium">
                          Rs {formatTurnover((b as any)[turnoverKey] || 0)}
                        </td>
                        <td className="px-4 py-3 text-center text-text-muted text-xs">{b.branch_count}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            b.active_status === 'A' ? 'bg-green/15 text-green' : 'bg-red/10 text-red'
                          }`}>
                            {b.active_status === 'A' ? 'Active' : 'Suspended'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {b.tms_link && (
                            <a
                              href={`https://${b.tms_link}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[10px] text-accent hover:text-accent-hover underline"
                            >
                              TMS
                            </a>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  )
}
