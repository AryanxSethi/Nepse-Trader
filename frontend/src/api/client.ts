const API_BASE = ''

const DEFAULT_TIMEOUT = 30000

export class ApiError extends Error {
  status?: number
  response?: Response

  constructor(
    message: string,
    status?: number,
    response?: Response,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.response = response
  }
}

export class NetworkError extends ApiError {
  constructor(message: string) {
    super(message)
    this.name = 'NetworkError'
  }
}

export class TimeoutError extends ApiError {
  constructor() {
    super('Request timed out')
    this.name = 'TimeoutError'
  }
}

interface FetchOptions {
  timeout?: number
  signal?: AbortSignal
  method?: string
  body?: unknown
}

export async function apiGet<T>(path: string, opts?: FetchOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'GET' })
}

export async function apiPost<T>(path: string, body?: unknown, opts?: FetchOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'POST', body })
}

export async function apiDelete<T>(path: string, opts?: FetchOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'DELETE' })
}

export async function apiPut<T>(path: string, body?: unknown, opts?: FetchOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'PUT', body })
}

async function request<T>(path: string, opts?: FetchOptions): Promise<T> {
  const controller = new AbortController()
  const timeout = opts?.timeout ?? DEFAULT_TIMEOUT
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  const combinedSignal = opts?.signal
    ? anySignal([opts.signal, controller.signal])
    : controller.signal

  try {
    const headers: Record<string, string> = {}
    if (opts?.body && !(opts.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }

    const res = await fetch(`${API_BASE}${path}`, {
      method: opts?.method ?? 'GET',
      headers,
      body: opts?.body
        ? opts.body instanceof FormData
          ? opts.body
          : JSON.stringify(opts.body)
        : undefined,
      signal: combinedSignal,
    })

    if (!res.ok) {
      throw new ApiError(
        `HTTP ${res.status}: ${res.statusText}`,
        res.status,
        res,
      )
    }

    return res.json() as Promise<T>
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new TimeoutError()
    }
    if (e instanceof TypeError) {
      throw new NetworkError('Network error — check your connection')
    }
    throw new ApiError(String(e))
  } finally {
    clearTimeout(timeoutId)
  }
}

function anySignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController()
  for (const sig of signals) {
    if (sig.aborted) {
      controller.abort(sig.reason)
      return controller.signal
    }
    sig.addEventListener('abort', () => controller.abort(sig.reason), { once: true })
  }
  return controller.signal
}
