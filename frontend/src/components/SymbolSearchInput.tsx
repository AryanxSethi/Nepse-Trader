import { useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { SearchIcon, CloseIcon } from './Icons'
import { fetchSearch } from '../api/endpoints'
import type { SearchSuggestion } from '../types'

interface Props {
  onSelect: (symbol: string) => void
  value?: string
  placeholder?: string
}

/** Search input with autocomplete suggestions for stock symbols. */
export default function SymbolSearchInput({ onSelect, value = '', placeholder = 'Search stock...' }: Props) {
  const [query, setQuery] = useState(value)
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const abortRef = useRef<AbortController | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setQuery(value)
  }, [value])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSuggestions([])
      setOpen(false)
      return
    }
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setLoading(true)
    try {
      const data = await fetchSearch(q)
      const items = data.suggestions || []
      setSuggestions(items)
      setOpen(items.length > 0)
    } catch {
      setSuggestions([])
      setOpen(false)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    clearTimeout(timer.current)
    if (query.trim().length > 1) {
      timer.current = setTimeout(() => doSearch(query), 300)
    } else {
      setSuggestions([])
      setOpen(false)
    }
    return () => clearTimeout(timer.current)
  }, [query, doSearch])

  const selectSuggestion = (s: SearchSuggestion) => {
    clearTimeout(timer.current)
    abortRef.current?.abort()
    setQuery(s.symbol)
    setSuggestions([])
    setOpen(false)
    onSelect(s.symbol)
  }

  const handleClear = () => {
    abortRef.current?.abort()
    setQuery('')
    setSuggestions([])
    setOpen(false)
    onSelect('')
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-hover px-3 py-2 transition-all duration-200 focus-within:border-accent/50">
        {loading ? (
          <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin shrink-0" />
        ) : (
          <SearchIcon size={14} className="text-text-muted shrink-0" />
        )}
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => { if (suggestions.length > 0) setOpen(true) }}
          placeholder={placeholder}
          className="flex-1 bg-transparent outline-none text-sm text-text placeholder-text-muted/40"
        />
        {query && (
          <button
            type="button"
            onClick={handleClear}
            className="text-text-muted hover:text-text transition-colors shrink-0"
          >
            <CloseIcon size={12} />
          </button>
        )}
      </div>

      <AnimatePresence>
        {open && suggestions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="absolute top-full mt-1 w-full bg-surface-card border border-border rounded-xl overflow-hidden shadow-xl z-50"
          >
            {suggestions.map((s, i) => (
              <motion.button
                key={`${s.symbol}-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.02 }}
                onClick={() => selectSuggestion(s)}
                className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-surface-hover transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span className="text-sm font-medium text-text shrink-0">{s.symbol}</span>
                  <span className="text-xs text-text-muted truncate">{s.name}</span>
                </div>
                {s.ltp != null && (
                  <span className="text-xs font-medium text-text shrink-0 mr-2">{s.ltp.toFixed(2)}</span>
                )}
                {s.percent_change != null && (
                  <span className={`text-xs font-medium shrink-0 mr-2 ${s.percent_change >= 0 ? 'text-green' : 'text-red'}`}>
                    {s.percent_change >= 0 ? '+' : ''}{s.percent_change.toFixed(1)}%
                  </span>
                )}
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${
                  s.match_type === 'exact' ? 'bg-green/10 text-green' : 'bg-yellow/10 text-yellow'
                }`}>
                  {s.match_type === 'exact' ? 'exact' : 'fuzzy'}
                </span>
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
