import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { PageTransition } from '../components/Navbar'
import FloatingChat from '../components/FloatingChat'
import ErrorBanner from '../components/ErrorBanner'
import RefreshIndicator from '../components/RefreshIndicator'
import SymbolSearchInput from '../components/SymbolSearchInput'
import { formatNPR, formatPercent, formatChange } from '../utils/format'
import { fetchPortfolio, addHolding, deleteHolding } from '../api/endpoints'
import type { PortfolioHolding } from '../api/endpoints'
import { usePageTitle } from '../hooks/usePageTitle'
import { POLL } from '../config/constants'
import {
  TrendingUpIcon, TrendingDownIcon, CloseIcon,
} from '../components/Icons'

interface PortfolioData {
  holdings: (PortfolioHolding & { name?: string })[]
  total_invested: number
  total_value: number
  total_pl: number
  total_pl_percent: number
}

function AddHoldingModal({ onClose, onAdded }: { onClose: () => void; onAdded: () => void }) {
  const [symbol, setSymbol] = useState('')
  const [quantity, setQuantity] = useState('')
  const [avgCost, setAvgCost] = useState('')
  const [buyDate, setBuyDate] = useState(new Date().toISOString().split('T')[0])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    setError('')
    if (!symbol || !quantity || !avgCost) {
      setError('Symbol, quantity, and avg cost are required')
      return
    }
    const qty = parseInt(quantity)
    const cost = parseFloat(avgCost)
    if (qty <= 0 || cost <= 0) {
      setError('Quantity and avg cost must be positive')
      return
    }
    setSubmitting(true)
    try {
      await addHolding(symbol.trim().toUpperCase(), qty, cost, buyDate)
      onAdded()
      onClose()
      toast.success('Holding added')
    } catch (e: any) {
      setError(e.message || 'Failed to add holding')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-surface-card border border-border rounded-xl p-5 w-full max-w-sm mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-text">Add Holding</h3>
          <button onClick={onClose} className="text-text-muted hover:text-text"><CloseIcon size={16} /></button>
        </div>
        <div className="space-y-3">
          <SymbolSearchInput onSelect={setSymbol} value={symbol} placeholder="Symbol (e.g. NABIL)" />
          <input
            type="number"
            placeholder="Quantity"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-full bg-surface-hover text-text text-sm rounded-lg px-3 py-2 border border-border outline-none"
          />
          <input
            type="number"
            step="0.01"
            placeholder="Avg Cost (NPR)"
            value={avgCost}
            onChange={(e) => setAvgCost(e.target.value)}
            className="w-full bg-surface-hover text-text text-sm rounded-lg px-3 py-2 border border-border outline-none"
          />
          <input
            type="date"
            value={buyDate}
            onChange={(e) => setBuyDate(e.target.value)}
            className="w-full bg-surface-hover text-text text-sm rounded-lg px-3 py-2 border border-border outline-none"
          />
          {error && <p className="text-xs text-red">{error}</p>}
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="w-full bg-accent text-white text-sm font-medium rounded-lg py-2 hover:bg-accent/90 disabled:opacity-50"
          >
            {submitting ? 'Adding...' : 'Add'}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

/** User portfolio with holdings, P&L tracking, and add/remove functionality. */
export default function Portfolio() {
  usePageTitle('Portfolio')
  const [data, setData] = useState<PortfolioData | null>(null)
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [fetchedAt, setFetchedAt] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)

  const loadPortfolio = useCallback(async () => {
    try {
      const resp = await fetchPortfolio()
      setData({
        holdings: resp.holdings,
        total_invested: resp.total_invested,
        total_value: resp.total_value,
        total_pl: resp.total_pl,
        total_pl_percent: resp.total_pl_percent,
      })
      setFetchedAt(new Date().toISOString())
      setError(null)
    } catch {
      setError('Failed to load portfolio data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPortfolio()
    const id = setInterval(loadPortfolio, POLL.PORTFOLIO)
    return () => clearInterval(id)
  }, [loadPortfolio])

  const handleDelete = async (id: number) => {
    try {
      await deleteHolding(id)
      setDeleteError(null)
      setConfirmDelete(null)
      loadPortfolio()
      toast.success('Holding removed')
    } catch {
      toast.error('Failed to delete holding')
    }
  }

  if (loading) {
    return (
      <PageTransition>
        <div className="max-w-5xl mx-auto px-4 py-6 space-y-4">
          <div className="animate-shimmer h-8 w-32 rounded" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map(i => <div key={i} className="animate-shimmer h-20 rounded-xl" />)}
          </div>
          <div className="animate-shimmer h-64 rounded-xl" />
        </div>
      </PageTransition>
    )
  }

  const isPositive = (data?.total_pl ?? 0) >= 0

  return (
    <PageTransition>
      <div className="max-w-5xl mx-auto px-4 py-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-text">Portfolio</h1>
            <RefreshIndicator fetchedAt={fetchedAt} />
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="bg-accent text-white text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-accent/90"
          >
            + Add Holding
          </button>
        </div>

        {error && (
          <ErrorBanner message={error} onRetry={() => { setLoading(true); loadPortfolio() }} onDismiss={() => setError(null)} />
        )}
        {deleteError && (
          <ErrorBanner message={deleteError} onDismiss={() => setDeleteError(null)} />
        )}

        {/* Summary bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-xl bg-surface-card border border-border p-3">
            <p className="text-[11px] text-text-muted">Total Invested</p>
            <p className="text-lg font-bold text-text">{formatNPR(data?.total_invested)}</p>
          </div>
          <div className="rounded-xl bg-surface-card border border-border p-3">
            <p className="text-[11px] text-text-muted">Current Value</p>
            <p className="text-lg font-bold text-text">{formatNPR(data?.total_value)}</p>
          </div>
          <div className="rounded-xl bg-surface-card border border-border p-3">
            <p className="text-[11px] text-text-muted">Total P&amp;L</p>
            <p className={`text-lg font-bold ${isPositive ? 'text-green' : 'text-red'}`}>
              {formatChange(data?.total_pl)}
            </p>
            <p className={`text-xs ${isPositive ? 'text-green' : 'text-red'}`}>
              {formatPercent(data?.total_pl_percent)}
            </p>
          </div>
          <div className="rounded-xl bg-surface-card border border-border p-3">
            <p className="text-[11px] text-text-muted">Holdings</p>
            <p className="text-lg font-bold text-text">{data?.holdings.length ?? 0}</p>
          </div>
        </div>

        {/* Holdings table */}
        <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs">
                  <th className="text-left px-4 py-3 font-medium">Symbol</th>
                  <th className="text-right px-4 py-3 font-medium">Qty</th>
                  <th className="text-right px-4 py-3 font-medium">Avg Cost</th>
                  <th className="text-right px-4 py-3 font-medium">Invested</th>
                  <th className="text-right px-4 py-3 font-medium">LTP</th>
                  <th className="text-right px-4 py-3 font-medium">Value</th>
                  <th className="text-right px-4 py-3 font-medium">P&amp;L</th>
                  <th className="text-right px-4 py-3 font-medium">P&amp;L%</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {(data?.holdings ?? []).length === 0 && (
                  <tr>
                    <td colSpan={9} className="text-center text-text-muted text-sm py-8">
                      No holdings yet. Add your first stock.
                    </td>
                  </tr>
                )}
                {(data?.holdings ?? []).map((h, i) => {
                  const plPos = (h.pnl ?? 0) >= 0
                  return (
                    <motion.tr
                      key={h.id}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.02 }}
                      className="border-b border-border/50 hover:bg-surface-hover/50 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <span className="font-medium text-text">{h.symbol}</span>
                        {h.name && <p className="text-[10px] text-text-muted truncate max-w-[120px]">{h.name}</p>}
                      </td>
                      <td className="px-4 py-3 text-right font-mono-nums text-text">{h.quantity}</td>
                      <td className="px-4 py-3 text-right font-mono-nums text-text-muted">{formatNPR(h.avg_cost)}</td>
                      <td className="px-4 py-3 text-right font-mono-nums text-text-muted">{formatNPR(h.invested)}</td>
                      <td className="px-4 py-3 text-right font-mono-nums text-text">{formatNPR(h.ltp)}</td>
                      <td className="px-4 py-3 text-right font-mono-nums text-text">{formatNPR(h.current_value)}</td>
                      <td className={`px-4 py-3 text-right font-mono-nums font-medium ${plPos ? 'text-green' : 'text-red'}`}>
                        <span className="flex items-center justify-end gap-1">
                          {h.pnl != null && (plPos ? <TrendingUpIcon size={12} /> : <TrendingDownIcon size={12} />)}
                          {formatChange(h.pnl)}
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-right font-mono-nums font-medium ${plPos ? 'text-green' : 'text-red'}`}>
                        {formatPercent(h.pnl != null && h.invested > 0 ? (h.pnl / h.invested) * 100 : null)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {confirmDelete === h.id ? (
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] text-red">Sure?</span>
                            <button
                              onClick={() => handleDelete(h.id)}
                              className="text-xs text-red font-medium hover:text-red/80 transition-colors"
                            >
                              Yes
                            </button>
                            <button
                              onClick={() => setConfirmDelete(null)}
                              className="text-xs text-text-muted hover:text-text transition-colors"
                            >
                              No
                            </button>
                          </div>
                        ) : (
                          <button
                          onClick={() => setConfirmDelete(h.id)}
                          className="text-text-muted hover:text-red transition-colors"
                          title="Remove"
                        >
                          <CloseIcon size={14} />
                        </button>
                        )}
                      </td>
                    </motion.tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        <p className="text-[10px] text-text-muted/40 text-center">
          Holdings update every 30s with live LTP. The stock market involves risk.
        </p>
      </div>
      {showAdd && (
        <AddHoldingModal
          onClose={() => setShowAdd(false)}
          onAdded={loadPortfolio}
        />
      )}
      <FloatingChat />
    </PageTransition>
  )
}
