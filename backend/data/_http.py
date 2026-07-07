"""HTTP utilities for retryable GET requests and circuit breaker.

Provides *retry_get*, *retry_get_json*, *retry_get_text* with exponential
backoff, and a per-source *CircuitBreaker*.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger('http')

TIMEOUT_SEC = 15
MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 8.0


@dataclass
class FetchResult:
    """Result of a fetch operation with status, data, and metadata."""
    ok: bool
    data: Any = None
    source: str = ''
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    status_code: int = 0


def _build_error(source: str, exc: Exception) -> FetchResult:
    """Return a failed FetchResult and log the error."""
    msg = f'{type(exc).__name__}: {exc}'
    logger.warning('[%s] %s', source, msg)
    return FetchResult(ok=False, source=source, error=msg)


async def retry_get(
    url: str,
    *,
    source: str,
    params: dict | None = None,
    timeout: int = TIMEOUT_SEC,
    retries: int = MAX_RETRIES,
    client: httpx.AsyncClient | None = None,
) -> FetchResult:
    """GET with exponential backoff retry."""
    last_error: Exception | None = None
    close_client = client is None

    if client is None:
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    try:
        for attempt in range(1, retries + 1):
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    return FetchResult(
                        ok=True,
                        data=resp,
                        source=source,
                        status_code=200,
                    )
                last_error = httpx.HTTPStatusError(
                    f'HTTP {resp.status_code}', request=resp.request, response=resp
                )
                if attempt < retries:
                    delay = min(BASE_DELAY * (2 ** (attempt - 1)), MAX_DELAY)
                    logger.info('[%s] retry %d/%d after %ds (status %s)', source, attempt, retries, delay, resp.status_code)
                    await asyncio.sleep(delay)
                else:
                    logger.warning('[%s] exhausted %d retries, last status %s', source, retries, resp.status_code)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                last_error = exc
                if attempt < retries:
                    delay = min(BASE_DELAY * (2 ** (attempt - 1)), MAX_DELAY)
                    logger.info('[%s] retry %d/%d after %ds (%s)', source, attempt, retries, delay, type(exc).__name__)
                    await asyncio.sleep(delay)
                else:
                    logger.warning('[%s] exhausted %d retries, last error %s', source, retries, type(exc).__name__)

        return _build_error(source, last_error or RuntimeError('unknown error'))
    finally:
        if close_client:
            await client.aclose()


async def retry_get_json(
    url: str,
    *,
    source: str,
    params: dict | None = None,
    timeout: int = TIMEOUT_SEC,
    retries: int = MAX_RETRIES,
) -> FetchResult:
    """GET -> JSON with retry. Returns FetchResult with data as parsed JSON or None."""
    result = await retry_get(url, source=source, params=params, timeout=timeout, retries=retries)
    if not result.ok or result.data is None:
        return result

    resp: httpx.Response = result.data
    try:
        parsed = resp.json()
    except Exception as e:
        return _build_error(source, e)

    return FetchResult(ok=True, data=parsed, source=source, fetched_at=result.fetched_at)


async def retry_get_text(
    url: str,
    *,
    source: str,
    params: dict | None = None,
    timeout: int = TIMEOUT_SEC,
    retries: int = MAX_RETRIES,
) -> FetchResult:
    """GET -> text with retry."""
    result = await retry_get(url, source=source, params=params, timeout=timeout, retries=retries)
    if not result.ok or result.data is None:
        return result

    resp: httpx.Response = result.data
    return FetchResult(ok=True, data=resp.text, source=source, fetched_at=result.fetched_at)


class CircuitBreaker:
    """Per-source circuit breaker: after N consecutive failures, skip for cooloff seconds."""

    def __init__(self, threshold: int = 3, cooloff: float = 60.0):
        """Initialise the circuit breaker.

        Args:
            threshold: Consecutive failures before opening the circuit.
            cooloff: Seconds to stay open before allowing requests again.
        """
        self._threshold = threshold
        self._cooloff = cooloff
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}

    def record_success(self, source: str):
        """Reset failure count and close circuit for *source*."""
        self._failures.pop(source, None)
        self._open_until.pop(source, None)

    def record_failure(self, source: str):
        """Increment failure count; open circuit if threshold reached."""
        self._failures[source] = self._failures.get(source, 0) + 1
        if self._failures[source] >= self._threshold:
            until = asyncio.get_running_loop().time() + self._cooloff
            self._open_until[source] = until
            logger.warning('[%s] circuit opened for %.0fs', source, self._cooloff)

    def is_open(self, source: str) -> bool:
        """Check whether the circuit is currently open for *source*."""
        until = self._open_until.get(source)
        if until is None:
            return False
        if asyncio.get_running_loop().time() >= until:
            self._open_until.pop(source, None)
            self._failures.pop(source, None)
            logger.info('[%s] circuit closed (cooloff expired)', source)
            return False
        return True

    def status(self, source: str) -> str:
        """Return human-readable circuit breaker status for *source*."""
        if self.is_open(source):
            remaining = self._open_until.get(source, 0) - asyncio.get_running_loop().time()
            return f'open ({remaining:.0f}s remaining)'
        failures = self._failures.get(source, 0)
        if failures > 0:
            return f'degraded ({failures}/{self._threshold} failures)'
        return 'up'
