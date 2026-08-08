"""Cache-Control header middleware for known static endpoints."""

CACHE_CONTROL_ROUTES = {
    "/api/ipos": "public, max-age=60",
    "/api/securities": "public, max-age=300",
    "/api/market/status": "public, max-age=30",
    "/api/brokers/top": "public, max-age=300",
    "/api/brokers/search": "public, max-age=300",
    "/api/sectors": "public, max-age=300",
}


async def add_cache_headers(request, call_next):
    """Add Cache-Control headers to responses for known static endpoints."""
    response = await call_next(request)
    path = request.url.path
    if path in CACHE_CONTROL_ROUTES:
        response.headers["Cache-Control"] = CACHE_CONTROL_ROUTES[path]
    return response