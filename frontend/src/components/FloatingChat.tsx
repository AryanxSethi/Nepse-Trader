import { useState, useRef, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useLLMStream } from '../hooks/useLLMQuery'
import type { ParsedResult } from '../hooks/useLLMQuery'
import { formatResponse } from '../utils/formatChat'
import { ChatIcon, BrainIcon, CloseIcon } from './Icons'

interface Props {
  symbol?: string
  onParsedResult?: (result: ParsedResult) => void
}

/** Floating chat widget for querying the AI analyst about stocks. */
export default function FloatingChat({ symbol, onParsedResult }: Props) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<{ id: string; role: 'user' | 'assistant'; content: string }[]>([])
  const [input, setInput] = useState('')
  const [streamingContent, setStreamingContent] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [llmStatus, setLlmStatus] = useState<string | null>(null)
  const [matchInfo, setMatchInfo] = useState<{ symbol: string; type: string } | null>(null)
  const [fuzzySuggestion, setFuzzySuggestion] = useState<{ symbol: string; name: string } | null>(null)
  const { stream, isPending, error } = useLLMStream()
  const listRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const lastUserMessageRef = useRef('')

  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, streamingContent, isStreaming])

  useEffect(() => {
    if (error && !isStreaming) {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'assistant', content: 'Unable to reach the AI assistant. Make sure Ollama is running.' }])
    }
  }, [error, isStreaming])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open])

  useEffect(() => {
    if (open) {
      const id = setTimeout(() => textareaRef.current?.focus(), 100)
      return () => clearTimeout(id)
    }
  }, [open])

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isPending) return
    const q = input.trim()
    lastUserMessageRef.current = q
    setInput('')
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', content: q }])

    setFuzzySuggestion(null)
    setIsStreaming(true)
    setStreamingContent('')
    setLlmStatus('analyzing')

    stream(q, {
      onToken: (token) => {
        setStreamingContent((prev) => prev + token)
        setLlmStatus(null)
      },
      onMeta: (meta) => {
        if (meta.symbol_match_type && meta.symbol_match_type !== 'exact' && meta.symbol) {
          setMatchInfo({ symbol: meta.symbol, type: meta.symbol_match_type })
        }
        if (meta.fuzzy_suggestion) {
          setFuzzySuggestion({ symbol: meta.fuzzy_suggestion.symbol, name: meta.fuzzy_suggestion.name || '' })
        }
        if (onParsedResult && (meta.symbol || meta.suggested_page)) {
          onParsedResult({
            symbol: meta.symbol,
            symbols: meta.symbols,
            start_date: meta.start_date,
            end_date: meta.end_date,
            suggested_page: meta.suggested_page,
          })
        }
      },
      onDone: (fullAnswer) => {
        setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'assistant', content: fullAnswer }])
        setStreamingContent('')
        setIsStreaming(false)
        setLlmStatus(null)
        setMatchInfo(null)
      },
      onError: () => {
        setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'assistant', content: 'Unable to reach the AI assistant. Make sure Ollama is running.' }])
        setStreamingContent('')
        setIsStreaming(false)
        setLlmStatus(null)
        setMatchInfo(null)
        setFuzzySuggestion(null)
      },
      onStatus: (status) => {
        setLlmStatus(status)
      },
    })
  }, [input, isPending, stream, onParsedResult])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const form = (e.target as HTMLTextAreaElement).closest('form')
      form?.requestSubmit()
    }
    if (e.key === 'ArrowUp' && !input) {
      e.preventDefault()
      if (lastUserMessageRef.current) {
        setInput(lastUserMessageRef.current)
      }
    }
  }, [input])

  const handleFuzzyYes = useCallback(() => {
    if (!fuzzySuggestion) return
    if (onParsedResult) {
      onParsedResult({ symbol: fuzzySuggestion.symbol })
    }
    setFuzzySuggestion(null)
  }, [fuzzySuggestion, onParsedResult])

  const handleFuzzyNo = useCallback(() => {
    if (!fuzzySuggestion) return
    setMessages((prev) => [...prev, {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: 'No problem. Type the correct symbol name and I\'ll look it up.',
    }])
    setFuzzySuggestion(null)
    setTimeout(() => textareaRef.current?.focus(), 50)
  }, [fuzzySuggestion])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    autoResize()
  }, [autoResize])

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-accent text-white shadow-lg hover:bg-accent-hover transition-colors flex items-center justify-center"
          title="Ask AI Analyst"
        >
          <ChatIcon size={24} />
        </button>
      )}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-6 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)] h-[520px] max-h-[calc(100vh-6rem)] rounded-2xl bg-surface-card border border-border shadow-2xl flex flex-col overflow-hidden"
          >
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border shrink-0 shadow-[0_1px_0_0] shadow-border/30">
              <div className="flex items-center gap-2">
                <BrainIcon size={16} className="text-accent" />
                <span className="text-sm font-semibold text-text">AI Analyst</span>
              </div>
              <div className="flex items-center gap-3">
                <Link to="/guide" className="text-[11px] text-accent hover:text-accent-hover underline underline-offset-2 transition-colors">
                  Guide
                </Link>
                <button onClick={() => setOpen(false)} className="text-text-muted hover:text-text transition-colors p-1" title="Close (Esc)">
                  <CloseIcon size={16} />
                </button>
              </div>
            </div>

            <div ref={listRef} className="flex-1 overflow-y-auto px-5 py-5 space-y-5 scroll-smooth bg-surface/40">
              {messages.length === 0 && !isStreaming && (
                <div className="text-center py-12">
                  <BrainIcon size={32} className="text-accent/40 mx-auto mb-3" />
                  <p className="text-sm text-text-muted leading-relaxed">
                    Ask me anything about NEPSE stocks — compare companies, check technical indicators, or get market insights.
                  </p>
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'assistant' && <BrainIcon size={14} className="text-accent shrink-0 mt-1.5" />}
                  <div className={`rounded-2xl px-5 py-3.5 text-sm leading-[1.65] max-w-[88%] shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-accent/20 text-text rounded-br-md border border-accent/10'
                      : 'bg-surface-hover text-text border border-border/60 rounded-bl-md border-l-[3px] border-l-accent/25'
                  }`}>
                    <div
                      className="prose-custom"
                      dangerouslySetInnerHTML={{ __html: formatResponse(msg.content) }}
                    />
                    {msg.role === 'assistant' && i === messages.length - 1 && fuzzySuggestion && (
                      <div className="mt-3 flex items-center gap-2">
                        <button
                          onClick={handleFuzzyYes}
                          className="px-3 py-1.5 text-xs font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
                        >
                          Yes, show {fuzzySuggestion.symbol}
                        </button>
                        <button
                          onClick={handleFuzzyNo}
                          className="px-3 py-1.5 text-xs font-medium bg-surface-card text-text border border-border rounded-lg hover:bg-surface-hover transition-colors"
                        >
                          No, try another
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isStreaming && (
                <div className="flex gap-3">
                  <BrainIcon size={14} className="text-accent shrink-0 mt-1.5" />
                  <div className="rounded-2xl px-5 py-3.5 text-sm leading-[1.65] max-w-[88%] bg-surface-hover text-text border border-border/60 shadow-sm rounded-bl-md border-l-[3px] border-l-accent/25">
                    {matchInfo && (
                      <div className="mb-2 flex items-center gap-1.5 text-[11px] text-accent bg-accent/5 px-2 py-1 rounded-lg">
                        <span>Matched</span>
                        <span className="font-semibold">{matchInfo.symbol}</span>
                        <span className="text-text-muted">({matchInfo.type})</span>
                      </div>
                    )}
                    {streamingContent ? (
                      <div
                        className="prose-custom"
                        dangerouslySetInnerHTML={{ __html: formatResponse(streamingContent) }}
                      />
                    ) : (
                      <div className="flex items-center gap-2 py-1.5 min-h-[24px]">
                        {llmStatus === 'analyzing' && <span className="text-xs text-text-muted animate-pulse">Analyzing your question...</span>}
                        {llmStatus === 'searching' && <span className="text-xs text-text-muted animate-pulse">Searching market data...</span>}
                        {llmStatus === 'thinking' && (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-text-muted animate-pulse">Thinking</span>
                            <span className="w-2 h-2 bg-accent rounded-full animate-pulse" />
                            <span className="w-2 h-2 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
                            <span className="w-2 h-2 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
                          </div>
                        )}
                        {!llmStatus && (
                          <div className="flex gap-1.5 py-1">
                            <span className="w-2.5 h-2.5 bg-accent rounded-full animate-pulse" />
                            <span className="w-2.5 h-2.5 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
                            <span className="w-2.5 h-2.5 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
                          </div>
                        )}
                      </div>
                    )}
                    {streamingContent && fuzzySuggestion && (
                      <div className="mt-3 flex items-center gap-2">
                        <button
                          onClick={handleFuzzyYes}
                          className="px-3 py-1.5 text-xs font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
                        >
                          Yes, show {fuzzySuggestion.symbol}
                        </button>
                        <button
                          onClick={handleFuzzyNo}
                          className="px-3 py-1.5 text-xs font-medium bg-surface-card text-text border border-border rounded-lg hover:bg-surface-hover transition-colors"
                        >
                          No, try another
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            <form onSubmit={handleSubmit} className="flex items-end gap-2 px-5 py-4 border-t border-border shrink-0 bg-surface/20">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                aria-label={symbol ? 'Ask about ' + symbol : 'Ask about stocks'}
                placeholder={symbol ? `Ask about ${symbol}...` : 'Ask about stocks...'}
                rows={1}
                className="flex-1 bg-surface-hover text-text text-sm rounded-xl px-4 py-3 border border-border outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-colors placeholder-text-muted/40 resize-none overflow-y-auto max-h-[120px] leading-[1.5]"
              />
              <button
                type="submit"
                disabled={isPending || !input.trim()}
                className="px-5 py-3 bg-accent text-white text-sm rounded-xl font-semibold tracking-wide hover:bg-accent-hover transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
              >
                Send
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
