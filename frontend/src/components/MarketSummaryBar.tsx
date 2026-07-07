interface MarketSummary {
  turnover: number | null
  trades: number | null
  scrips: number | null
  market_cap: number | null
}

function formatNum(n: number | null): string {
  if (n == null) return '—'
  if (n >= 1e9) return `Rs ${(n / 1e9).toFixed(2)}B`
  if (n >= 1e7) return `Rs ${(n / 1e7).toFixed(2)}Cr`
  if (n >= 1e5) return `Rs ${(n / 1e5).toFixed(2)}L`
  return n.toLocaleString()
}

interface Props {
  summary: MarketSummary
  lastUpdated?: string
}

/** Displays key market summary metrics (turnover, trades, scrips, market cap). */
export default function MarketSummaryBar({ summary, lastUpdated }: Props) {
  const items = [
    { label: 'Turnover', value: formatNum(summary.turnover) },
    { label: 'Trades', value: summary.trades != null ? summary.trades.toLocaleString() : '—' },
    { label: 'Scrips', value: summary.scrips != null ? String(summary.scrips) : '—' },
    { label: 'Market Cap', value: formatNum(summary.market_cap) },
  ]

  return (
    <div className="rounded-xl bg-surface-card border border-border px-4 py-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-4 sm:gap-6 flex-wrap">
          {items.map((item) => (
            <div key={item.label} className="flex items-center gap-1.5">
              <span className="text-[10px] uppercase tracking-wider text-text-muted">{item.label}:</span>
              <span className="text-xs font-semibold text-text font-mono-nums">{item.value}</span>
            </div>
          ))}
        </div>
        {lastUpdated && (
          <span className="text-[10px] text-text-muted/50">Updated {lastUpdated}</span>
        )}
      </div>
    </div>
  )
}
