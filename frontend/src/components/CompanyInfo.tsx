import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { formatNPR } from '../utils/format'
import { fetchStockDetail } from '../api/endpoints'
import { SkeletonCompanyInfo } from './Skeleton'

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
  vwap?: string
  prev_close?: string
  volume?: string
  '180d_avg'?: string
  confidence_score?: string
  pivot_s3?: string
  pivot_s2?: string
  pivot_s1?: string
  pivot_pp?: string
  pivot_r1?: string
  pivot_r2?: string
  pivot_r3?: string
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

/** Displays detailed company fundamentals, price stats, and pivot levels. */
export default function CompanyInfo({ symbol }: Props) {
  const [detail, setDetail] = useState<CompanyDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [pivotOpen, setPivotOpen] = useState(false)

  useEffect(() => {
    if (!symbol) return
    const controller = new AbortController()
    setLoading(true)
    fetchStockDetail(symbol, { signal: controller.signal })
      .then(data => setDetail(data))
      .catch(() => setDetail({}))
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [symbol])

  if (loading) return <SkeletonCompanyInfo />

  if (!detail || Object.keys(detail).length === 0) return null

  const hasVwap = detail.vwap && detail.market_price
  const vwapDiff = hasVwap
    ? parseFloat(detail.market_price!.replace(/[^0-9.]/g, '')) - parseFloat(detail.vwap!.replace(/[^0-9.]/g, ''))
    : null
  const vwapLabel = vwapDiff != null ? (vwapDiff < 0 ? 'BELOW' : 'ABOVE') : null
  const vwapClass = vwapDiff != null ? (vwapDiff < 0 ? 'text-green' : 'text-red') : ''

  const hasPivot = detail.pivot_s3 || detail.pivot_s2 || detail.pivot_s1 || detail.pivot_pp
  const pivotLevels = hasPivot ? [
    { label: 'R3', key: 'pivot_r3' },
    { label: 'R2', key: 'pivot_r2' },
    { label: 'R1', key: 'pivot_r1' },
    { label: 'PP', key: 'pivot_pp' },
    { label: 'S1', key: 'pivot_s1' },
    { label: 'S2', key: 'pivot_s2' },
    { label: 'S3', key: 'pivot_s3' },
  ] : []

  const mktPrice = detail.market_price ? parseFloat(detail.market_price.replace(/[^0-9.]/g, '')) : null

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
        <div className="border-t border-border/40 my-1.5" />
        {detail.vwap && (
          <InfoRow
            label="VWAP"
            value={`${formatNPR(detail.vwap.replace(/[^0-9.]/g, ''))}${vwapLabel ? `  [${vwapLabel}]` : ''}`}
            className={vwapClass}
          />
        )}
        <InfoRow label="Previous Close" value={detail.prev_close ? formatNPR(detail.prev_close.replace(/[^0-9.]/g, '')) : undefined} />
        <InfoRow label="180 Day Avg" value={detail['180d_avg'] ? formatNPR(detail['180d_avg'].replace(/[^0-9.]/g, '')) : undefined} />
        {detail.volume && (
          <InfoRow label="Volume" value={(() => {
            const parsed = parseInt(detail.volume.replace(/[^0-9]/g, ''))
            return isNaN(parsed) ? detail.volume : parsed.toLocaleString()
          })()} />
        )}
        {detail.confidence_score && (
          <InfoRow
            label="Confidence"
            value={detail.confidence_score}
            className={detail.confidence_score === 'High' ? 'text-green' : detail.confidence_score === 'Low' ? 'text-red' : 'text-yellow'}
          />
        )}
      </div>

      {hasPivot && (
        <>
          <button
            onClick={() => setPivotOpen(!pivotOpen)}
            className="w-full flex items-center justify-between mt-2 px-3 py-2 rounded-lg hover:bg-surface-hover transition-colors text-xs font-medium text-text-muted"
          >
            <span>Pivot Analysis</span>
            <span className={`transition-transform ${pivotOpen ? 'rotate-180' : ''}`}>▾</span>
          </button>
          <AnimatePresence>
            {pivotOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="space-y-0.5 pt-1">
                  {pivotLevels.map(({ label, key }) => {
                    const val = detail[key]
                    if (!val) return null
                    const numVal = parseFloat(val.replace(/[^0-9.]/g, ''))
                    const isNear = mktPrice != null && numVal > 0
                      && Math.abs(mktPrice - numVal) / numVal < 0.005
                    return (
                      <div
                        key={key}
                        className={`flex items-center justify-between py-1 px-3 rounded-lg text-xs ${
                          isNear ? 'bg-accent/10 ring-1 ring-accent/30' : 'hover:bg-surface-hover'
                        } transition-colors`}
                      >
                        <span className="text-text-muted font-medium">{label}</span>
                        <span className={`font-semibold tabular-nums ${
                          label.startsWith('R') ? 'text-green' : label.startsWith('S') ? 'text-red' : 'text-accent'
                        }`}>
                          {formatNPR(numVal)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </motion.div>
  )
}
