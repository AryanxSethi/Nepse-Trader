import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import SignalTable from '../components/SignalTable'
import { useSignals } from '../hooks/useStockData'
import RefreshIndicator from '../components/RefreshIndicator'
import { PageTransition } from '../components/Navbar'
import { SignalIcon, WarningIcon } from '../components/Icons'

export default function Signals() {
  const navigate = useNavigate()
  const [signalType, setSignalType] = useState('')
  const [fetchedAt, setFetchedAt] = useState<string | null>(null)
  const { data, isLoading, error } = useSignals(signalType || undefined)

  useEffect(() => {
    if (data && !isLoading) {
      setFetchedAt(new Date().toISOString())
    }
  }, [data, isLoading])

  return (
    <PageTransition>
      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        <div>
          <div className="flex items-center gap-2">
            <SignalIcon size={20} className="text-accent" />
            <h1 className="text-xl font-bold text-text">Signals</h1>
          </div>
          <p className="text-sm text-text-muted mt-1">Technical indicator-based signals for NEPSE stocks</p>
        </div>

        {error && (
          <div className="rounded-xl bg-red/10 border border-red/20 p-3 flex items-start gap-2">
            <WarningIcon size={16} className="text-red shrink-0 mt-0.5" />
            <p className="text-sm text-red">Signal data unavailable. Generate signals from the backend.</p>
          </div>
        )}

        <div className="flex items-center gap-2">
          <RefreshIndicator fetchedAt={fetchedAt} />
          <select
            value={signalType}
            onChange={(e) => setSignalType(e.target.value)}
            className="bg-surface-hover text-text text-sm rounded-lg px-3 py-1.5 border border-border outline-none"
          >
            <option value="">All</option>
            <option value="BUY">Buy</option>
            <option value="SELL">Sell</option>
            <option value="HOLD">Hold</option>
          </select>
          <span className="text-xs text-text-muted">{(data || []).length} signals</span>
        </div>

        <SignalTable
          signals={data || []}
          onSelectSymbol={(symbol) => navigate(`/trade?symbol=${symbol}`)}
          loading={isLoading}
        />

        <p className="text-[10px] text-text-muted/40 text-center">
          Signals based on technical indicators (RSI, MACD, SMA, Volume). Not financial advice.
        </p>
      </div>
    </PageTransition>
  )
}
