import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { BacktestIcon } from './Icons'

interface EquityPoint {
  date: string
  value: number
}

interface Props {
  data: EquityPoint[]
  strategyReturn: number
  buyHoldReturn: number
  loading?: boolean
}

/** Line chart comparing strategy equity curve against buy-and-hold. */
export default function EquityCurve({ data, strategyReturn, buyHoldReturn, loading }: Props) {
  if (loading) {
    return <div className="animate-shimmer rounded-xl h-64 bg-surface-card" />
  }

  if (!data.length) {
    return (
      <div className="rounded-xl bg-surface-card border border-border flex items-center justify-center h-64">
        <div className="text-center">
          <BacktestIcon size={32} className="text-text-muted/30 mx-auto mb-2" />
          <p className="text-text-muted text-sm">Run a backtest to see results</p>
        </div>
      </div>
    )
  }

  const strategyColor = strategyReturn >= 0 ? '#22c55e' : '#ef4444'
  const buyHoldColor = '#3b82f6'

  return (
    <div className="rounded-xl bg-surface-card border border-border p-4">
      <h3 className="text-sm font-semibold text-text mb-4">Equity Curve</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="date"
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            tickFormatter={(v) => v.slice(5, 10)}
            stroke="var(--border)"
          />
          <YAxis
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            stroke="var(--border)"
            domain={['dataMin - 5000', 'dataMax + 5000']}
          />
          <Tooltip
            contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)' }}
          />
          <Legend
            formatter={(value) => <span style={{ color: 'var(--text-muted)' }}>{value}</span>}
          />
          <Line
            type="monotone"
            dataKey="value"
            name="Strategy"
            stroke={strategyColor}
            strokeWidth={2}
            dot={false}
            isAnimationActive={true}
            animationDuration={1200}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="flex gap-4 mt-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-3 h-0.5 rounded" style={{ background: strategyColor }} />
          <span className="text-text-muted">Strategy: <span className="text-text font-medium">{strategyReturn > 0 ? '+' : ''}{strategyReturn}%</span></span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-0.5 rounded" style={{ background: buyHoldColor }} />
          <span className="text-text-muted">Buy & Hold: <span className="text-text font-medium">{buyHoldReturn > 0 ? '+' : ''}{buyHoldReturn}%</span></span>
        </div>
      </div>
    </div>
  )
}
