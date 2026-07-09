const DEFAULT_TIMEOUT = 30000

/** Error returned by the API on non-2xx responses. */
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

/** Error for network-level failures (e.g. no connection). */
export class NetworkError extends ApiError {
  constructor(message: string) {
    super(message)
    this.name = 'NetworkError'
  }
}

/** Error thrown when a request exceeds the timeout. */
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

/** Perform a GET request. */
export async function apiGet<T>(path: string, opts?: FetchOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'GET' })
}

/** Perform a POST request. */
export async function apiPost<T>(path: string, body?: unknown, opts?: FetchOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'POST', body })
}

/** Perform a POST request and return the raw Response for streaming consumption. */
export async function apiPostStream(path: string, body?: unknown, opts?: FetchOptions): Promise<Response> {
  return requestRaw(path, { ...opts, method: 'POST', body })
}

/** Perform a DELETE request. */
export async function apiDelete<T>(path: string, opts?: FetchOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'DELETE' })
}

/** Perform a PUT request. */
export async function apiPut<T>(path: string, body?: unknown, opts?: FetchOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'PUT', body })
}

async function requestRaw(path: string, opts?: FetchOptions): Promise<Response> {
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

    const res = await fetch(path, {
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

    return res
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (e instanceof DOMException && e.name === 'AbortError') {
      if (opts?.signal?.aborted) throw e
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

async function request<T>(path: string, opts?: FetchOptions): Promise<T> {
  const res = await requestRaw(path, opts)
  return res.json() as Promise<T>
}

function anySignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController()
  for (const sig of signals) {
    if (sig.aborted) {
      controller.abort(sig.reason)
      break
    }
    sig.addEventListener('abort', () => controller.abort(sig.reason), { once: true })
  }
  return controller.signal
}
