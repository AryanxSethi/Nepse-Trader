import { useState, useRef, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useLLMAsk } from '../hooks/useLLMQuery'
import type { ParsedResult } from '../hooks/useLLMQuery'
import { ChatIcon, BrainIcon, CloseIcon } from './Icons'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

interface QuickQuery {
  label: string
  query: string
}

interface Props {
  symbol?: string
  title?: string
  welcomeMessage?: string
  quickQueries?: QuickQuery[]
  onSubmit?: (query: string) => Promise<string | null>
  onParsedResult?: (result: ParsedResult) => void
}

const DEFAULT_WELCOME = 'Ask me anything about NEPSE stocks — compare companies, check technical indicators, or get market insights.'

function sanitize(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
  }
  return text.replace(/[&<>"']/g, (c) => map[c])
}

function formatResponse(text: string): string {
  const escaped = sanitize(text)
  let formatted = escaped
  formatted = formatted.replace(/\*\*(.+?)\*\*/g, '$1')
  formatted = formatted.replace(/__(.+?)__/g, '$1')
  formatted = formatted.replace(/^### (.+)$/gm, '<div class="text-xs font-semibold text-text mt-2 mb-1">$1</div>')
  formatted = formatted.replace(/^- (.+)$/gm, '<span class="block text-text-muted">\u2022 $1</span>')
  formatted = formatted.replace(/\n{2,}/g, '<div class="h-2"></div>')
  formatted = formatted.replace(/\n/g, '<br/>')
  return formatted
}

export default function QuestionInput({ symbol, title, welcomeMessage, quickQueries, onSubmit, onParsedResult }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [showChat, setShowChat] = useState(false)
  const [loadingPhase, setLoadingPhase] = useState(0)
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set())
  const [customLoading, setCustomLoading] = useState(false)
  const { mutate, isPending, data, error, reset } = useLLMAsk()
  const listRef = useRef<HTMLDivElement>(null)
  const initialized = useRef(false)
  const loadingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const isProcessing = isPending || customLoading
  const welcomeRef = useRef(welcomeMessage ?? DEFAULT_WELCOME)
  welcomeRef.current = welcomeMessage ?? DEFAULT_WELCOME

  useEffect(() => {
    if (!initialized.current && symbol) {
      const stored = localStorage.getItem('nepse-chat-history')
      if (stored) {
        try { setMessages(JSON.parse(stored)) } catch {}
      }
      setMessages((prev) => {
        if (prev.length === 0) return [{ id: crypto.randomUUID(), role: 'assistant', content: `Selected **${symbol}**. ${welcomeRef.current}` }]
        return prev
      })
      initialized.current = true
    }
  }, [symbol])

  const clearHistory = useCallback(() => {
    setMessages([])
    localStorage.removeItem('nepse-chat-history')
  }, [])

  const onParsedResultRef = useRef(onParsedResult)
  onParsedResultRef.current = onParsedResult

  useEffect(() => {
    if (data) {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'assistant', content: data.answer }])
      if (onParsedResultRef.current && (data.symbol || data.suggested_page)) {
        onParsedResultRef.current({
          symbol: data.symbol,
          symbols: data.symbols,
          start_date: data.start_date,
          end_date: data.end_date,
          symbol_match_type: data.symbol_match_type,
          suggested_page: data.suggested_page,
        })
      }
      reset()
      setLoadingPhase(0)
      if (loadingTimerRef.current) { clearInterval(loadingTimerRef.current); loadingTimerRef.current = null }
    }
  }, [data, reset])

  useEffect(() => {
    if (error) {
      setMessages((prev) => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Unable to reach the AI assistant. Ensure Ollama is running with the LLM model.',
      }])
      reset()
      setLoadingPhase(0)
      if (loadingTimerRef.current) { clearInterval(loadingTimerRef.current); loadingTimerRef.current = null }
    }
  }, [error, reset])

  useEffect(() => {
    if (isPending && !onSubmit) {
      setLoadingPhase(1)
      const start = Date.now()
      loadingTimerRef.current = setInterval(() => {
        const elapsed = (Date.now() - start) / 1000
        if (elapsed > 6) setLoadingPhase(4)
        else if (elapsed > 3) setLoadingPhase(3)
        else if (elapsed > 1) setLoadingPhase(2)
      }, 500)
    }
    return () => {
      if (loadingTimerRef.current) { clearInterval(loadingTimerRef.current); loadingTimerRef.current = null }
    }
  }, [isPending, onSubmit])

  useEffect(() => {
    try {
      localStorage.setItem('nepse-chat-history', JSON.stringify(messages))
    } catch (e) {
      console.warn('Failed to persist chat history:', e)
    }
  }, [messages])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loadingPhase, isProcessing])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isProcessing) return
    const q = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', content: q }])

    if (onSubmit) {
      setCustomLoading(true)
      setLoadingPhase(1)
      const start = Date.now()
      const interval = setInterval(() => {
        const elapsed = (Date.now() - start) / 1000
        if (elapsed > 6) setLoadingPhase(4)
        else if (elapsed > 3) setLoadingPhase(3)
        else if (elapsed > 1) setLoadingPhase(2)
      }, 500)
      try {
        const answer = await onSubmit(q)
        if (answer !== null) {
          setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'assistant', content: answer }])
        }
      } catch {
        setMessages((prev) => [...prev, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Unable to fetch answer. Please try again.',
        }])
      } finally {
        setCustomLoading(false)
        setLoadingPhase(0)
        clearInterval(interval)
      }
    } else {
      mutate(q)
    }
  }

  const handleQuickQuery = (query: string) => {
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', content: query }])
    if (onSubmit) {
      setCustomLoading(true)
      setLoadingPhase(1)
      const start = Date.now()
      const interval = setInterval(() => {
        const elapsed = (Date.now() - start) / 1000
        if (elapsed > 6) setLoadingPhase(4)
        else if (elapsed > 3) setLoadingPhase(3)
        else if (elapsed > 1) setLoadingPhase(2)
      }, 500)
      onSubmit(query).then((answer) => {
        if (answer !== null) {
          setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'assistant', content: answer }])
        }
      }).catch(() => {
        setMessages((prev) => [...prev, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Unable to fetch answer. Please try again.',
        }])
      }).finally(() => {
        setCustomLoading(false)
        setLoadingPhase(0)
        clearInterval(interval)
      })
    } else {
      mutate(query)
    }
  }

  const toggleExpand = (idx: number) => {
    setExpandedMessages((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  const loadingLabels = ['', 'Searching symbols...', 'Analyzing market data...', 'Generating response...', 'Still generating...']

  const chatTitle = title || 'AI Analyst'
  const hasMessages = messages.length > 0
  const showQuickQueries = Boolean(quickQueries?.length) && !hasMessages && !isProcessing

  if (!showChat) {
    return (
      <button
        onClick={() => { setShowChat(true); if (!initialized.current) {     setMessages([{ id: crypto.randomUUID(), role: 'assistant', content: welcomeRef.current }]); initialized.current = true } }}
        className="w-full rounded-xl bg-surface-card border border-border p-3 flex items-center gap-2 hover:bg-surface-hover transition-colors text-left"
      >
        <ChatIcon size={16} className="text-accent shrink-0" />
        <span className="text-xs text-text-muted">Ask the AI analyst ...</span>
      </button>
    )
  }

  return (
    <div className="rounded-xl bg-surface-card border border-border flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <div className="flex items-center gap-1.5">
          <BrainIcon size={14} className="text-accent" />
          <span className="text-xs font-medium text-text">{chatTitle}</span>
          {messages.length > 0 && (
            <span className="text-[10px] text-text-muted ml-1">({messages.filter(m => m.role === 'user').length})</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button onClick={clearHistory} className="text-[10px] text-text-muted hover:text-text px-1.5 py-0.5 rounded hover:bg-surface-hover transition-colors" title="Clear history">
              Clear
            </button>
          )}
          <button onClick={() => setShowChat(false)} className="text-text-muted hover:text-text transition-colors">
            <CloseIcon size={14} />
          </button>
        </div>
      </div>

      <div ref={listRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-2 scroll-smooth min-h-[120px]">
        {messages.map((msg, i) => {
          const isLong = msg.content.length > 300
          const isExpanded = expandedMessages.has(i)
          const displayContent = isLong && !isExpanded ? msg.content.slice(0, 300) + '...' : msg.content

          return (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : ''}`}
            >
              {msg.role === 'assistant' && <BrainIcon size={14} className="text-accent shrink-0 mt-1" />}
              <div className={`rounded-lg px-3 py-2 text-xs leading-relaxed max-w-[85%] ${
                msg.role === 'user'
                  ? 'bg-accent/15 text-text'
                  : 'bg-surface-hover text-text'
              }`}>
                <div
                  className="prose-custom"
                  dangerouslySetInnerHTML={{ __html: formatResponse(displayContent) }}
                />
                {isLong && (
                  <button
                    onClick={() => toggleExpand(i)}
                    className="text-accent hover:text-accent-hover text-[10px] mt-1 font-medium transition-colors"
                  >
                    {isExpanded ? 'Show less' : 'Show more'}
                  </button>
                )}
              </div>
            </motion.div>
          )
        })}

        {showQuickQueries && quickQueries && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: 0.1 }}
            className="flex flex-wrap gap-1.5 pt-1 pb-2"
          >
            {quickQueries.map((qq) => (
              <button
                key={qq.label}
                onClick={() => handleQuickQuery(qq.query)}
                className="px-2.5 py-1 rounded-lg bg-accent/10 border border-accent/20 text-[11px] text-accent hover:bg-accent/15 hover:border-accent/30 transition-all font-medium"
              >
                {qq.label}
              </button>
            ))}
          </motion.div>
        )}

        {isProcessing && (
          <div className="flex gap-2">
            <BrainIcon size={14} className="text-accent shrink-0 mt-1" />
            <div className="rounded-lg px-3 py-2 bg-surface-hover space-y-1.5">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" />
                <span className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0.15s' }} />
                <span className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0.3s' }} />
              </div>
              {loadingPhase > 0 && (
                <p className="text-[10px] text-text-muted animate-fade-in">{loadingLabels[loadingPhase]}</p>
              )}
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex items-center gap-2 px-3 py-2 border-t border-border flex-shrink-0 max-sm:px-2 max-sm:py-1.5">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={symbol ? `Ask about ${symbol}...` : "Ask about stocks..."}
          className="flex-1 bg-surface-hover text-text text-xs rounded-lg px-3 py-2 border border-border outline-none focus:border-accent/50 transition-colors placeholder-text-muted/40"
        />
        <button
          type="submit"
          disabled={isProcessing || !input.trim()}
          className="px-3 py-2 bg-accent text-white text-xs rounded-lg font-medium hover:bg-accent-hover transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0 flex items-center gap-1 max-sm:px-2 max-sm:py-1.5"
        >
          {isProcessing ? (
            <>
              <span className="w-1 h-1 bg-white rounded-full animate-pulse" />
              <span className="w-1 h-1 bg-white rounded-full animate-pulse" style={{ animationDelay: '0.15s' }} />
              <span className="w-1 h-1 bg-white rounded-full animate-pulse" style={{ animationDelay: '0.3s' }} />
            </>
          ) : (
            'Send'
          )}
        </button>
      </form>
    </div>
  )
}