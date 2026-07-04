import { useState, useEffect, useCallback } from 'react'

interface MarketStatus {
  is_open: boolean
  as_of: string
  next_open: string
  next_close: string | null
}

function computeLocalStatus(): MarketStatus {
  const now = new Date()
  const nptOffset = 5 * 60 + 45
  const utc = now.getTime() + now.getTimezoneOffset() * 60000
  const npt = new Date(utc + nptOffset * 60000)

  const day = npt.getDay()
  const hours = npt.getHours()
  const minutes = npt.getMinutes()
  const totalMinutes = hours * 60 + minutes

  const isWeekend = day === 6 || day === 0
  const isAfterHours = totalMinutes < 11 * 60 || totalMinutes >= 15 * 60
  const is_open = !isWeekend && !isAfterHours

  const nextOpen = new Date(npt)
  nextOpen.setHours(11, 0, 0, 0)
  if (totalMinutes >= 15 * 60 || isWeekend) {
    do {
      nextOpen.setDate(nextOpen.getDate() + 1)
    } while (nextOpen.getDay() === 6 || nextOpen.getDay() === 0)
  }

  const nextClose = is_open ? new Date(npt) : null
  if (nextClose) {
    nextClose.setHours(15, 0, 0, 0)
  }

  return {
    is_open,
    as_of: npt.toISOString(),
    next_open: nextOpen.toISOString(),
    next_close: nextClose ? nextClose.toISOString() : null,
  }
}

export function useMarketStatus() {
  const [status, setStatus] = useState<MarketStatus>(computeLocalStatus)

  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const res = await fetch('/api/market/status', { signal })
      if (res.ok) {
        const data = await res.json()
        setStatus(data)
        return
      }
    } catch {
      console.warn('Market status fetch failed, using computed status')
    }
    setStatus(computeLocalStatus())
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 5000)
    refresh(controller.signal).finally(() => clearTimeout(timeout))
    const interval = setInterval(() => {
      const c = new AbortController()
      const t = setTimeout(() => c.abort(), 5000)
      refresh(c.signal).finally(() => clearTimeout(t))
    }, 60000)
    return () => { clearInterval(interval); controller.abort() }
  }, [refresh])

  return status
}


