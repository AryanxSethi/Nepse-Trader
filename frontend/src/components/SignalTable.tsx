import { motion } from 'framer-motion'
import type { SignalRow } from '../types'
import { ArrowRightIcon } from './Icons'

interface Props {
  signals: SignalRow[]
  onSelectSymbol: (symbol: string) => void
  loading?: boolean
}

/** Table displaying AI-generated trading signals with confidence bars. */
export default function SignalTable({ signals, onSelectSymbol, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-xl bg-surface-card border border-border p-4 space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="animate-shimmer h-10 rounded" />
        ))}
      </div>
    )
  }

  return (
    <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-text-muted text-xs">
              <th className="text-left px-4 py-3 font-medium">Symbol</th>
              <th className="text-left px-4 py-3 font-medium">Signal</th>
              <th className="text-right px-4 py-3 font-medium">Confidence</th>
              <th className="text-left px-4 py-3 font-medium hidden md:table-cell">Reason</th>
              <th className="text-right px-4 py-3 font-medium hidden sm:table-cell">Time</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {signals.map((s, i) => (
              <motion.tr
                key={`${s.symbol}-${i}`}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.015 }}
                onClick={() => onSelectSymbol(s.symbol)}
                className="border-b border-border/50 hover:bg-surface-hover cursor-pointer transition-colors"
              >
                <td className="px-4 py-3">
                  <span className="font-medium text-text">{s.symbol}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                    s.signal_type === 'BUY' ? 'bg-green/15 text-green' :
                    s.signal_type === 'SELL' ? 'bg-red/15 text-red' :
                    'bg-yellow/15 text-yellow'
                  }`}>
                    {s.signal_type}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-16 h-1.5 rounded-full bg-border overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          s.confidence >= 70 ? 'bg-green' : s.confidence >= 50 ? 'bg-yellow' : 'bg-red'
                        }`}
                        style={{ width: `${s.confidence}%` }}
                      />
                    </div>
                    <span className="text-text-muted text-xs w-8 text-right">{s.confidence}%</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-text-muted text-xs hidden md:table-cell max-w-xs truncate">
                  {s.reason}
                </td>
                <td className="px-4 py-3 text-text-muted text-xs hidden sm:table-cell text-right">
                  {new Date(s.generated_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3 text-right">
                  <ArrowRightIcon size={14} className="text-text-muted/50" />
                </td>
              </motion.tr>
            ))}
            {signals.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-text-muted text-sm py-8">
                  No signals available for this filter
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
