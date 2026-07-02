import { motion } from 'framer-motion'
import { TrendingUpIcon, TrendingDownIcon, ChartIcon } from './Icons'
import { formatNPR, formatChange, formatPercent } from '../utils/format'

interface Item {
  symbol: string
  ltp?: number | null
  change?: number | null
  percent_change?: number | null
  turnover?: number
}

interface Props {
  title: string
  items: Item[]
  type: 'gainers' | 'losers' | 'active'
  onSelect?: (symbol: string) => void
  loading?: boolean
}

const colorMap: Record<string, string> = {
  gainers: 'text-green',
  losers: 'text-red',
  active: 'text-accent',
}

const headerIconMap = {
  gainers: TrendingUpIcon,
  losers: TrendingDownIcon,
  active: ChartIcon,
}

export default function WinnerLoserCard({ title, items, type, onSelect, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-xl bg-surface-card border border-border p-4">
        <h3 className="text-sm font-semibold text-text mb-3">{title}</h3>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="animate-shimmer h-6 rounded mb-2" style={{ width: `${80 - i * 5}%` }} />
        ))}
      </div>
    )
  }

  const HeaderIcon = headerIconMap[type]
  const isGainerLoser = type === 'gainers' || type === 'losers'

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl bg-surface-card border border-border p-4"
    >
      <h3 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
        <HeaderIcon size={16} className={colorMap[type]} />
        {title}
      </h3>
      <div className="space-y-1">
        {items.slice(0, 5).map((item, i) => (
          <motion.button
            key={item.symbol}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            onClick={() => onSelect?.(item.symbol)}
            className="w-full flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-surface-hover transition-colors"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xs text-text-muted w-4 shrink-0">{i + 1}.</span>
              <span className="text-sm font-medium text-text truncate">{item.symbol}</span>
            </div>
            {isGainerLoser ? (
              <div className="flex items-center gap-3 shrink-0 ml-2">
                {item.ltp != null && (
                  <span className="text-xs font-mono-nums text-text-muted tabular-nums">
                    {formatNPR(item.ltp)}
                  </span>
                )}
                {item.change != null && (
                  <span className={`flex items-center gap-0.5 text-xs font-semibold font-mono-nums tabular-nums ${item.change >= 0 ? 'text-green' : 'text-red'}`}>
                    {item.change >= 0 ? <TrendingUpIcon size={10} /> : <TrendingDownIcon size={10} />}
                    {formatChange(item.change)}
                  </span>
                )}
                {item.percent_change != null && (
                  <span className={`text-xs font-semibold font-mono-nums tabular-nums ${item.percent_change >= 0 ? 'text-green' : 'text-red'}`}>
                    {formatPercent(item.percent_change, 1)}
                  </span>
                )}
                {item.change == null && item.percent_change == null && <span className="text-xs text-text-muted">\u2014</span>}
              </div>
            ) : (
              <span className="text-sm font-semibold text-accent">
                {(item.turnover || 0) / 1e6 >= 1
                  ? `${((item.turnover || 0) / 1e6).toFixed(1)}M`
                  : `${((item.turnover || 0) / 1e3).toFixed(0)}K`}
              </span>
            )}
          </motion.button>
        ))}
        {items.length === 0 && (
          <p className="text-xs text-text-muted text-center py-2">No data available</p>
        )}
      </div>
    </motion.div>
  )
}
