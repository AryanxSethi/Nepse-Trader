import { useEffect, useState } from 'react'

interface RefreshIndicatorProps {
  fetchedAt?: string | null
  stale?: boolean
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const seconds = Math.floor(diff / 1000)
  if (seconds < 10) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ago`
}

/** Shows when data was last updated with a stale indicator. */
export default function RefreshIndicator({ fetchedAt, stale }: RefreshIndicatorProps) {
  const [label, setLabel] = useState('')

  useEffect(() => {
    if (!fetchedAt) {
      setLabel('')
      return
    }
    const update = () => setLabel(timeAgo(fetchedAt))
    update()
    const id = setInterval(update, 10000)
    return () => clearInterval(id)
  }, [fetchedAt])

  if (!label) return null

  return (
    <span
      className={`inline-flex items-center gap-1 text-[11px] font-medium ${
        stale ? 'text-yellow' : 'text-text-muted'
      }`}
    >
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${stale ? 'bg-yellow' : 'bg-green'}`} />
      Updated {label}
    </span>
  )
}
