import { useEffect } from 'react'

export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} — NEPSE Trader` : 'NEPSE Trader'
  }, [title])
}