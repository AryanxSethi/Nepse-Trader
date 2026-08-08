import { useState, useEffect } from 'react'
import SearchBar from './SearchBar'
import StockChart from './StockChart'
import { SkeletonBlock } from './Skeleton'
import { WarningIcon, CompareIcon, CloseIcon } from './Icons'
import { formatNPR } from '../utils/format'
import { fetchCompare } from '../api/endpoints'
import { NetworkError, TimeoutError } from '../api/client'
import type { CompareItem } from '../api/endpoints'
import type { PricePoint } from '../types'


function toNum(v: unknown): number | null {
  if (v == null) return null
  if (typeof v === 'number') return isNaN(v) ? null : v
  if (typeof v === 'string') {
    const n = parseFloat(v.replace(/[^0-9.-]/g, ''))
    return isNaN(n) ? null : n
  }
  return null
}

function formatNum(n: unknown): string {
  const num = toNum(n)
  if (num == null) return '\u2014'
  if (num >= 1e9) return `${(num / 1e9).toFixed(2)}B`
  if (num >= 1e7) return `${(num / 1e7).toFixed(2)}Cr`
  if (num >= 1e5) return `${(num / 1e5).toFixed(2)}L`
  return num.toLocaleString()
}

function formatPrice(n: unknown): string {
  const num = toNum(n)
  if (num == null) return '\u2014'
  return formatNPR(num)
}

function cellClass(value: unknown, key: string) {
  if (key === 'percent_change') {
    const num = toNum(value)
    if (num != null) return num >= 0 ? 'text-green' : 'text-red'
  }
  if (key === 'signal_type' && typeof value === 'string') {
    if (value === 'BUY') return 'text-green font-semibold'
    if (value === 'SELL') return 'text-red font-semibold'
    return 'text-yellow font-semibold'
  }
  return 'text-text font-mono-nums'
}

function getValue(item: CompareItem, key: string) {
  return (item as unknown as Record<string, unknown>)[key] ?? null
}

const METRICS: { label: string; key: string; fmt: (v: unknown) => string }[] = [
  { label: 'LTP', key: 'ltp', fmt: (v: unknown) => formatPrice(v) },
  { label: 'Change %', key: 'percent_change', fmt: (v: unknown) => {
    const num = toNum(v)
    return num != null ? `${num >= 0 ? '+' : ''}${num.toFixed(2)}%` : '\u2014'
  } },
  { label: 'Volume', key: 'volume', fmt: (v: unknown) => {
    const num = toNum(v)
    return num != null ? num.toLocaleString() : '\u2014'
  } },
  { label: 'Turnover', key: 'turnover', fmt: formatNum },
  { label: 'Market Cap', key: 'market_cap', fmt: formatNum },
  { label: 'RSI', key: 'rsi', fmt: (v: unknown) => {
    const num = toNum(v)
    return num != null ? num.toFixed(2) : '\u2014'
  } },
  { label: 'MACD', key: 'macd', fmt: (v: unknown) => {
    const num = toNum(v)
    return num != null ? num.toFixed(2) : '\u2014'
  } },
  { label: 'MACD Signal', key: 'macd_signal', fmt: (v: unknown) => {
    const num = toNum(v)
    return num != null ? num.toFixed(2) : '\u2014'
  } },
  { label: 'SMA20', key: 'sma20', fmt: (v: unknown) => {
    const num = toNum(v)
    return num != null ? num.toFixed(2) : '\u2014'
  } },
  { label: 'SMA50', key: 'sma50', fmt: (v: unknown) => {
    const num = toNum(v)
    return num != null ? num.toFixed(2) : '\u2014'
  } },
  { label: 'ADX', key: 'adx', fmt: (v: unknown) => {
    const num = toNum(v)
    return num != null ? num.toFixed(2) : '\u2014'
  } },
  { label: 'Signal', key: 'signal_type', fmt: (v: unknown) => (typeof v === 'string' && v) || '\u2014' },
  { label: 'Confidence', key: 'signal_confidence', fmt: (v: unknown) => {
    const num = toNum(v)
    return num != null ? `${num}%` : '\u2014'
  } },
]

/** Side-by-side comparison of two stocks with metrics table and charts. */
export default function ComparePanel({ initialSymbols }: { initialSymbols?: string[] | null }) {
  const [symbol1, setSymbol1] = useState(initialSymbols?.[0] || '')
  const [symbol2, setSymbol2] = useState(initialSymbols?.[1] || '')
  const [data, setData] = useState<CompareItem[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (!(symbol1 && symbol2)) {
      setData(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    setData(null)
    const controller = new AbortController()
    fetchCompare([symbol1, symbol2], { signal: controller.signal })
      .then((d) => {
        setData(d.comparison || [])
        setError('')
        setLoading(false)
      })
      .catch((e) => {
        if (e instanceof DOMException && e.name === 'AbortError') return
        if (e instanceof NetworkError || e instanceof TimeoutError) {
          setError(e.message)
        } else {
          setError('Compare data unavailable. Please try again.')
        }
        setLoading(false)
      })
    return () => controller.abort()
  }, [symbol1, symbol2, reloadKey])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <CompareIcon size={16} className="text-accent" />
        <h3 className="text-sm font-semibold text-text">Compare Stocks</h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <p className="text-[10px] text-text-muted mb-1">Stock 1</p>
          <SearchBar
            onSearch={(sym) => { setSymbol1(sym.toUpperCase()); setError('') }}
            placeholder="NABIL, SCB, ..."
          />
          {symbol1 && (
            <div className="mt-1.5 inline-flex items-center gap-1.5 bg-accent/10 text-accent text-[11px] font-medium px-2.5 py-1 rounded-full">
              <span>{symbol1}</span>
              <button onClick={() => setSymbol1('')} className="hover:text-accent-hover transition-colors">
                <CloseIcon size={12} />
              </button>
            </div>
          )}
        </div>
        <div>
          <p className="text-[10px] text-text-muted mb-1">Stock 2</p>
          <SearchBar
            onSearch={(sym) => { setSymbol2(sym.toUpperCase()); setError('') }}
            placeholder="NABIL, SCB, ..."
          />
          {symbol2 && (
            <div className="mt-1.5 inline-flex items-center gap-1.5 bg-accent/10 text-accent text-[11px] font-medium px-2.5 py-1 rounded-full">
              <span>{symbol2}</span>
              <button onClick={() => setSymbol2('')} className="hover:text-accent-hover transition-colors">
                <CloseIcon size={12} />
              </button>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red/10 border border-red/20 p-3 flex items-start gap-2">
          <WarningIcon size={14} className="text-red shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-xs text-red">{error}</p>
            <button
              onClick={() => setReloadKey((k) => k + 1)}
              className="mt-2 text-xs text-accent hover:text-accent-hover underline"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {loading && (
        <div className="space-y-2">
          <SkeletonBlock height={200} />
        </div>
      )}

      {data && data.length >= 2 && !loading && (
        <div className="space-y-6">
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-surface-hover border-b border-border">
                  <th className="text-left py-2 px-3 text-text-muted font-medium">Metric</th>
                  <th className="text-right py-2 px-3 text-text font-semibold">{data[0].symbol}</th>
                  <th className="text-right py-2 px-3 text-text font-semibold">{data[1].symbol}</th>
                </tr>
              </thead>
              <tbody>
                {METRICS.map((m, i) => (
                  <tr key={m.key} className={`border-b border-border/50 ${i % 2 === 0 ? 'bg-surface-card' : 'bg-surface-card/50'}`}>
                    <td className="py-2 px-3 text-text-muted">{m.label}</td>
                    <td className={`py-2 px-3 text-right ${cellClass(getValue(data[0], m.key), m.key)}`}>
                      {m.fmt(getValue(data[0], m.key))}
                    </td>
                    <td className={`py-2 px-3 text-right ${cellClass(getValue(data[1], m.key), m.key)}`}>
                      {m.fmt(getValue(data[1], m.key))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data[0].prices && data[0].prices.length >= 2 && (
            <div className="rounded-xl bg-surface-card border border-border p-4">
              <h4 className="text-xs font-semibold text-text mb-3">{data[0].symbol} — Price Chart</h4>
              <StockChart data={data[0].prices.map(p => ({ ...p, symbol: data[0].symbol, open: p.close, high: p.close, low: p.close, volume: 0 })) as PricePoint[]} height={300} />
            </div>
          )}

          {data[1].prices && data[1].prices.length >= 2 && (
            <div className="rounded-xl bg-surface-card border border-border p-4">
              <h4 className="text-xs font-semibold text-text mb-3">{data[1].symbol} — Price Chart</h4>
              <StockChart data={data[1].prices.map(p => ({ ...p, symbol: data[1].symbol, open: p.close, high: p.close, low: p.close, volume: 0 })) as PricePoint[]} height={300} />
            </div>
          )}
        </div>
      )}

      {!symbol1 && !symbol2 && !loading && (
        <div className="rounded-xl bg-surface-card border border-border flex items-center justify-center h-32">
          <p className="text-xs text-text-muted">Select two stocks to compare</p>
        </div>
      )}

      {data && data.length >= 2 && !loading && (
        <div className="rounded-lg bg-yellow/10 border border-yellow/20 p-2 flex items-start gap-1.5">
          <WarningIcon size={12} className="text-yellow shrink-0 mt-0.5" />
          <p className="text-[10px] text-yellow font-medium">
            Signal and confidence values are AI-generated and may be inaccurate.
          </p>
        </div>
      )}
    </div>
  )
}
