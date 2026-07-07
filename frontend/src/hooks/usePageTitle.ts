import { useEffect } from 'react'

/** Set the document page title with a "NEPSE Trader" suffix. */
export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} — NEPSE Trader` : 'NEPSE Trader'
  }, [title])
}