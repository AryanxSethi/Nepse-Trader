import { useEffect, useRef } from 'react'
import { createChart, ColorType, LineSeries } from 'lightweight-charts'
import { useMarketStatus } from '../hooks/useMarketStatus'
import { fetchIndexHistory } from '../api/endpoints'
import { POLL } from '../config/constants'

/** TradingView-style line chart for NEPSE and Sensitive Index (today-only intraday). */
export default function IndexChart() {
  const marketStatus = useMarketStatus()
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null)
  const nepseRef = useRef<ReturnType<ReturnType<typeof createChart>['addSeries']> | null>(null)
  const sensRef = useRef<ReturnType<ReturnType<typeof createChart>['addSeries']> | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    const chart = createChart(containerRef.current, {
      autoSize: true,
      height: 240,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#94a3b8',
        fontSize: 11,
      },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      rightPriceScale: { visible: true, borderVisible: false, scaleMargins: { top: 0.05, bottom: 0.12 } },
      timeScale: {
        visible: true,
        timeVisible: true,
        borderVisible: false,
        tickMarkFormatter: (time: number | string | { timestamp: number }) => {
          if (typeof time !== 'number') return ''
          const d = new Date((time + 5 * 3600 + 45 * 60) * 1000)
          return `${d.getUTCHours().toString().padStart(2, '0')}:${d.getUTCMinutes().toString().padStart(2, '0')}`
        },
      },
      crosshair: {
        vertLine: { visible: true, labelVisible: true, style: 2 },
        horzLine: { visible: true, labelVisible: true, style: 2 },
      },
      handleScroll: false,
      handleScale: false,
    })
    chartRef.current = chart
    nepseRef.current = chart.addSeries(LineSeries, {
      priceScaleId: 'right',
      color: '#06b6d4', lineWidth: 3,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
    })
    sensRef.current = chart.addSeries(LineSeries, {
      priceScaleId: 'left',
      color: '#f59e0b', lineWidth: 3,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
    })
    chart.priceScale('left').applyOptions({
      visible: true,
      borderVisible: false,
      scaleMargins: { top: 0.5, bottom: 0.05 },
    })

    return () => {
      chart.remove()
      chartRef.current = null
      nepseRef.current = null
      sensRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!marketStatus.is_open) {
      nepseRef.current?.setData([])
      sensRef.current?.setData([])
      return
    }
    let id: ReturnType<typeof setInterval> | null = null
    const refresh = async () => {
      try {
        const json = await fetchIndexHistory()
        const data = json.today?.length ? json.today : (json.snapshots ?? [])
        if (!data || data.length === 0) return
        if (nepseRef.current) {
          nepseRef.current.setData(data.map(s => ({ time: s.time as any, value: s.values['NEPSE'] ?? 0 })) as any)
        }
        if (sensRef.current) {
          sensRef.current.setData(data.map(s => ({ time: s.time as any, value: s.values['Sensitive Index'] ?? 0 })) as any)
        }
      } catch { /* ignore */ }
    }
    refresh()
    id = setInterval(refresh, POLL.SNAPSHOT_OPEN)
    return () => { if (id) clearInterval(id) }
  }, [marketStatus.is_open])

  return (
    <div className="rounded-xl bg-surface-card border border-border p-4">
      <div className="flex items-center gap-2 mb-2">
        <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4 text-accent">
          <path d="M3 12h2v7H3v-7zm4-4h2v11H7V8zm4-3h2v14h-2V5zm4 6h2v8h-2v-8zm4-8h2v16h-2V3z" fill="currentColor" />
        </svg>
        <span className="text-xs font-semibold text-text-muted">Index Overlay</span>
        <span className="flex items-center gap-1 text-[10px] text-text-muted ml-2">
          <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: '#06b6d4' }} />
          NEPSE
        </span>
        <span className="flex items-center gap-1 text-[10px] text-text-muted">
          <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: '#f59e0b' }} />
          Sensitive
        </span>
      </div>
      <div className="relative" style={{ height: 240 }}>
        <div ref={containerRef} className="w-full" style={{ height: 240 }} />
        {!marketStatus.is_open && (
          <div className="absolute inset-0 flex items-center justify-center bg-surface-card">
            <p className="text-[11px] text-text-muted/40">Chart available during market hours</p>
          </div>
        )}
      </div>
    </div>
  )
}
