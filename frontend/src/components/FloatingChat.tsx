import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useHermesStream } from '../hooks/useHermesQuery'
import { ChatIcon, BrainIcon, CloseIcon } from './Icons'

interface ParsedResult {
  symbol?: string
  start_date?: string
  end_date?: string
}

interface Props {
  symbol?: string
  onParsedResult?: (result: ParsedResult) => void
}

export default function FloatingChat({ symbol, onParsedResult }: Props) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([])
  const [input, setInput] = useState('')
  const [streamingContent, setStreamingContent] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const { stream, isPending, error } = useHermesStream()
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, streamingContent, isStreaming])

  useEffect(() => {
    if (error && !isStreaming) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'Unable to reach the AI assistant. Make sure Ollama or OpenRouter is configured.',
      }])
    }
  }, [error, isStreaming])

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isPending) return
    const q = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: q }])

    setIsStreaming(true)
    setStreamingContent('')

    stream(q, {
      onToken: (token) => {
        setStreamingContent((prev) => prev + token)
      },
      onMeta: (meta) => {
        if (onParsedResult && (meta.symbol || meta.suggested_page)) {
          onParsedResult({
            symbol: meta.symbol,
            start_date: meta.start_date,
            end_date: meta.end_date,
          })
        }
      },
      onDone: (fullAnswer) => {
        setMessages((prev) => [...prev, { role: 'assistant', content: fullAnswer }])
        setStreamingContent('')
        setIsStreaming(false)
      },
      onError: () => {
        setMessages((prev) => [...prev, {
          role: 'assistant',
          content: 'Unable to reach the AI assistant. Make sure Ollama or OpenRouter is configured.',
        }])
        setStreamingContent('')
        setIsStreaming(false)
      },
    })
  }, [input, isPending, stream, onParsedResult])

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
            <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
              <div className="flex items-center gap-2">
                <BrainIcon size={16} className="text-accent" />
                <span className="text-sm font-semibold text-text">AI Analyst</span>
              </div>
              <button onClick={() => setOpen(false)} className="text-text-muted hover:text-text transition-colors p-1">
                <CloseIcon size={16} />
              </button>
            </div>

            <div ref={listRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scroll-smooth">
              {messages.length === 0 && !isStreaming && (
                <div className="text-center py-8">
                  <BrainIcon size={32} className="text-accent/40 mx-auto mb-3" />
                  <p className="text-sm text-text-muted">
                    Ask me anything about NEPSE stocks — compare companies, check technical indicators, or get market insights.
                  </p>
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'assistant' && <BrainIcon size={14} className="text-accent shrink-0 mt-1" />}
                  <div className={`rounded-lg px-3 py-2 text-sm leading-relaxed max-w-[85%] ${
                    msg.role === 'user' ? 'bg-accent/15 text-text' : 'bg-surface-hover text-text'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {isStreaming && (
                <div className="flex gap-2">
                  <BrainIcon size={14} className="text-accent shrink-0 mt-1" />
                  <div className="rounded-lg px-3 py-2 text-sm leading-relaxed max-w-[85%] bg-surface-hover text-text">
                    {streamingContent || (
                      <div className="flex gap-1 py-1">
                        <span className="w-2 h-2 bg-accent rounded-full animate-pulse" />
                        <span className="w-2 h-2 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0.15s' }} />
                        <span className="w-2 h-2 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0.3s' }} />
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            <form onSubmit={handleSubmit} className="flex items-center gap-2 px-4 py-3 border-t border-border shrink-0">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={symbol ? `Ask about ${symbol}...` : 'Ask about stocks...'}
                className="flex-1 bg-surface-hover text-text text-sm rounded-xl px-4 py-2.5 border border-border outline-none focus:border-accent/50 transition-colors placeholder-text-muted/40"
              />
              <button
                type="submit"
                disabled={isPending || !input.trim()}
                className="px-4 py-2.5 bg-accent text-white text-sm rounded-xl font-medium hover:bg-accent-hover transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
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
