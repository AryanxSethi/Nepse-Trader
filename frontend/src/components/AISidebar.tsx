import { useState, useEffect, useCallback } from 'react'
import { CompanyIcon, BrainIcon, CloseIcon } from './Icons'
import { fetchCompanies } from '../api/endpoints'
import { POLL } from '../config/constants'

const STORAGE_KEY = 'nepse-watchlist'

function loadWatchlist(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveWatchlist(list: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
}

interface WatchlistPrice {
  symbol: string
  ltp: number | null
  percent_change: number | null
}

interface CompanyEntry {
  symbol: string
  name: string
  ltp?: number | null
  percent_change?: number | null
}

interface Props {
  onSelectSymbol?: (symbol: string) => void
  currentSymbol?: string
}

export default function AISidebar({ onSelectSymbol, currentSymbol }: Props) {
  const [watchlist, setWatchlist] = useState<string[]>(() => loadWatchlist())
  const [prices, setPrices] = useState<Map<string, WatchlistPrice>>(new Map())

  const refreshPrices = useCallback(async () => {
    if (watchlist.length === 0) return
    try {
      const companies: CompanyEntry[] = await fetchCompanies()
      const map = new Map<string, WatchlistPrice>()
      for (const sym of watchlist) {
        const found = companies.find((c) => c.symbol?.toUpperCase() === sym)
        if (found) {
          map.set(sym, {
            symbol: sym,
            ltp: found.ltp ?? null,
            percent_change: found.percent_change ?? null,
          })
        }
      }
      setPrices(map)
    } catch (e) {
      console.warn('Failed to refresh prices', e)
    }
  }, [watchlist])

  useEffect(() => {
    refreshPrices()
    const id = setInterval(refreshPrices, POLL.WATCHLIST)
    return () => clearInterval(id)
  }, [refreshPrices])

  const addSymbol = (sym: string) => {
    const upper = sym.toUpperCase()
    if (watchlist.includes(upper) || watchlist.length >= 5) return
    const next = [...watchlist, upper]
    setWatchlist(next)
    saveWatchlist(next)
  }

  const removeSymbol = (sym: string) => {
    const next = watchlist.filter((s) => s !== sym)
    setWatchlist(next)
    saveWatchlist(next)
  }

  const canAdd = currentSymbol && !watchlist.includes(currentSymbol.toUpperCase()) && watchlist.length < 5

  return (
    <div className="space-y-3">
      <div className="rounded-xl bg-surface-card border border-border p-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-semibold text-text flex items-center gap-1.5">
            <CompanyIcon size={14} className="text-accent" />
            Watchlist
          </h3>
          {canAdd && (
            <button
              onClick={() => addSymbol(currentSymbol!)}
              className="text-[10px] text-accent hover:text-accent-hover font-medium transition-colors"
            >
              + Add
            </button>
          )}
        </div>
        {watchlist.length === 0 ? (
          <p className="text-[10px] text-text-muted">Search a stock and add it to your watchlist (max 5)</p>
        ) : (
          <div className="space-y-1">
            {watchlist.map((sym) => {
              const p = prices.get(sym)
              return (
                <div key={sym} className="flex items-center justify-between py-1 group">
                  <button
                    onClick={() => onSelectSymbol?.(sym)}
                    className="text-xs text-text hover:text-accent transition-colors font-medium"
                  >
                    {sym}
                  </button>
                  <div className="flex items-center gap-2">
                    {p ? (
                      <>
                        <span className="text-[11px] text-text-muted font-mono-nums">
                          {p.ltp != null ? p.ltp.toFixed(2) : '\u2014'}
                        </span>
                        {p.percent_change != null && (
                          <span className={`text-[11px] font-medium font-mono-nums ${p.percent_change >= 0 ? 'text-green' : 'text-red'}`}>
                            {p.percent_change >= 0 ? '+' : ''}{p.percent_change.toFixed(1)}%
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-[11px] text-text-muted">...</span>
                    )}
                    <button
                      onClick={() => removeSymbol(sym)}
                      className="text-text-muted/30 hover:text-red transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <CloseIcon size={12} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div className="rounded-xl bg-surface-card border border-border p-3">
        <h3 className="text-xs font-semibold text-text mb-2 flex items-center gap-1.5">
          <BrainIcon size={14} className="text-accent" />
          Tips
        </h3>
        <ul className="text-[10px] text-text-muted space-y-1">
          <li>Type "NABIL past 1 year" for custom date ranges</li>
          <li>Ask "Compare NABIL and SCB" for side-by-side analysis</li>
          <li>Typo-tolerant search — "nabl" finds NABIL</li>
        </ul>
      </div>
    </div>
  )
}
