import { useState, useRef, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'

export interface AskResponse {
  answer: string
  suggested_page?: string
  symbol?: string
  symbols?: string[]
  symbol_match_type?: string
  fuzzy_suggestion?: { symbol: string; name: string; score?: number } | null
  start_date?: string
  end_date?: string
}

export interface ParsedResult {
  symbol?: string
  symbols?: string[]
  start_date?: string
  end_date?: string
  symbol_match_type?: string
  suggested_page?: string
}

export interface StreamCallbacks {
  onToken: (token: string) => void
  onMeta: (meta: Partial<AskResponse>) => void
  onDone: (fullAnswer: string) => void
  onError: (error: Error) => void
  onStatus?: (status: string) => void
}

/** Stream LLM answer tokens with real-time callbacks. */
export function useLLMStream() {
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const stream = useCallback(async (question: string, callbacks: StreamCallbacks) => {
    setIsPending(true)
    setError(null)

    const controller = new AbortController()
    abortRef.current = controller

    const timeoutId = setTimeout(() => controller.abort(), 180000)

    let fullAnswer = ''

    try {
      let history: { role: string; content: string }[] = []
      try {
        const stored = localStorage.getItem('nepse-chat-history')
        if (stored) history = JSON.parse(stored).slice(-6)
      } catch {}

      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, history }),
        signal: controller.signal,
      })

      if (!res.ok) throw new Error('Failed to get answer')
      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed) continue
          try {
            const msg = JSON.parse(trimmed)
            if (msg.type === 'meta') {
              callbacks.onMeta(msg)
            } else if (msg.type === 'token') {
              fullAnswer += msg.token
              callbacks.onToken(msg.token)
            } else if (msg.type === 'done') {
              callbacks.onDone(fullAnswer)
            } else if (msg.type === 'status' && callbacks.onStatus) {
              callbacks.onStatus(msg.status)
            }
          } catch (e) {
            console.warn('[useLLMStream] parse error on line:', trimmed.slice(0, 80), e)
          }
        }
      }

      if (buffer.trim()) {
        try {
          const msg = JSON.parse(buffer.trim())
          if (msg.type === 'token') {
            fullAnswer += msg.token
            callbacks.onToken(msg.token)
          } else if (msg.type === 'done') {
            callbacks.onDone(fullAnswer)
          } else if (msg.type === 'status' && callbacks.onStatus) {
            callbacks.onStatus(msg.status)
          }
        } catch (e) {
          console.warn('[useLLMStream] parse error on remaining buffer:', buffer.trim().slice(0, 80), e)
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        callbacks.onToken('Request timed out. Please try a simpler question.')
        callbacks.onDone(fullAnswer)
        return
      }
      setError(err instanceof Error ? err : new Error(String(err)))
      callbacks.onError(err instanceof Error ? err : new Error(String(err)))
    } finally {
      clearTimeout(timeoutId)
      setIsPending(false)
      abortRef.current = null
    }
  }, [])

  const cancel = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { stream, cancel, isPending, error }
}

async function collectAnswer(question: string): Promise<AskResponse> {
  let history: { role: string; content: string }[] = []
  try {
    const stored = localStorage.getItem('nepse-chat-history')
    if (stored) history = JSON.parse(stored).slice(-6)
  } catch {}

  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
  })
  if (!res.ok) throw new Error('Failed to get answer')
  if (!res.body) throw new Error('No response body')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let answer = ''
  let meta: Partial<AskResponse> = {}

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      try {
        const msg = JSON.parse(trimmed)
        if (msg.type === 'meta') {
          meta = msg
        } else if (msg.type === 'token') {
          answer += msg.token
        }
      } catch (e) {
        console.warn('[collectAnswer] parse error on line:', trimmed.slice(0, 80), e)
      }
    }
  }

  return { answer, ...meta }
}

/** Ask a question and get the full response via mutation. */
export function useLLMAsk() {
  return useMutation<AskResponse, Error, string>({
    mutationFn: collectAnswer,
  })
}
