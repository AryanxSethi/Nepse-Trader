import { useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { SearchIcon, CloseIcon } from './Icons'
import { fetchSearch } from '../api/endpoints'
import type { SearchSuggestion } from '../types'

interface Props {
  onSearch: (symbol: string, start?: string, end?: string) => void
  placeholder?: string
  mode?: 'stock' | 'guide'
  initialValue?: string
}

export default function SearchBar({ onSearch, placeholder = 'Search stock...', mode = 'stock', initialValue }: Props) {
  const [query, setQuery] = useState(initialValue || '')
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const inputRef = useRef<HTMLInputElement>(null)
  const externalUpdate = useRef(false)
  const abortRef = useRef<AbortController | null>(null)
  const selectedSymbolRef = useRef('')

  useEffect(() => {
    if (initialValue !== undefined) {
      selectedSymbolRef.current = initialValue
      setQuery(initialValue)
    }
  }, [initialValue])

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSuggestions([])
      return
    }
    if (mode === 'guide') {
      onSearch(q)
      return
    }
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setLoading(true)
    setError(false)
    try {
      const data = await fetchSearch(q, { signal: controller.signal })
      if (data.symbol && !data.suggestions?.length) {
        onSearch(data.symbol, data.start, data.end)
        setQuery(data.symbol)
        externalUpdate.current = true
        setSuggestions([])
        return
      }
      setSuggestions(data.suggestions || [])
    } catch (err) {
      console.warn('[SearchBar] search failed:', err)
      setError(true)
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }, [onSearch, mode])

  useEffect(() => {
    if (mode === 'guide') return
    if (query === selectedSymbolRef.current) return
    clearTimeout(timer.current)
    if (query.length > 1) {
      timer.current = setTimeout(() => doSearch(query), 300)
    } else {
      setSuggestions([])
    }
    return () => clearTimeout(timer.current)
  }, [query, doSearch, mode])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    if (mode === 'guide') {
      onSearch(query)
      setQuery('')
      return
    }
    clearTimeout(timer.current)
    abortRef.current?.abort()
    if (suggestions.length > 0) {
      const s = suggestions[0]
      selectedSymbolRef.current = s.symbol
      onSearch(s.symbol)
      setQuery(s.symbol)
      externalUpdate.current = true
      setSuggestions([])
    } else {
      doSearch(query)
    }
  }

  const selectSuggestion = (s: SearchSuggestion) => {
    clearTimeout(timer.current)
    abortRef.current?.abort()
    selectedSymbolRef.current = s.symbol
    onSearch(s.symbol)
    setQuery(s.symbol)
    externalUpdate.current = true
    setSuggestions([])
    inputRef.current?.blur()
  }

  return (
    <div className="relative w-full max-w-xl">
      <form onSubmit={handleSubmit}>
        <div className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 transition-all duration-200 ${
          error ? 'border-red animate-shake' : 'border-border focus-within:border-accent/50'
        } bg-surface-card`}>
          {loading ? (
            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin shrink-0" />
          ) : (
            <SearchIcon size={16} className="text-text-muted shrink-0" />
          )}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="flex-1 bg-transparent outline-none text-sm text-text placeholder-text-muted/40"
          />
          {query && (
            <button
              type="button"
              onClick={() => { abortRef.current?.abort(); setQuery(''); setSuggestions([]) }}
              className="text-text-muted hover:text-text transition-colors shrink-0"
            >
              <CloseIcon size={14} />
            </button>
          )}
        </div>
      </form>

      <AnimatePresence>
        {suggestions.length > 0 && (
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
                className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-surface-hover transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span className="text-sm font-medium text-text shrink-0">{s.symbol}</span>
                  <span className="text-xs text-text-muted truncate">{s.name}</span>
                </div>
                {s.ltp != null && (
                  <span className="text-xs font-medium text-text shrink-0 mr-2">{s.ltp.toFixed(2)}</span>
                )}
                {s.percent_change != null && (
                  <span className={`text-xs font-medium shrink-0 mr-2 ${
                    s.percent_change >= 0 ? 'text-green' : 'text-red'
                  }`}>
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
