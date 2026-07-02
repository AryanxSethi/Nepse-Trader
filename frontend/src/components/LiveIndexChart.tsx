import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, LineSeries } from 'lightweight-charts'
import { formatNPR } from '../utils/format'

interface Props {
  className?: string
}

interface IndexPoint {
  time: number
  value: number
}

export default function LiveIndexChart({ className = '' }: Props) {
  const chartRef = useRef<HTMLDivElement>(null)
  const seriesRef = useRef<ReturnType<ReturnType<typeof createChart>['addSeries']> | null>(null)
  const chartApiRef = useRef<ReturnType<typeof createChart> | null>(null)
  const [points, setPoints] = useState<IndexPoint[]>([])
  const [currentValue, setCurrentValue] = useState<number | null>(null)
  const [currentChange, setCurrentChange] = useState<number | null>(null)
  const [currentPerChange, setCurrentPerChange] = useState<number | null>(null)

  useEffect(() => {
    if (!chartRef.current) return
    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 120,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#94a3b8',
        fontSize: 10,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false },
      },
      rightPriceScale: {
        visible: false,
      },
      timeScale: {
        visible: true,
        timeVisible: true,
        secondsVisible: false,
        borderVisible: false,
        tickMarkFormatter: (time: number) => {
          const d = new Date(time * 1000)
          const now = new Date()
          const isToday = d.getUTCFullYear() === now.getUTCFullYear() &&
            d.getUTCMonth() === now.getUTCMonth() &&
            d.getUTCDate() === now.getUTCDate()
          if (isToday) {
            const nptMs = time * 1000 + (5 * 3600 + 45 * 60) * 1000
            const npt = new Date(nptMs)
            return npt.getUTCHours().toString().padStart(2, '0') + ':' +
                   npt.getUTCMinutes().toString().padStart(2, '0')
          }
          return d.getUTCDate().toString().padStart(2, '0') + '/' +
                 (d.getUTCMonth() + 1).toString().padStart(2, '0')
        },
      },
      crosshair: {
        vertLine: { visible: false },
        horzLine: { visible: false },
      },
      handleScroll: false,
      handleScale: false,
    })
    const series = chart.addSeries(LineSeries, {
      color: '#06b6d4',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })
    chartApiRef.current = chart
    seriesRef.current = series

    const handleResize = () => {
      if (chartRef.current) {
        chart.applyOptions({ width: chartRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartApiRef.current = null
      seriesRef.current = null
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const fetchHistory = async () => {
      try {
        const res = await fetch('/api/market/index-history')
        if (!res.ok) return
        const json = await res.json()
        if (cancelled) return
        const pts: IndexPoint[] = (json.points || []).map((p: { time: number | string; value: number }) => ({
          time: typeof p.time === 'string' ? Math.floor(new Date(p.time).getTime() / 1000) : p.time,
          value: p.value,
        }))
        setPoints(pts)
        if (pts.length >= 2) {
          seriesRef.current?.setData(pts as any)
        }
        if (json.current) {
          setCurrentValue(json.current.currentValue)
          setCurrentChange(json.current.change)
          setCurrentPerChange(json.current.perChange)
        } else if (pts.length > 0) {
          setCurrentValue(pts[pts.length - 1].value)
        }
      } catch {}
    }
    fetchHistory()
    const id = setInterval(fetchHistory, 30000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  if (currentValue === null) return null

  const isPositive = (currentChange ?? 0) >= 0
  const colorClass = isPositive ? 'text-green' : 'text-red'

  return (
    <div className={`rounded-xl bg-surface-card border border-border p-4 ${className}`}>
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs font-semibold text-text-muted">NEPSE Index</span>
        <div className="text-right">
          <span className={`text-2xl font-bold ${colorClass}`}>
            {formatNPR(currentValue)}
          </span>
          {currentChange != null && (
            <span className={`text-sm ml-2 font-medium ${colorClass}`}>
              {isPositive ? '+' : ''}{currentChange?.toFixed(2)} ({isPositive ? '+' : ''}{currentPerChange?.toFixed(2)}%)
            </span>
          )}
        </div>
      </div>
      <div className="relative">
        <div ref={chartRef} className={`w-full ${points.length < 2 ? 'invisible' : ''}`} />
        {points.length < 2 && (
          <div className="absolute inset-0 flex items-center justify-center text-[11px] text-text-muted">
            Loading index chart...
          </div>
        )}
      </div>
    </div>
  )
}
