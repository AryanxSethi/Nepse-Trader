import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BrainIcon, ArrowUpIcon, ArrowDownIcon, InfoIcon } from './Icons'

interface Props {
  signal?: { type: string; confidence: number; reason: string } | null
  indicators?: Record<string, number | string>
}

/** Collapsible panel showing AI-generated trading signals and indicator values. */
export default function AISuggestion({ signal, indicators }: Props) {
  const [open, setOpen] = useState(false)

  if (!indicators && !signal) {
    return (
      <div className="rounded-xl bg-surface-card border border-border p-3">
        <p className="text-xs text-text-muted">Analysis available when you select a stock with sufficient data.</p>
      </div>
    )
  }

  const hasMA = indicators?.ma5_signal || indicators?.ma20_signal || indicators?.ma180_signal

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
              <div className="grid grid-cols-4 gap-1.5 text-[11px]">
                {indicators.rsi != null && (
                  <div className="bg-surface-hover rounded-lg p-1.5">
                    <span className="text-text-muted text-[10px]">RSI</span>
                    <p className="text-text font-semibold">{indicators.rsi}</p>
                  </div>
                )}
                {indicators.trend != null && (
                  <div className="bg-surface-hover rounded-lg p-1.5">
                    <span className="text-text-muted text-[10px]">Trend</span>
                    <p className={`font-semibold flex items-center gap-1 ${
                      indicators.trend === 'uptrend' ? 'text-green' :
                      indicators.trend === 'downtrend' ? 'text-red' : 'text-yellow'
                    }`}>
                      {indicators.trend === 'uptrend' ? <ArrowUpIcon size={10} /> :
                       indicators.trend === 'downtrend' ? <ArrowDownIcon size={10} /> : null}
                      {indicators.trend === 'uptrend' ? 'Up' :
                       indicators.trend === 'downtrend' ? 'Down' : 'Sideways'}
                    </p>
                  </div>
                )}
                {indicators.adx != null && (
                  <div className="bg-surface-hover rounded-lg p-1.5">
                    <span className="text-text-muted text-[10px]">ADX</span>
                    <p className="text-text font-semibold">{indicators.adx}</p>
                  </div>
                )}
                {hasMA && (
                  <div className="bg-surface-hover rounded-lg p-1.5">
                    <span className="text-text-muted text-[10px]">MA Signal</span>
                    <div className="space-y-0.5 mt-0.5">
                      {indicators.ma5_signal != null && (
                        <p className={`text-[10px] font-medium ${
                          indicators.ma5_signal === 'BULLISH' ? 'text-green' : indicators.ma5_signal === 'BEARISH' ? 'text-red' : 'text-yellow'
                        }`}>
                          MA5 {indicators.ma5_signal}
                        </p>
                      )}
                      {indicators.ma20_signal != null && (
                        <p className={`text-[10px] font-medium ${
                          indicators.ma20_signal === 'BULLISH' ? 'text-green' : indicators.ma20_signal === 'BEARISH' ? 'text-red' : 'text-yellow'
                        }`}>
                          MA20 {indicators.ma20_signal}
                        </p>
                      )}
                      {indicators.ma180_signal != null && (
                        <p className={`text-[10px] font-medium ${
                          indicators.ma180_signal === 'BULLISH' ? 'text-green' : indicators.ma180_signal === 'BEARISH' ? 'text-red' : 'text-yellow'
                        }`}>
                          MA180 {indicators.ma180_signal}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
            {signal?.reason && (
              <p className="text-xs text-text-muted leading-relaxed">{signal.reason}</p>
            )}
            <div className="rounded-lg bg-yellow/10 border border-yellow/20 p-2 flex items-start gap-1.5">
              <InfoIcon size={12} className="text-yellow shrink-0 mt-0.5" />
              <p className="text-[10px] text-yellow font-medium leading-relaxed">
                This analysis is generated by automated algorithms and may not be accurate. <strong>Not financial advice.</strong>
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
