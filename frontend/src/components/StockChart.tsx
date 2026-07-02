import { useRef, useEffect, useState } from 'react'
import { createChart, ColorType, CandlestickSeries, LineSeries } from 'lightweight-charts'
import type { PricePoint, Indicators } from '../types'
import { WarningIcon } from './Icons'

interface Props {
  data: PricePoint[]
  indicators?: Indicators
  height?: number
}

function getCSSVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export default function StockChart({ data, indicators, height = 420 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null)
  const resizeObserverRef = useRef<ResizeObserver | null>(null)
  const [chartType, setChartType] = useState<'candle' | 'line'>('candle')
  const [renderError, setRenderError] = useState(false)
  const [showIndicators, setShowIndicators] = useState<Record<string, boolean>>({
    sma20: false,
    sma50: false,
    bollinger: false,
  })

  useEffect(() => {
    const container = containerRef.current
    if (!container || data.length === 0) return
    setRenderError(false)

    try {
      const bg = getCSSVar('--bg-card') || '#1a1d26'
      const textColor = getCSSVar('--text-muted') || '#94a3b8'
      const gridColor = getCSSVar('--border') || '#2a2d3a'

      const chart = createChart(container, {
        width: container.clientWidth || 800,
        height,
        layout: {
          background: { type: ColorType.Solid, color: bg },
          textColor,
        },
        grid: {
          vertLines: { color: gridColor },
          horzLines: { color: gridColor },
        },
        crosshair: {
          mode: 0,
          vertLine: { color: '#3b82f6', width: 1, style: 2 },
          horzLine: { color: '#3b82f6', width: 1, style: 2 },
        },
        timeScale: {
          borderColor: gridColor,
          timeVisible: true,
        },
        rightPriceScale: {
          borderColor: gridColor,
        },
      })
      chartRef.current = chart

      const validData = data.filter((d) => d.date && d.close != null)
      if (validData.length < 2) {
        chart.remove()
        chartRef.current = null
        setRenderError(true)
        return
      }

      const candleData = validData.map((d) => ({
        time: d.date,
        open: d.open ?? d.close,
        high: d.high ?? d.close,
        low: d.low ?? d.close,
        close: d.close,
      }))

      const lineData = validData.map((d) => ({
        time: d.date,
        value: d.close,
      }))

      if (chartType === 'candle') {
        chart.addSeries(CandlestickSeries, {
          upColor: '#22c55e',
          downColor: '#ef4444',
          borderUpColor: '#22c55e',
          borderDownColor: '#ef4444',
          wickUpColor: '#22c55e',
          wickDownColor: '#ef4444',
        }).setData(candleData)
      } else {
        chart.addSeries(LineSeries, {
          color: '#3b82f6',
          lineWidth: 2,
        }).setData(lineData)
      }

      if (showIndicators.sma20 && indicators?.sma20) {
        const smaData = validData.map((d) => ({
          time: d.date,
          value: indicators.sma20 ?? d.close,
        })).slice(20)
        chart.addSeries(LineSeries, { color: '#eab308', lineWidth: 1, lineStyle: 2, title: 'SMA20' }).setData(smaData)
      }

      if (showIndicators.sma50 && indicators?.sma50) {
        const smaData = validData.map((d) => ({
          time: d.date,
          value: indicators.sma50 ?? d.close,
        })).slice(50)
        chart.addSeries(LineSeries, { color: '#f97316', lineWidth: 1, lineStyle: 2, title: 'SMA50' }).setData(smaData)
      }

      if (showIndicators.bollinger && indicators?.bb_upper) {
        const upper = validData.map((d) => ({ time: d.date, value: indicators.bb_upper ?? d.close }))
        const lower = validData.map((d) => ({ time: d.date, value: indicators.bb_lower ?? d.close }))
        const middle = validData.map((d) => ({ time: d.date, value: indicators.bb_middle ?? d.close }))
        chart.addSeries(LineSeries, { color: '#8b5cf6', lineWidth: 1, title: 'BB Upper' }).setData(upper)
        chart.addSeries(LineSeries, { color: '#8b5cf6', lineWidth: 1, title: 'BB Lower' }).setData(lower)
        chart.addSeries(LineSeries, { color: '#a78bfa', lineWidth: 1, lineStyle: 2, title: 'BB Middle' }).setData(middle)
      }

      chart.timeScale().fitContent()

      resizeObserverRef.current = new ResizeObserver(() => {
        if (container && chartRef.current) {
          chartRef.current.applyOptions({ width: container.clientWidth })
        }
      })
      resizeObserverRef.current.observe(container)

      return () => {
        resizeObserverRef.current?.disconnect()
        resizeObserverRef.current = null
        chart.remove()
        chartRef.current = null
      }
    } catch (err) {
      console.error('[StockChart] Render error:', err)
      setRenderError(true)
    }
  }, [data, chartType, showIndicators, height, indicators])

  if (data.length === 0) {
    return (
      <div className="rounded-xl bg-surface-card border border-border flex items-center justify-center" style={{ height }}>
        <p className="text-text-muted text-sm">Select a stock to view chart</p>
      </div>
    )
  }

  if (renderError) {
    return (
      <div className="rounded-xl bg-surface-card border border-border flex items-center justify-center" style={{ height }}>
        <div className="text-center">
          <WarningIcon size={24} className="text-yellow mx-auto mb-2" />
          <p className="text-text-muted text-sm">Chart render unavailable for this data</p>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border flex-wrap">
        <button
          onClick={() => setChartType('candle')}
          className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${chartType === 'candle' ? 'bg-accent text-white' : 'text-text-muted hover:text-text'}`}
        >
          Candle
        </button>
        <button
          onClick={() => setChartType('line')}
          className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${chartType === 'line' ? 'bg-accent text-white' : 'text-text-muted hover:text-text'}`}
        >
          Line
        </button>
        <div className="w-px h-4 bg-border mx-1" />
        <button
          onClick={() => setShowIndicators((p) => ({ ...p, sma20: !p.sma20 }))}
          className={`px-2 py-0.5 rounded text-xs ${showIndicators.sma20 ? 'bg-yellow/15 text-yellow' : 'text-text-muted hover:text-text'}`}
        >
          SMA20
        </button>
        <button
          onClick={() => setShowIndicators((p) => ({ ...p, sma50: !p.sma50 }))}
          className={`px-2 py-0.5 rounded text-xs ${showIndicators.sma50 ? 'bg-orange/15 text-orange' : 'text-text-muted hover:text-text'}`}
        >
          SMA50
        </button>
        <button
          onClick={() => setShowIndicators((p) => ({ ...p, bollinger: !p.bollinger }))}
          className={`px-2 py-0.5 rounded text-xs ${showIndicators.bollinger ? 'bg-purple/15 text-purple-400' : 'text-text-muted hover:text-text'}`}
        >
          Bollinger
        </button>
      </div>
      <div ref={containerRef} style={{ width: '100%', minHeight: height }} />
    </div>
  )
}
