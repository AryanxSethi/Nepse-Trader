import { useState, useEffect } from 'react'
import EquityCurve from '../components/EquityCurve'
import RefreshIndicator from '../components/RefreshIndicator'
import { SkeletonBlock } from '../components/Skeleton'
import { useBacktest } from '../hooks/useStockData'
import { PageTransition } from '../components/Navbar'
import { BacktestIcon, WarningIcon, SearchIcon } from '../components/Icons'

interface StockOption {
  symbol: string
  name: string
}

export default function Backtest() {
  const [symbol, setSymbol] = useState('NABIL')
  const [fastMA, setFastMA] = useState(20)
  const [slowMA, setSlowMA] = useState(50)
  const [days, setDays] = useState(365)
  const [run, setRun] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [stocks, setStocks] = useState<StockOption[]>([])
  const [stockSearch, setStockSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [computedAt, setComputedAt] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/securities')
      .then((r) => r.json())
      .then((data) => setStocks(data || []))
      .catch(() => {})
  }, [])

  const filteredStocks = stockSearch
    ? stocks.filter((s) =>
        s.symbol.toLowerCase().includes(stockSearch.toLowerCase()) ||
        s.name.toLowerCase().includes(stockSearch.toLowerCase())
      ).slice(0, 15)
    : []

  const { data, isLoading, error } = useBacktest(symbol, fastMA, slowMA, days, run)

  useEffect(() => {
    if (data && !isLoading) {
      setComputedAt(new Date().toISOString())
    }
  }, [data, isLoading])

  const handleRun = () => {
    if (slowMA <= fastMA) {
      setErrorMsg('Slow MA must be greater than Fast MA')
      return
    }
    setErrorMsg('')
    setRun(true)
  }

  const selectStock = (sym: string) => {
    setSymbol(sym)
    setStockSearch(sym)
    setShowDropdown(false)
  }

  return (
    <PageTransition>
      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        <div>
          <div className="flex items-center gap-2">
            <BacktestIcon size={20} className="text-accent" />
            <h1 className="text-xl font-bold text-text">Backtest Strategy</h1>
          </div>
          <p className="text-sm text-text-muted mt-1">Test MA crossover strategies against historical NEPSE data</p>
        </div>

        <div className="rounded-xl bg-surface-card border border-border p-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="relative">
              <label className="text-xs text-text-muted block mb-1">Stock</label>
              <div className="relative">
                <input
                  type="text"
                  value={stockSearch}
                  onChange={(e) => { setStockSearch(e.target.value); setShowDropdown(true) }}
                  onFocus={() => setShowDropdown(true)}
                  placeholder="Search stock..."
                  className="w-full bg-surface-hover text-text text-sm rounded-lg px-3 py-2 border border-border outline-none focus:border-accent/50 transition-colors placeholder-text-muted/40"
                />
                <SearchIcon size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
              </div>
              {showDropdown && filteredStocks.length > 0 && (
                <div className="absolute z-10 mt-1 w-full bg-surface-card border border-border rounded-lg overflow-hidden shadow-xl max-h-48 overflow-y-auto">
                  {filteredStocks.map((s) => (
                    <button
                      key={s.symbol}
                      onClick={() => selectStock(s.symbol)}
                      className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-hover transition-colors"
                    >
                      <span className="text-sm font-medium text-text">{s.symbol}</span>
                      <span className="text-xs text-text-muted truncate ml-2">{s.name}</span>
                    </button>
                  ))}
                </div>
              )}
              {showDropdown && stockSearch && filteredStocks.length === 0 && (
                <div className="absolute z-10 mt-1 w-full bg-surface-card border border-border rounded-lg p-3 shadow-xl">
                  <p className="text-xs text-text-muted">No stocks matching "{stockSearch}"</p>
                </div>
              )}
            </div>
            <div>
              <label className="text-xs text-text-muted block mb-1">Fast MA</label>
              <input
                type="number"
                value={fastMA}
                onChange={(e) => setFastMA(Number(e.target.value))}
                min={5}
                max={100}
                className="w-full bg-surface-hover text-text text-sm rounded-lg px-3 py-2 border border-border outline-none focus:border-accent/50 transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-text-muted block mb-1">Slow MA</label>
              <input
                type="number"
                value={slowMA}
                onChange={(e) => setSlowMA(Number(e.target.value))}
                min={10}
                max={200}
                className="w-full bg-surface-hover text-text text-sm rounded-lg px-3 py-2 border border-border outline-none focus:border-accent/50 transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-text-muted block mb-1">Period</label>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="w-full bg-surface-hover text-text text-sm rounded-lg px-3 py-2 border border-border outline-none focus:border-accent/50 transition-colors"
              >
                <option value={90}>3 Months</option>
                <option value={180}>6 Months</option>
                <option value={365}>1 Year</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={handleRun}
                className="w-full bg-accent text-white text-sm font-medium rounded-lg py-2 hover:bg-accent-hover transition-colors"
              >
                Run Backtest
              </button>
            </div>
          </div>
          {errorMsg && (
            <p className="text-xs text-red mt-2 flex items-center gap-1">
              <WarningIcon size={12} /> {errorMsg}
            </p>
          )}
        </div>

        {error && (
          <div className="rounded-xl bg-red/10 border border-red/20 p-3 text-sm text-red text-center">
            Backtest failed. Not enough data or invalid parameters.
          </div>
        )}

        {isLoading && (
          <div className="space-y-4">
            <SkeletonBlock height={300} />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <SkeletonBlock height={60} />
              <SkeletonBlock height={60} />
              <SkeletonBlock height={60} />
              <SkeletonBlock height={60} />
            </div>
          </div>
        )}

        {data && !isLoading && !error && (
          <div className="space-y-6 animate-fade-in">
            <EquityCurve
              data={data.equity_curve || []}
              strategyReturn={data.total_return}
              buyHoldReturn={data.buy_hold_return}
            />
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {[
                { label: 'Total Return', value: `${data.total_return > 0 ? '+' : ''}${data.total_return}%`, color: data.total_return >= 0 ? 'text-green' : 'text-red' },
                { label: 'Buy & Hold', value: `${data.buy_hold_return > 0 ? '+' : ''}${data.buy_hold_return}%`, color: 'text-text' },
                { label: 'Sharpe Ratio', value: data.sharpe_ratio, color: 'text-text' },
                { label: 'Max Drawdown', value: `${data.max_drawdown}%`, color: 'text-red' },
                { label: 'Win Rate', value: `${data.win_rate}%`, color: data.win_rate >= 50 ? 'text-green' : 'text-red' },
                { label: 'Total Trades', value: data.total_trades, color: 'text-text' },
              ].map((m) => (
                <div key={m.label} className="rounded-xl bg-surface-card border border-border p-3">
                  <p className="text-xs text-text-muted">{m.label}</p>
                  <p className={`text-lg font-bold ${m.color}`}>{m.value}</p>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-center">
              <RefreshIndicator fetchedAt={computedAt} />
            </div>
            <p className="text-[10px] text-text-muted/40 text-center">
              Past performance does not guarantee future results. For educational purposes only.
            </p>
          </div>
        )}

        {!run && !isLoading && !data && (
          <div className="rounded-xl bg-surface-card border border-border flex items-center justify-center h-64">
            <div className="text-center">
              <BacktestIcon size={40} className="text-text-muted/30 mx-auto mb-3" />
              <p className="text-text-muted text-sm">Configure parameters and click Run Backtest</p>
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  )
}
