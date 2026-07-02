import { useState, useCallback, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import SearchBar from '../components/SearchBar'
import DateRangeSelector from '../components/DateRangeSelector'
import StockChart from '../components/StockChart'
import AISuggestion from '../components/AISuggestion'
import CompanyInfo from '../components/CompanyInfo'
import ComparePanel from '../components/ComparePanel'
import HermesSidebar from '../components/HermesSidebar'
import FloatingChat from '../components/FloatingChat'
import { SkeletonBlock } from '../components/Skeleton'
import { formatNPR } from '../utils/format'
import { useStockHistory } from '../hooks/useStockData'

const MS_PER_DAY = 86400000
import { PageTransition } from '../components/Navbar'
import { CompanyIcon, WarningIcon, ChartIcon, CompareIcon } from '../components/Icons'

function toDateStr(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export default function Trade() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [symbol, setSymbol] = useState(searchParams.get('symbol') || '')
  const [dateDays, setDateDays] = useState(90)
  const [activeTab, setActiveTab] = useState<'chart' | 'compare'>('chart')

  const symbolFromParams = searchParams.get('symbol')

  useEffect(() => {
    if (symbolFromParams) setSymbol(symbolFromParams)
  }, [symbolFromParams])

  const endStrRef = useRef('')
  const startStrRef = useRef('')
  const dateStr = toDateStr(new Date())
  if (endStrRef.current !== dateStr || startStrRef.current === '') {
    const end = new Date()
    const start = new Date(end.getTime() - dateDays * MS_PER_DAY)
    startStrRef.current = toDateStr(start)
    endStrRef.current = toDateStr(end)
  }
  const startStr = startStrRef.current
  const endStr = endStrRef.current

  const { data, isLoading, error } = useStockHistory(symbol, startStr, endStr)

  const handleSearch = useCallback((sym: string, s?: string, e?: string) => {
    setSymbol(sym)
    setSearchParams({ symbol: sym })
    if (s && e) {
      const sd = new Date(s)
      const ed = new Date(e)
      setDateDays(Math.round((ed.getTime() - sd.getTime()) / MS_PER_DAY))
    }
  }, [setSearchParams])

  const handleParsedResult = useCallback((result: { symbol?: string; start_date?: string; end_date?: string }) => {
    if (result.symbol) {
      handleSearch(result.symbol, result.start_date, result.end_date)
    }
  }, [handleSearch])

  return (
    <PageTransition>
      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="flex items-center gap-4 mb-4 flex-wrap">
          <div className="flex-1 min-w-[240px]">
            <SearchBar
              onSearch={handleSearch}
              placeholder="Search symbol, e.g. NABIL or nabil past 1 year..."
              initialValue={symbol}
            />
          </div>
          <DateRangeSelector selected={dateDays} onChange={setDateDays} />
        </div>

        <div className="flex items-center gap-1 mb-4 border-b border-border">
          <button
            onClick={() => setActiveTab('chart')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors border-b-2 ${
              activeTab === 'chart' ? 'border-accent text-accent' : 'border-transparent text-text-muted hover:text-text'
            }`}
          >
            <ChartIcon size={14} />
            Chart
          </button>
          <button
            onClick={() => setActiveTab('compare')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors border-b-2 ${
              activeTab === 'compare' ? 'border-accent text-accent' : 'border-transparent text-text-muted hover:text-text'
            }`}
          >
            <CompareIcon size={14} />
            Compare
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <div className="lg:col-span-3 space-y-4">
            {activeTab === 'compare' ? (
              <ComparePanel />
            ) : (
              <>
                {symbol && (
                  <div className="flex items-center gap-3">
                    <CompanyIcon size={18} className="text-accent" />
                    <h2 className="text-lg font-bold text-text">{symbol}</h2>
                    {data?.prices?.length > 0 && (
                      <span className="text-sm text-text-muted">
                        LTP: <span className="font-semibold text-text">
                          {formatNPR(data.prices[data.prices.length - 1]?.close)}
                        </span>
                      </span>
                    )}
                  </div>
                )}

                {error && (
                  <div className="rounded-xl bg-red/10 border border-red/20 p-4 flex items-start gap-3">
                    <WarningIcon size={18} className="text-red shrink-0 mt-0.5" />
                    <p className="text-sm text-red">
                      {symbol
                        ? `Unable to load data for ${symbol}. The stock may have insufficient trading history.`
                        : 'Select a stock to view the chart'}
                    </p>
                  </div>
                )}

                {isLoading && (
                  <div className="space-y-3">
                    <SkeletonBlock height={400} />
                    <div className="grid grid-cols-3 gap-3">
                      <SkeletonBlock height={60} />
                      <SkeletonBlock height={60} />
                      <SkeletonBlock height={60} />
                    </div>
                  </div>
                )}

                {data && !isLoading && symbol && (
                  <>
                    <StockChart
                      key={symbol + startStr + endStr}
                      data={data.prices || []}
                      indicators={data.indicators}
                    />
                    {symbol && (
                      <CompanyInfo symbol={symbol} />
                    )}
                    {data.prices?.length > 0 && (
                      <AISuggestion
                        signal={data.signal}
                        indicators={data.indicators}
                      />
                    )}
                  </>
                )}

                {symbol && data && data.prices?.length === 0 && !error && !isLoading && (
                  <div className="rounded-xl bg-surface-card border border-border p-6 flex items-start gap-3">
                    <WarningIcon size={18} className="text-yellow shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-text">No price data for {symbol}</p>
                      <p className="text-xs text-text-muted mt-1">
                        This stock has no records in the selected date range. Try a wider range or a different symbol.
                      </p>
                    </div>
                  </div>
                )}

                {!symbol && !isLoading && !data && (
                  <div className="rounded-xl bg-surface-card border border-border flex items-center justify-center h-96">
                    <div className="text-center">
                      <ChartIcon size={40} className="text-text-muted/30 mx-auto mb-3" />
                      <p className="text-text-muted text-sm">Search for a stock to begin analysis</p>
                      <p className="text-text-muted/40 text-xs mt-1">NABIL, SCB, CZBIL, NICA ...</p>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          <div className="space-y-4">
            <HermesSidebar onSelectSymbol={handleSearch} currentSymbol={symbol} />
          </div>
        </div>
      </div>
      <FloatingChat symbol={symbol} onParsedResult={handleParsedResult} />
    </PageTransition>
  )
}


