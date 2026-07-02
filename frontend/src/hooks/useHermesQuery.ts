import { useState, useRef, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'

export interface AskResponse {
  answer: string
  suggested_page?: string
  symbol?: string
  symbol_match_type?: string
  start_date?: string
  end_date?: string
}

export interface StreamCallbacks {
  onToken: (token: string) => void
  onMeta: (meta: Partial<AskResponse>) => void
  onDone: (fullAnswer: string) => void
  onError: (error: Error) => void
}

export function useHermesStream() {
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const stream = useCallback(async (question: string, callbacks: StreamCallbacks) => {
    setIsPending(true)
    setError(null)

    const controller = new AbortController()
    abortRef.current = controller

    const timeoutId = setTimeout(() => controller.abort(), 30000)

    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal: controller.signal,
      })

      if (!res.ok) throw new Error('Failed to get answer')
      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullAnswer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const msg = JSON.parse(line)
            if (msg.type === 'meta') {
              callbacks.onMeta(msg)
            } else if (msg.type === 'token') {
              fullAnswer += msg.token
              callbacks.onToken(msg.token)
            } else if (msg.type === 'done') {
              callbacks.onDone(fullAnswer)
            }
          } catch {
          }
        }
      }

      // Process remaining buffer
      if (buffer.trim()) {
        try {
          const msg = JSON.parse(buffer)
          if (msg.type === 'token') {
            fullAnswer += msg.token
            callbacks.onToken(msg.token)
          } else if (msg.type === 'done') {
            callbacks.onDone(fullAnswer)
          }
        } catch {
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        callbacks.onToken('Request timed out. Please try a simpler question.')
        callbacks.onDone(fullAnswer)
        return
      }
      if (err.name !== 'AbortError') {
        setError(err)
        callbacks.onError(err)
      }
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
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
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
      if (!line.trim()) continue
      try {
        const msg = JSON.parse(line)
        if (msg.type === 'meta') {
          meta = msg
        } else if (msg.type === 'token') {
          answer += msg.token
        }
      } catch {}
    }
  }

  return { answer, ...meta }
}

export function useHermesAsk() {
  return useMutation<AskResponse, Error, string>({
    mutationFn: collectAnswer,
  })
}
