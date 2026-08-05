"""Fuzzy symbol search over the securities list using RapidFuzz.

Scoring strategy
----------------
* Exact match → score 1.0
* Symbol prefix match → score 0.98
* Fuzzy WRatio (len(query) >= 5) or ratio (len(query) < 5) → score 0.50–0.97
* Name substring (len(query) >= 5) → score 0.30
"""

import re
import asyncio
from datetime import timedelta, date
from rapidfuzz import process, fuzz


SECURITY_CACHE: list[dict] = []
security_cache_lock = asyncio.Lock()


async def set_security_cache(securities: list[dict]):
    """Replace the in-memory security cache with a fresh list."""
    global SECURITY_CACHE
    async with security_cache_lock:
        SECURITY_CACHE = securities


async def fuzzy_search(query: str, limit: int = 20) -> list[dict]:
    """Search securities by symbol (exact → prefix → fuzzy) or by name substring.

    Returns up to *limit* results sorted by relevance, each with *symbol*,
    *name*, *match_type*, and *score* (0–1.0).
    """
    async with security_cache_lock:
        cache = list(SECURITY_CACHE)
    if not cache or not query or not query.strip():
        return []

    q = query.strip().upper()
    exact = [s for s in cache if s["symbol"] == q]
    if exact:
        return [{**exact[0], "match_type": "exact", "score": 1.0}]

    prefix_matches = [s for s in cache if s["symbol"].startswith(q)]
    if prefix_matches:
        return [{**s, "match_type": "prefix", "score": 0.98} for s in prefix_matches[:limit]]

    choices = {s["symbol"]: s["symbol"] for s in cache}
    if len(q) < 5:
        results = process.extract(q, choices, scorer=fuzz.ratio, limit=limit)
        min_score = 60
    else:
        results = process.extract(q, choices, scorer=fuzz.WRatio, limit=limit)
        min_score = 50

    output = []
    for match, score, _ in results:
        if score < min_score:
            continue
        for s in cache:
            if s["symbol"] == match:
                output.append({**s, "match_type": "fuzzy", "score": round(score / 100, 2)})
                break
    if not output and len(q) >= 5:
        name_matches = [s for s in cache if q in s["name"].upper()]
        if name_matches:
            return [{**s, "match_type": "name", "score": 0.95} for s in name_matches[:limit]]
    return output


def parse_date_query(text: str) -> dict:
    """Extract a date range from a natural-language query string.

    Handles patterns like "past 30 days", "last 2 months", "1y", "ytd", "max".
    Returns ``{"start": date | None, "end": date | None}``.
    """
    text = text.strip().lower()
    today = date.today()

    patterns = [
        (r"past\s+(\d+)\s+day", lambda m: today - timedelta(days=int(m.group(1)))),
        (r"past\s+(\d+)\s+week", lambda m: today - timedelta(weeks=int(m.group(1)))),
        (r"past\s+(\d+)\s+month", lambda m: today - timedelta(days=int(m.group(1)) * 30)),
        (r"past\s+(\d+)\s+year", lambda m: today - timedelta(days=int(m.group(1)) * 365)),
        (r"last\s+(\d+)\s+day", lambda m: today - timedelta(days=int(m.group(1)))),
        (r"last\s+(\d+)\s+week", lambda m: today - timedelta(weeks=int(m.group(1)))),
        (r"last\s+(\d+)\s+month", lambda m: today - timedelta(days=int(m.group(1)) * 30)),
        (r"last\s+(\d+)\s+year", lambda m: today - timedelta(days=int(m.group(1)) * 365)),
        (r"(\d+)\s*(w|m|o|y)", lambda m: {
            "w": today - timedelta(weeks=int(m.group(1))),
            "m": today - timedelta(days=int(m.group(1)) * 30),
            "o": today - timedelta(days=int(m.group(1)) * 30),
            "y": today - timedelta(days=int(m.group(1)) * 365),
        }.get(m.group(2), today - timedelta(days=90))),
    ]

    if "ytd" in text or "year to date" in text:
        return {"start": date(today.year, 1, 1), "end": today}
    if "max" in text or "all" in text:
        return {"start": date(2020, 1, 1), "end": today}

    for pattern, resolver in patterns:
        m = re.search(pattern, text)
        if m:
            start = resolver(m)
            if callable(start):
                start = start(m)
            if isinstance(start, timedelta):
                start = today - start
            return {"start": start, "end": today}

    return {}


async def extract_symbols(text: str) -> list[str]:
    """Extract multiple stock symbols from a query for comparison.
    Handles: 'compare NABIL and MKJC', 'NABIL vs MKJC', 'NABIL, MKJC'
    """
    text_upper = text.upper().strip()
    
    for sep in [' AND ', ' VS ', ' VERSUS ', ' COMPARED TO ']:
        if sep in text_upper:
            parts = text_upper.split(sep)
            symbols = []
            for part in parts:
                cleaned = re.sub(r"[^a-zA-Z0-9 ]", "", part).strip()
                if cleaned:
                    s = await fuzzy_search(cleaned)
                    if s:
                        symbols.append(s[0]["symbol"])
            if len(symbols) >= 2:
                return symbols[:5]
    
    if ',' in text_upper:
        parts = [p.strip() for p in text_upper.split(',') if p.strip()]
        symbols = []
        for part in parts:
            cleaned = re.sub(r"[^a-zA-Z0-9 ]", "", part).strip()
            if cleaned:
                s = await fuzzy_search(cleaned)
                if s:
                    symbols.append(s[0]["symbol"])
        if len(symbols) >= 2:
            return symbols[:5]
    
    cleaned = re.sub(r"\b(rsi|macd|sma|price|ltp|current|rate|value|compare|chart|of|the|a|an|is|what|how|show|me|for|in|to|and|vs|top|gainers|losers|today|market|overview|summary|indices|index|best|worst|nepse|nepal|sensitive|float|stock|stocks|trading|start|do|does|did|has|have|been|like|know|tell|give|list|all|most|recent|last|past|date|time|above|below|over|under|with|without|now|level|benchmark|much|hello|hi|hey|thanks|thank|bye|goodbye|namaste|morning|evening|okay|ok|yes|no|sure|please|just|there|so|well|then|see|open|close|high|low|volume|turnover|status|live|kati|cha|chha|ho|ke|yo|ko|ma|ra|pani|paryo)\b", "", text_upper, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^a-zA-Z0-9 ]", "", cleaned).strip()
    words = [w for w in cleaned.split() if len(w) > 1]
    if words and len(words) <= 3 and sum(len(w) for w in words) <= 20:
        candidate = " ".join(words)
        if re.match(r'^[0-9 ]+$', candidate):
            return []
        s = await fuzzy_search(candidate)
        if s:
            return [s[0]["symbol"]]
    
    return []


async def parse_query(text: str) -> dict:
    """Parse a natural-language query into a symbol, date range, and suggestions.

    Returns ``{"symbol": str | None, "start": date, "end": date, "suggestions": list}``.
    Falls back to a 30-day window when no date is extracted.
    """
    result = {"symbol": None, "start": None, "end": None, "suggestions": []}

    date_info = parse_date_query(text)
    result["start"] = date_info.get("start")
    result["end"] = date_info.get("end")

    clean = re.sub(r"(past|last|for|of|from|to|show|me|the)\s*\d*\s*(day|week|month|year|ytd|max|all)", "", text, flags=re.IGNORECASE)
    clean = re.sub(r"\b(hello|hi|hey|thanks|thank|bye|goodbye|namaste|please|just|there|okay|ok|sure|yes|no|so|well|then|now)\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\d{4}[\-/]\d{2}[\-/]\d{2}", "", clean)
    clean = re.sub(r"\d{2}[\-/]\d{2}[\-/]\d{4}", "", clean)
    clean = re.sub(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*\d{0,4}", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"[^a-zA-Z0-9 ]", "", clean).strip()

    words = [w for w in clean.split() if len(w) > 1]
    candidates = " ".join(words) if words else ""

    if candidates and len(candidates) <= 25:
        suggestions = await fuzzy_search(candidates)
        if suggestions:
            result["symbol"] = suggestions[0]["symbol"]
            result["suggestions"] = suggestions

    if not result["start"]:
        result["start"] = today = date.today() - timedelta(days=30)
        result["end"] = date.today()

    return result
