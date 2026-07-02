import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { formatNPR } from '../utils/format'

interface CompanyDetail {
  sector?: string
  market_price?: string
  percent_change?: string
  last_traded_on?: string
  '52w_high'?: string
  '52w_low'?: string
  '52w_range'?: string
  '120d_avg'?: string
  '1y_yield'?: string
  [key: string]: string | undefined
}

interface Props {
  symbol: string
}

function InfoRow({ label, value, className }: { label: string; value: string | undefined | null; className?: string }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between py-1.5 px-3 rounded-lg hover:bg-surface-hover transition-colors">
      <span className="text-xs text-text-muted">{label}</span>
      <span className={`text-xs font-semibold text-text tabular-nums ${className || ''}`}>{value}</span>
    </div>
  )
}

export default function CompanyInfo({ symbol }: Props) {
  const [detail, setDetail] = useState<CompanyDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!symbol) return
    let cancelled = false
    setLoading(true)
    fetch(`/api/stocks/${encodeURIComponent(symbol)}/detail`)
      .then(r => r.json())
      .then(data => { if (!cancelled) setDetail(data) })
      .catch(() => { if (!cancelled) setDetail({}) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [symbol])

  if (loading) {
    return (
      <div className="rounded-xl bg-surface-card border border-border p-4">
        <div className="animate-shimmer h-4 w-24 rounded mb-3" />
        <div className="space-y-1.5">
          {[1, 2, 3, 4, 5, 6, 7].map(i => (
            <div key={i} className="animate-shimmer h-5 rounded" style={{ width: `${90 - i * 5}%` }} />
          ))}
        </div>
      </div>
    )
  }

  if (!detail || Object.keys(detail).length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl bg-surface-card border border-border p-4"
    >
      <h3 className="text-sm font-semibold text-text mb-2">Company Info</h3>
      <div className="space-y-0.5">
        <InfoRow label="Sector" value={detail.sector} />
        <InfoRow label="Market Price" value={detail.market_price ? formatNPR(detail.market_price.replace(/[^0-9.]/g, '')) : undefined} />
        <InfoRow
          label="% Change"
          value={detail.percent_change}
          className={detail.percent_change?.startsWith('-') ? 'text-red' : 'text-green'}
        />
        <InfoRow label="Last Traded On" value={detail.last_traded_on} />
        <InfoRow
          label="52 Week High - Low"
          value={detail['52w_high'] && detail['52w_low']
            ? `${formatNPR(detail['52w_high'].replace(/[^0-9.]/g, ''), 0)} - ${formatNPR(detail['52w_low'].replace(/[^0-9.]/g, ''), 0)}`
            : detail['52w_range']}
        />
        <InfoRow label="120 Day Avg" value={detail['120d_avg'] ? formatNPR(detail['120d_avg'].replace(/[^0-9.]/g, '')) : undefined} />
        <InfoRow
          label="1 Year Yield"
          value={detail['1y_yield']}
          className={detail['1y_yield']?.startsWith('-') ? 'text-red' : 'text-green'}
        />
      </div>
    </motion.div>
  )
}
