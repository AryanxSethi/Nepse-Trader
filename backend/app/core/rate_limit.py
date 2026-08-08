"""Prefix-based sliding-window rate limiting middleware."""

import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse

RATE_LIMIT_RULES: list[tuple[str, int, int]] = [
    ("/api/signals/generate", 3, 60),
    ("/api/backtest", 5, 60),
    ("/api/ask", 10, 60),
    ("/api/market", 30, 60),
    ("/api/portfolio", 20, 60),
]
"""Prefix-based rate limits: (path_prefix, max_requests, window_seconds)."""

_ip_buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


async def rate_limit_middleware(request: Request, call_next):
    """Sliding-window rate limiter keyed by client IP and request path."""
    path = request.url.path
    if path == "/api/health" or not path.startswith("/api"):
        return await call_next(request)

    max_reqs, window = 60, 60
    for prefix, m, w in RATE_LIMIT_RULES:
        if path.startswith(prefix):
            max_reqs, window = m, w
            break

    ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _ip_buckets[ip][path]
    cutoff = now - window
    bucket[:] = [t for t in bucket if t > cutoff]

    # Bounded eviction: when the bucket map exceeds 1024 client IPs, drop
    # everything except the current client so memory cannot grow unbounded.
    if len(_ip_buckets) > 1024:
        for client_ip in [i for i in _ip_buckets if i != ip]:
            del _ip_buckets[client_ip]

    if len(bucket) >= max_reqs:
        retry_after = int(bucket[0] + window - now) if bucket else int(window)
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
            headers={"Retry-After": str(retry_after)},
        )

    bucket.append(now)
    return await call_next(request)