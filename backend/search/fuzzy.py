import re
from datetime import timedelta, date
from rapidfuzz import process, fuzz


SECURITY_CACHE = []


def set_security_cache(securities: list[dict]):
    global SECURITY_CACHE
    SECURITY_CACHE = securities


def fuzzy_search(query: str, limit: int = 20) -> list[dict]:
    if not SECURITY_CACHE or not query or not query.strip():
        return []

    q = query.strip().upper()
    exact = [s for s in SECURITY_CACHE if s["symbol"] == q]
    if exact:
        return [{**exact[0], "match_type": "exact", "score": 1.0}]

    name_matches = [s for s in SECURITY_CACHE if q in s["name"].upper()]
    if name_matches:
        return [{**s, "match_type": "name", "score": 0.95} for s in name_matches[:limit]]

    choices = {s["symbol"]: s["symbol"] for s in SECURITY_CACHE}
    results = process.extract(q, choices, scorer=fuzz.WRatio, limit=limit)

    output = []
    for match, score, _ in results:
        if score < 50:
            continue
        for s in SECURITY_CACHE:
            if s["symbol"] == match:
                output.append({**s, "match_type": "fuzzy", "score": round(score / 100, 2)})
                break
    return output


def parse_date_query(text: str) -> dict:
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


def extract_symbols(text: str) -> list[str]:
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
                    s = fuzzy_search(cleaned)
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
                s = fuzzy_search(cleaned)
                if s:
                    symbols.append(s[0]["symbol"])
        if len(symbols) >= 2:
            return symbols[:5]
    
    cleaned = re.sub(r"\b(rsi|macd|sma|price|ltp|current|rate|value|compare|chart|of|the|a|an|is|what|how|show|me|for|in|to|and|vs|top|gainers|losers|today|market|overview|summary|indices|best|worst|nepse|nepal|stock|stocks|trading|start|do|does|did|has|have|been|like|know|tell|give|list|all|most|recent|last|past|date|time|above|below|over|under|with|without)\b", "", text_upper, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^a-zA-Z0-9 ]", "", cleaned).strip()
    words = [w for w in cleaned.split() if len(w) > 1]
    if words and len(words) <= 3 and sum(len(w) for w in words) <= 20:
        candidate = " ".join(words)
        if re.match(r'^[0-9 ]+$', candidate):
            return []
        s = fuzzy_search(candidate)
        if s:
            return [s[0]["symbol"]]
    
    return []


def parse_query(text: str) -> dict:
    result = {"symbol": None, "start": None, "end": None, "suggestions": []}

    date_info = parse_date_query(text)
    result["start"] = date_info.get("start")
    result["end"] = date_info.get("end")

    clean = re.sub(r"(past|last|for|of|from|to|show|me|the)\s*\d*\s*(day|week|month|year|ytd|max|all)", "", text, flags=re.IGNORECASE)
    clean = re.sub(r"\d{4}[\-/]\d{2}[\-/]\d{2}", "", clean)
    clean = re.sub(r"\d{2}[\-/]\d{2}[\-/]\d{4}", "", clean)
    clean = re.sub(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*\d{0,4}", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"[^a-zA-Z0-9 ]", "", clean).strip()

    words = [w for w in clean.split() if len(w) > 1]
    candidates = " ".join(words) if words else ""

    if candidates and len(candidates) <= 25:
        suggestions = fuzzy_search(candidates)
        if suggestions:
            result["symbol"] = suggestions[0]["symbol"]
            result["suggestions"] = suggestions

    if not result["start"]:
        result["start"] = today = date.today() - timedelta(days=30)
        result["end"] = date.today()

    return result
