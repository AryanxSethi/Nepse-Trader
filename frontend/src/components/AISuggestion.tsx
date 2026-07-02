import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BrainIcon, ArrowUpIcon, ArrowDownIcon, InfoIcon } from './Icons'

interface Props {
  signal?: { type: string; confidence: number; reason: string } | null
  indicators?: Record<string, number | string>
}

export default function AISuggestion({ signal, indicators }: Props) {
  const [open, setOpen] = useState(false)

  if (!indicators && !signal) {
    return (
      <div className="rounded-xl bg-surface-card border border-border p-3">
        <p className="text-xs text-text-muted">Analysis available when you select a stock with sufficient data.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <BrainIcon size={16} className="text-accent" />
          <span className="text-sm font-medium text-text">Analysis</span>
          {signal && (
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
              signal.type === 'BUY' ? 'bg-green/15 text-green' :
              signal.type === 'SELL' ? 'bg-red/15 text-red' :
              'bg-yellow/15 text-yellow'
            }`}>
              {signal.type} ({signal.confidence}%)
            </span>
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
            className="px-4 pb-3 space-y-2"
          >
            {indicators && (
              <div className="grid grid-cols-3 gap-2 text-xs">
                {indicators.rsi != null && (
                  <div className="bg-surface-hover rounded-lg p-2">
                    <span className="text-text-muted">RSI</span>
                    <p className="text-text font-medium">{indicators.rsi}</p>
                  </div>
                )}
                {indicators.trend != null && (
                  <div className="bg-surface-hover rounded-lg p-2">
                    <span className="text-text-muted">Trend</span>
                    <p className={`font-medium flex items-center gap-1 ${
                      indicators.trend === 'uptrend' ? 'text-green' :
                      indicators.trend === 'downtrend' ? 'text-red' : 'text-yellow'
                    }`}>
                      {indicators.trend === 'uptrend' ? <ArrowUpIcon size={12} /> :
                       indicators.trend === 'downtrend' ? <ArrowDownIcon size={12} /> : null}
                      {indicators.trend === 'uptrend' ? 'Up' :
                       indicators.trend === 'downtrend' ? 'Down' : 'Sideways'}
                    </p>
                  </div>
                )}
                {indicators.adx != null && (
                  <div className="bg-surface-hover rounded-lg p-2">
                    <span className="text-text-muted">ADX</span>
                    <p className="text-text font-medium">{indicators.adx}</p>
                  </div>
                )}
              </div>
            )}
            {signal?.reason && (
              <p className="text-xs text-text-muted leading-relaxed">{signal.reason}</p>
            )}
            <p className="text-[10px] text-text-muted/40 pt-1 flex items-center gap-1">
              <InfoIcon size={10} /> Based on technical indicators. Not financial advice.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
