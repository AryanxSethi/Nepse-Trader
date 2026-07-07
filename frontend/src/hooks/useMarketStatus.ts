import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchMarketStatus } from '../api/endpoints'
import type { MarketStatus } from '../types'
import { POLL, NPT_OFFSET_MINUTES } from '../config/constants'


function computeLocalStatus(): MarketStatus {
  const now = new Date()
  const utc = now.getTime() + now.getTimezoneOffset() * 60000
  const npt = new Date(utc + NPT_OFFSET_MINUTES * 60000)

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

/** Compute and poll market open/close status. */
export function useMarketStatus() {
  const [status, setStatus] = useState<MarketStatus>(computeLocalStatus)
  const retryRef = useRef(0)

  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const data = await fetchMarketStatus(signal)
      setStatus(data)
      retryRef.current = 0
      return
    } catch (e) {
      const name = e instanceof Error ? e.name : typeof e
      console.warn('Market status fetch failed: [%s] %s', name, e instanceof Error ? e.message : String(e))
    }
    setStatus(computeLocalStatus())
    if (retryRef.current < 3) {
      retryRef.current++
      await new Promise(r => setTimeout(r, retryRef.current * 2000))
      if (!signal?.aborted) await refresh(signal)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const startupTimer = setTimeout(() => refresh(controller.signal), 3000)
    const interval = setInterval(() => {
      const c = new AbortController()
      refresh(c.signal)
    }, POLL.MARKET_STATUS)
    return () => { clearTimeout(startupTimer); clearInterval(interval); controller.abort() }
  }, [refresh])

  return status
}


