import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { TableIcon, WarningIcon } from './Icons'

interface FloorsheetRow {
  contract_no: string
  buyer: string
  seller: string
  quantity: number | null
  rate: number | null
  amount: number | null
}

interface Props {
  symbol: string
}

export default function FloorsheetPanel({ symbol }: Props) {
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState<FloorsheetRow[]>([])
  const [loading, setLoading] = useState(false)
  const [fetchError, setFetchError] = useState('')

  useEffect(() => {
    if (!open || !symbol) { setRows([]); return }
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 10000)
    setRows([])
    setLoading(true)
    setFetchError('')
    fetch(`/api/stocks/${encodeURIComponent(symbol)}/floorsheet`, { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error(`API error ${r.status}`); return r.json() })
      .then(data => setRows(data.floorsheet || []))
      .catch((e) => {
        if (e.name === 'AbortError') return
        setFetchError(e.message || 'Failed to load floorsheet')
      })
      .finally(() => { clearTimeout(timeout); setLoading(false) })
    return () => { controller.abort(); clearTimeout(timeout) }
  }, [open, symbol])

  return (
    <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <TableIcon size={16} className="text-accent" />
          <span className="text-sm font-medium text-text">Floorsheet</span>
          {rows.length > 0 && (
            <span className="text-[10px] text-text-muted">({rows.length} transactions)</span>
          )}
        </div>
        <span className={`text-text-muted text-xs transition-transform ${open ? 'rotate-180' : ''}`}>▾</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-4 pb-3"
          >
            {loading && (
              <div className="animate-pulse space-y-2 py-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-6 bg-surface-hover rounded" style={{ width: `${80 - i * 10}%` }} />
                ))}
              </div>
            )}

            {!loading && fetchError && (
              <div className="flex items-start gap-2 py-2">
                <WarningIcon size={14} className="text-red shrink-0 mt-0.5" />
                <p className="text-xs text-red">{fetchError}</p>
              </div>
            )}

            {!loading && !fetchError && rows.length === 0 && (
              <div className="flex items-start gap-2 py-2">
                <WarningIcon size={14} className="text-yellow shrink-0 mt-0.5" />
                <p className="text-xs text-text-muted">No floorsheet data available for {symbol}</p>
              </div>
            )}

            {!loading && rows.length > 0 && (
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="bg-surface-hover border-b border-border">
                      <th className="text-left py-1.5 px-2 text-text-muted font-medium">#</th>
                      <th className="text-left py-1.5 px-2 text-text-muted font-medium">Buyer</th>
                      <th className="text-left py-1.5 px-2 text-text-muted font-medium">Seller</th>
                      <th className="text-right py-1.5 px-2 text-text-muted font-medium">Qty</th>
                      <th className="text-right py-1.5 px-2 text-text-muted font-medium">Rate</th>
                      <th className="text-right py-1.5 px-2 text-text-muted font-medium">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr key={i} className="border-b border-border/50 hover:bg-surface-hover/50 transition-colors">
                        <td className="py-1.5 px-2 text-text-muted">{i + 1}</td>
                        <td className="py-1.5 px-2 text-text font-medium">{row.buyer}</td>
                        <td className="py-1.5 px-2 text-text">{row.seller}</td>
                        <td className="py-1.5 px-2 text-right font-mono-nums text-text">{row.quantity?.toLocaleString() ?? '\u2014'}</td>
                        <td className="py-1.5 px-2 text-right font-mono-nums text-text">{row.rate != null ? `Rs ${row.rate.toFixed(2)}` : '\u2014'}</td>
                        <td className="py-1.5 px-2 text-right font-mono-nums text-text">{row.amount != null ? `Rs ${row.amount.toLocaleString()}` : '\u2014'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
