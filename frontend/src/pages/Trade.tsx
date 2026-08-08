import { useState, useCallback, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import SearchBar from '../components/SearchBar'
import DateRangeSelector from '../components/DateRangeSelector'
import StockChart from '../components/StockChart'
import AISuggestion from '../components/AISuggestion'
import CompanyInfo from '../components/CompanyInfo'
import ComparePanel from '../components/ComparePanel'
import AISidebar from '../components/AISidebar'
import FloatingChat from '../components/FloatingChat'
import RefreshIndicator from '../components/RefreshIndicator'
import { SkeletonChart, SkeletonCard } from '../components/Skeleton'
import { formatNPR } from '../utils/format'
import { useStockHistory } from '../hooks/useStockData'
const MS_PER_DAY = 86400000
import { PageTransition } from '../components/Navbar'
import { usePageTitle } from '../hooks/usePageTitle'
import { fetchStockDetail, type StockDetail } from '../api/endpoints'
import { CompanyIcon, WarningIcon, ChartIcon, CompareIcon } from '../components/Icons'

function toDateStr(d: Date): string {
  return d.toISOString().slice(0, 10)
}

/** Stock analysis page with charts, comparison, and AI suggestions. */
export default function Trade() {
  usePageTitle('Stock Analysis')
  const [searchParams, setSearchParams] = useSearchParams()
  const [symbol, setSymbol] = useState(searchParams.get('symbol') || '')
  const [dateDays, setDateDays] = useState(90)
  const [activeTab, setActiveTab] = useState<'chart' | 'compare'>('chart')
  const [compareSymbols, setCompareSymbols] = useState<string[] | null>(null)
  const [fetchedAt, setFetchedAt] = useState<string | null>(null)
  const [detailData, setDetailData] = useState<StockDetail | null>(null)

  const symbolFromParams = searchParams.get('symbol')

  useEffect(() => {
    if (symbolFromParams) setSymbol(symbolFromParams)
  }, [symbolFromParams])

  useEffect(() => {
    if (!symbol) { setDetailData(null); return }
    const controller = new AbortController()
    fetchStockDetail(symbol, { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setDetailData(data) })
      .catch((err) => {
        if (!controller.signal.aborted) {
          console.warn('[Trade] stock detail fetch failed:', err)
          setDetailData(null)
        }
      })
    return () => controller.abort()
  }, [symbol])

  const startStr = useMemo(
    () => toDateStr(new Date(Date.now() - dateDays * MS_PER_DAY)),
    [dateDays]
  )
  const endStr = toDateStr(new Date())

  const { data, isLoading, error, refetch } = useStockHistory(symbol, startStr, endStr)

  useEffect(() => {
    if (data && !isLoading) {
      setFetchedAt(new Date().toISOString())
    }
  }, [data, isLoading])

  const handleSearch = useCallback((sym: string, s?: string, e?: string) => {
    setSymbol(sym)
    setActiveTab('chart')
    setCompareSymbols(null)
    setSearchParams({ symbol: sym })
    if (s && e) {
      const sd = new Date(s)
      const ed = new Date(e)
      setDateDays(Math.round((ed.getTime() - sd.getTime()) / MS_PER_DAY))
    }
  }, [setSearchParams])

  const handleParsedResult = useCallback((result: {
    symbol?: string; symbols?: string[]; start_date?: string; end_date?: string; suggested_page?: string
  }) => {
    if (result.suggested_page === 'compare' && result.symbols && result.symbols.length >= 2) {
      setActiveTab('compare')
      setCompareSymbols(result.symbols)
    } else if (result.symbol) {
      setActiveTab('chart')
      handleSearch(result.symbol, result.start_date, result.end_date)
    }
  }, [handleSearch])

  const overlayData = useMemo(() => {
    if (!detailData) return undefined
    const parseNum = (v: string | undefined) => v ? parseFloat(v.replace(/[^0-9.]/g, '')) : undefined
    const pivot: Record<string, number | undefined> = {}
    for (const key of ['s3', 's2', 's1', 'pp', 'r1', 'r2', 'r3'] as const) {
      pivot[key] = parseNum(detailData[`pivot_${key}`])
    }
    return {
      vwap: parseNum(detailData.vwap),
      prevClose: parseNum(detailData.prev_close),
      high52w: parseNum(detailData['52w_high']),
      low52w: parseNum(detailData['52w_low']),
      pivot,
    }
  }, [detailData])

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
            <RefreshIndicator fetchedAt={fetchedAt} />
            {activeTab === 'compare' ? (
              <ComparePanel key={compareSymbols?.join('-') ?? 'default'} initialSymbols={compareSymbols} />
            ) : (
              <>
                {symbol && (
                  <div className="flex items-center gap-3">
                    <CompanyIcon size={18} className="text-accent" />
                    <h2 className="text-lg font-bold text-text">{symbol}</h2>
                    {data?.prices && data.prices.length > 0 && (
                      <span className="text-sm text-text-muted">
                        LTP: <span className="font-semibold text-text">
                          {formatNPR(data.prices[data.prices.length - 1]?.close)}
                        </span>
                      </span>
                    )}
                    {detailData?.confidence_score && (
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                        detailData.confidence_score === 'High' ? 'bg-green/15 text-green' :
                        detailData.confidence_score === 'Low' ? 'bg-red/15 text-red' :
                        'bg-yellow/15 text-yellow'
                      }`}>
                        {detailData.confidence_score}
                      </span>
                    )}
                    <div className="rounded-lg bg-yellow/10 border border-yellow/20 px-2 py-1 flex items-center gap-1">
                      <WarningIcon size={10} className="text-yellow shrink-0" />
                      <p className="text-[10px] text-yellow font-medium">Chart based on market price</p>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="rounded-xl bg-red/10 border border-red/20 p-4 flex items-start gap-3">
                    <WarningIcon size={18} className="text-red shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-red">
                        {symbol
                          ? `Unable to load data for ${symbol}. The stock may have insufficient trading history.`
                          : 'Select a stock to view the chart'}
                      </p>
                      {symbol && (
                        <button
                          onClick={() => refetch()}
                          className="mt-2 text-xs text-accent hover:text-accent-hover underline"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {isLoading && (
                  <div className="space-y-3">
                    <SkeletonChart height={400} />
                    <div className="grid grid-cols-3 gap-3">
                      <SkeletonCard lines={2} />
                      <SkeletonCard lines={2} />
                      <SkeletonCard lines={2} />
                    </div>
                  </div>
                )}

                {data && !isLoading && symbol && (
                  <>
                    <StockChart
                      key={symbol + startStr + endStr}
                      data={data.prices || []}
                      indicators={data.indicators}
                      overlays={overlayData}
                    />
                    <CompanyInfo symbol={symbol} />
                    {data.prices?.length > 0 && (
                      <AISuggestion
                        signal={data.signal}
                        indicators={{
                          ...data.indicators,
                          ...(detailData?.ma5_signal ? { ma5_signal: detailData.ma5_signal } : {}),
                          ...(detailData?.ma20_signal ? { ma20_signal: detailData.ma20_signal } : {}),
                          ...(detailData?.ma180_signal ? { ma180_signal: detailData.ma180_signal } : {}),
                        }}
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

          <AISidebar onSelectSymbol={handleSearch} currentSymbol={symbol} />
        </div>
      </div>
      <FloatingChat symbol={symbol} onParsedResult={handleParsedResult} />
    </PageTransition>
  )
}
