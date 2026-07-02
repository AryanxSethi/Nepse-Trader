import { useMarketStatus } from '../hooks/useMarketStatus'

function formatCountdown(target: string): string {
  const diff = new Date(target).getTime() - new Date().getTime()
  if (diff <= 0) return 'now'
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const d = Math.floor(h / 24)
  if (d > 0) return `${d}d ${h % 24}h ${m}m`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function formatNPTTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kathmandu' })
}

function formatNPDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'Asia/Kathmandu' })
}

export default function MarketStatusBanner() {
  const status = useMarketStatus()

  if (status.is_open) {
    return (
      <div className="flex items-center justify-center gap-2 px-4 py-1.5 bg-green/10 border-b border-green/20 text-xs text-green">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-green" />
        </span>
        <span className="font-medium">Market Open</span>
        <span className="text-green/70">·</span>
        <span>Trading {formatNPTTime(status.as_of)}</span>
        {status.next_close && (
          <>
            <span className="text-green/70">·</span>
            <span>Close in {formatCountdown(status.next_close)}</span>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center gap-2 px-4 py-1.5 bg-red/5 border-b border-red/10 text-xs text-text-muted">
      <span className="h-2 w-2 rounded-full bg-red" />
      <span className="font-medium text-red">Market Closed</span>
      <span className="text-text-muted/50">·</span>
      <span>Opens {formatNPDate(status.next_open)} at {formatNPTTime(status.next_open)}</span>
      <span className="text-text-muted/50">·</span>
      <span>{formatCountdown(status.next_open)} away</span>
    </div>
  )
}
