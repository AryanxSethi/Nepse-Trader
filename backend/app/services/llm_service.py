"""AI chat service — intent detection, small talk, context building, LLM streaming."""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

import httpx
import pandas as pd
from sqlalchemy import select

from app.analysis.indicators import compute_indicators, compute_signal
from app.core.config import OLLAMA_MODEL, OLLAMA_URL
from app.db.models import DailyPrice
from app.db.session import async_session
from app.providers.cache import data_cache_get, data_cache_set
from app.providers.yonep import fetch_indices, fetch_market_summary, fetch_top_stocks
from app.search.fuzzy import extract_symbols, fuzzy_search, parse_date_query
from app.services.live import _fetch_live_all
from app.services.state import merolagani_fetcher, sharesansar_fetcher

logger = logging.getLogger('services.llm')


def _strip_bold(t: str) -> str:
    """Strip Markdown bold formatting (**, __) from a string."""
    return re.sub(r'\*\*(.+?)\*\*', r'\1', re.sub(r'__(.+?)__', r'\1', t))


def _to_num(value) -> float | None:
    """Coerce a numeric field that may arrive as int, float, or str to float."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", "")
        return float(value)
    except (TypeError, ValueError):
        return None


GUIDE_SYSTEM_PROMPT = (
    "You are a NEPSE trading data analyst assistant. Your role is to analyze "
    "provided market data and explain what the numbers indicate.\n\n"
    "SCOPE:\n"
    "- Only answer NEPSE stocks, trading, investing, regulations, "
    "brokers, demat accounts, MeroShare, technical/fundamental analysis, fees, "
    "and taxes in Nepal.\n"
    "- If asked about anything else, politely decline.\n\n"
    "INDEX DISAMBIGUATION:\n"
    "- \"NEPSE\" (or \"NEPSE Index\") refers to the NEPSE market benchmark index — "
    "NOT a company stock.\n"
    "- \"Sensitive Index\", \"Float Index\", and all other sub-indices are also "
    "market indices, not stocks.\n"
    "- There is NO stock with the symbol \"NEPSE\". If the user asks about the "
    "index, use the PROVIDED DATA's index values — do NOT look for a company.\n"
    "- If no index data is provided, say \"Index data is not available right now.\"\n\n"
    "TONE & CONVERSATION:\n"
    "- Be friendly, warm, and approachable. You are a helpful assistant, not a data report.\n"
    "- Greetings (\"hi\", \"hello\", \"good morning\"): respond warmly and offer help.\n"
    "  Example: \"Hi! I can look up stock data, explain indicators, or give a market overview. What would you like to know?\"\n"
    "- \"Thank you\" / \"thanks\": respond \"You're welcome!\" and offer follow-up help.\n"
    "- \"Explain more\" / \"elaborate\" / \"tell me more about\": expand on your previous answer with additional detail or examples — do not just repeat the same info.\n"
    "- \"Please\": acknowledge politely in your response.\n"
    "- End every exchange with an offer for further help when appropriate.\n"
    "- Always maintain data accuracy — friendliness never means inventing data.\n\n"
    "CONVERSATION ENDING:\n"
    "- Recognize farewell intent when the user says phrases like:\n"
    "  \"thank you\", \"thanks\", \"dhanyabad\", \"bye\", \"goodbye\", \"see you\",\n"
    "  \"that's all\", \"that's all for now\", \"nothing more\", \"nothing else\",\n"
    "  \"nothing else for now\", \"no more questions\", \"all done\", \"i'm done\",\n"
    "  and similar closing phrases.\n"
    "- If the message is ONLY a closing (no new question or topic), respond\n"
    "  with a warm, final closing message and do NOT offer follow-up help.\n"
    "- The closing should be warm and brief, ending with the disclaimer on\n"
    "  its own line.\n"
    "- Examples:\n"
    "  User: \"That's all for now, thank you.\"\n"
    "  Assistant: \"Goodbye! Happy trading, and remember — the stock market "
    "involves risk. Invest wisely.\"\n\n"
    "  User: \"Nothing else.\"\n"
    "  Assistant: \"Goodbye! Wishing you successful investments. "
    "The stock market involves risk — this is not financial advice.\"\n\n"
    "GUIDELINES:\n"
    "1. Base ALL numerical claims on PROVIDED DATA. If a metric is not in the "
    "data, say 'not available' — never guess.\n"
    "2. You may explain what indicators suggest (e.g., 'RSI above 70 = overbought'), "
    "but note past patterns do not guarantee future results.\n"
    "3. Offer directional analysis based on data, framed as analysis not recommendation.\n"
    "4. ALWAYS include: 'The stock market involves risk. This is not financial advice.'\n"
    "5. Cite NEPSE as data source.\n"
    "6. If you don't know something, say so honestly.\n\n"
    "TYPOS AND FUZZY MATCHES:\n"
    "- Symbol suggestions are handled by the backend and will appear in PROVIDED DATA notes. "
    "Do NOT guess symbols from your own knowledge.\n"
    "- If PROVIDED DATA contains a note about a symbol match, use that suggested symbol.\n"
    "- ONLY ask for confirmation: 'I couldn't find that symbol. Did you mean X?'\n"
    "- Do NOT provide any data, analysis, or information about the suggested symbol.\n"
    "- Wait for the user to confirm before doing anything else.\n\n"
    "CONFIRMATIONS:\n"
    "- Example: 'Showing RIDI chart on the Trade page.'\n"
    "- Do NOT treat 'yes' as a new question or try to find another symbol.\n\n"
    "STRICT FORMAT RULES:\n"
    "- Start data-backed responses with a one-line market snapshot (NEPSE + Sensitive index).\n"
    "- For stock data: use a single compact line per stock.\n"
    "  Example: NABIL | NPR 485.20 | +2.15% | Vol: 52,341 | RSI: 32.5\n"
    "- For technical indicators: one bullet per indicator with brief interpretation "
    "(e.g. '- RSI 32.5: oversold territory').\n"
    "- For market overview: use section headers and short bullet lists.\n"
    "- MAXIMUM 12 lines. No paragraph longer than 2 sentences.\n"
    "- Do NOT use asterisks (**) or underscores (__) for formatting anywhere in your response.\n"
    "- End with the disclaimer on its own line."
)


def detect_intent(query: str, symbols: list[str]) -> str:
    """Classify a user query into one of: compare, indicator, price, overview, or guide."""
    q = query.lower()
    INDEX_NAMES = ["nepse", "sensitive index", "float index"]
    if any(idx in q for idx in INDEX_NAMES) and any(w in q for w in ["index", "what", "value", "current", "how", "today", "level", "benchmark", "market"]):
        return "overview"
    if len(symbols) >= 2:
        return "compare"
    if len(symbols) == 1 and any(w in q for w in ["rsi", "macd", "sma", "moving average", "bollinger", "atr", "adx", "indicator", "signal", "technical"]):
        return "indicator"
    if len(symbols) == 1 and any(w in q for w in ["price", "ltp", "current", "how much", "rate", "value", "chart", "show", "display"]):
        return "price"
    if any(w in q for w in ["market", "overview", "gainers", "losers", "indices", "summary", "top", "index"]):
        return "overview"
    return "guide"


INDEX_TOKENS = {
    "nepse", "sensitive", "float", "index", "indices", "banking", "hydropower",
    "development", "manufacturing", "microfinance", "finance", "mutual",
    "insurance", "nonlife", "debenture", "preference", "hotel", "trading",
    "tourism", "others",
}

_SMALL_TALK_FILLERS = re.compile(
    r"\b(please|just|there|so|well|then|now|again|help|doing|today)\b",
    re.IGNORECASE,
)
_SMALL_TALK_PATTERNS = {
    "farewell": re.compile(
        r"\b(bye+|goodbye|good\s+bye|see\s+you|take\s+care|that.?s\s+all|that.?s\s+it|"
        r"nothing\s+(?:more|else)|no\s+more\s+questions|all\s+done|i.?m\s+done|"
        r"farewell|goodnight|good\s+night)\b",
        re.IGNORECASE,
    ),
    "thanks": re.compile(
        r"\b(thank\s+you+\s+very\s+much|thank\s+you+|thanks+|thank\b|dhanyabad|"
        r"dhanyawad|thankful)\b",
        re.IGNORECASE,
    ),
    "ack": re.compile(
        r"^(?:ok+|okay|yes|yep|yeah|sure|alright|fine|got\s+it|understood|noted)[.!?]*$",
        re.IGNORECASE,
    ),
    "greeting": re.compile(
        r"\b(hi+|hello+|hey+|namaste+|greetings+|good\s+morning|good\s+afternoon|"
        r"good\s+evening|how\s+are\s+you|how\s+do\s+you\s+do)\b[.!?]*$",
        re.IGNORECASE,
    ),
}

SMALL_TALK_RESPONSES = {
    "greeting": "Hi! I can look up stock data, explain indicators, or give a market overview. What would you like to know?",
    "thanks": "You're welcome! Is there anything else you'd like to know?",
    "farewell": "Goodbye! Happy trading — the stock market involves risk. This is not financial advice.",
    "ack": "Got it! Is there anything else you'd like to know?",
}


def detect_small_talk(question: str) -> str | None:
    """Classify pure small talk (greeting/thanks/farewell/ack) needing no LLM or data."""
    if not question:
        return None
    q = _SMALL_TALK_FILLERS.sub("", question)
    q = re.sub(r"\s+", " ", q).strip()
    if not q:
        return None
    for kind in ("farewell", "thanks", "ack", "greeting"):
        if _SMALL_TALK_PATTERNS[kind].search(q):
            return kind
    return None


async def build_data_context(symbols: list[str]) -> str:
    """Build a formatted market-data context string for the AI assistant.

    Args:
        symbols: List of stock symbols to fetch data for (max 5).

    Returns:
        A multi-line string with LTP, change, sector, 52W range, and technical indicators.
    """
    if not symbols:
        return ""

    live = await _fetch_live_all()
    live_map = {c.get("symbol", "").upper(): c for c in live}
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    lines = [f"=== REAL MARKET DATA (retrieved {now_str} NST) ==="]

    try:
        indices_data = await fetch_indices()
        if indices_data:
            lines.append("\nMarket Snapshot:")
            for idx in indices_data:
                name = idx.get("index", "")
                val = _to_num(idx.get("currentValue"))
                chg = _to_num(idx.get("change", idx.get("perChange")))
                lines.append(f"  {name}: {val}" + (f" ({chg:+.2f}%)" if chg is not None else ""))
    except Exception as e:
        logger.warning("build_data_context: index fetch failed: %s", e)

    records_by_symbol = {}
    try:
        async with async_session() as session:
            rows = await session.execute(
                select(DailyPrice)
                .where(DailyPrice.symbol.in_([s.upper() for s in symbols[:5]]))
                .order_by(DailyPrice.symbol, DailyPrice.date.desc())
            )
            for r in rows.scalars().all():
                records_by_symbol.setdefault(r.symbol, []).append(r.to_dict())
    except Exception as e:
        logger.warning("build_data_context: DB query failed: %s", e)

    for sym in symbols[:5]:
        sym_u = sym.upper()
        l = live_map.get(sym_u, {})

        lines.append(f"\nStock: {sym_u}")
        ltp = _to_num(l.get("ltp"))
        lines.append(f"  LTP: NPR {ltp:,.2f}" if ltp is not None else "  LTP: not available")

        pct = _to_num(l.get("percent_change"))
        if pct is not None:
            sign = "+" if pct >= 0 else ""
            lines.append(f"  Change: {sign}{pct:.2f}%")
        prev_close = _to_num(l.get("previous_close"))
        if prev_close is not None:
            lines.append(f"  Prev Close: NPR {prev_close:,.2f}")
        high = _to_num(l.get("high"))
        low = _to_num(l.get("low"))
        if high is not None and low is not None:
            lines.append(f"  Day Range: NPR {low:,.2f} - NPR {high:,.2f}")
        vol = _to_num(l.get("volume"))
        if vol is not None:
            lines.append(f"  Volume: {int(vol):,}")
        turnover = _to_num(l.get("turnover"))
        if turnover is not None:
            lines.append(f"  Turnover: NPR {turnover:,.0f}")
        trades = _to_num(l.get("trades"))
        if trades is not None:
            lines.append(f"  Trades: {int(trades):,}")
        mcap = _to_num(l.get("market_cap"))
        if mcap is not None:
            lines.append(f"  Market Cap: NPR {mcap:,.2f}M")

        detail = None
        try:
            cb = merolagani_fetcher.circuit_breaker_status('merolagani')
            if cb != 'open':
                detail = await merolagani_fetcher.get_company_detail(sym_u)
        except Exception as e:
            logger.warning("build_data_context: Merolagani detail fetch failed for %s: %s", sym_u, e)
        if not detail:
            try:
                ss_detail = await sharesansar_fetcher.get_company_detail(sym_u)
                if ss_detail:
                    ph = ss_detail.get('price_header') or {}
                    info = ss_detail.get('company_info') or {}
                    if info.get('sector'):
                        detail = {'sector': info['sector']}
                    else:
                        detail = {}
                    if ph.get('high_52w') and ph.get('low_52w'):
                        detail['52w_high'] = str(ph['high_52w'])
                        detail['52w_low'] = str(ph['low_52w'])
                    if ph.get('avg_120d'):
                        detail['120d_avg'] = str(ph['avg_120d'])
                    if ph.get('avg_180d'):
                        detail['180d_avg'] = str(ph['avg_180d'])
            except Exception as e:
                logger.warning("build_data_context: Sharesansar detail fallback failed for %s: %s", sym_u, e)
        if detail:
            if detail.get("sector"):
                lines.append(f"  Sector: {detail['sector']}")
            if detail.get("52w_high") and detail.get("52w_low"):
                lines.append(f"  52W Range: NPR {detail['52w_low']} - NPR {detail['52w_high']}")
            if detail.get("120d_avg"):
                lines.append(f"  120D Avg: NPR {detail['120d_avg']}")
            if detail.get("180d_avg"):
                lines.append(f"  180D Avg: NPR {detail['180d_avg']}")
            if detail.get("1y_yield"):
                lines.append(f"  1Y Yield: {detail['1y_yield']}")

        try:
            records = records_by_symbol.get(sym_u, [])
            if len(records) >= 20:
                df = pd.DataFrame(records)
                indicators = compute_indicators(df)
                sig_type, confidence, reason = compute_signal(indicators)

                rsi = indicators.get("rsi")
                if rsi is not None:
                    lines.append(f"  RSI: {rsi:.1f}")

                macd = indicators.get("macd")
                macd_sig = indicators.get("macd_signal")
                if macd is not None and macd_sig is not None:
                    status = "Bullish" if macd > macd_sig else "Bearish"
                    lines.append(f"  MACD: {status} (MACD: {macd:.2f}, Signal: {macd_sig:.2f})")

                sma20 = indicators.get("sma20")
                if sma20 is not None:
                    lines.append(f"  SMA20: {sma20:.2f}")
                sma50 = indicators.get("sma50")
                if sma50 is not None:
                    lines.append(f"  SMA50: {sma50:.2f}")

                adx = indicators.get("adx")
                if adx is not None:
                    trend = "Strong" if adx >= 25 else "Weak"
                    lines.append(f"  ADX: {adx:.1f} ({trend} trend)")

                lines.append(f"  Signal: {sig_type} (confidence: {confidence}%)")
        except Exception:
            lines.append("  Technical indicators: not available")

    return "\n".join(lines)


async def _stream_llm(system_prompt: str, question: str, max_tokens: int, timeout_secs: int, history: list[dict] | None = None):
    """Stream tokens from the Ollama chat API as an async generator.

    Args:
        system_prompt: System-level instruction for the LLM.
        question: User question.
        max_tokens: Maximum tokens in the response.
        timeout_secs: HTTP request timeout.
        history: Optional conversation history (last 6 messages).

    Yields:
        Content tokens from the LLM response.
    """
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": question})

    try:
        async with httpx.AsyncClient(timeout=timeout_secs) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.5, "num_predict": max_tokens},
                },
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logger.error("Ollama stream failed: %s", e)
        yield ""  # Signal failure — caller will use fallback


async def generate_answer(question: str, history: list[dict] | None = None):
    """Generate a streaming answer for an AI chat request.

    Detects intent, builds data context, streams LLM tokens, and yields
    JSON events (status, token, meta, done) for the SSE response.

    Args:
        question: The user's question.
        history: Optional conversation history (last 6 messages).

    Yields:
        JSON-encoded SSE events.
    """
    question = question.strip()

    if not question:
        yield json.dumps({"type": "token", "token": "Please ask a question about NEPSE stocks or trading."}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"
        return

    small_talk = detect_small_talk(question)
    if small_talk:
        yield json.dumps({"type": "status", "status": "analyzing"}) + "\n"
        yield json.dumps({
            "type": "meta", "suggested_page": None, "symbol": None,
            "symbols": None, "symbol_match_type": None,
            "fuzzy_suggestion": None, "start_date": None, "end_date": None,
        }) + "\n"
        yield json.dumps({"type": "token", "token": SMALL_TALK_RESPONSES[small_talk]}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"
        return

    NON_NEPSE_TOPICS = [
        "recipe", "cook", "bake", "movie", "song", "music", "album",
        "weather", "climate", "sports", "football", "cricket", "goal",
        "game", "play", "video game", "political", "election", "party",
        "travel", "hotel", "restaurant", "fashion", "celebrity",
    ]
    ql = question.lower()
    if any(t in ql for t in NON_NEPSE_TOPICS):
        yield json.dumps({"type": "token", "token": "I can only answer questions about NEPSE trading and the Nepali stock market."}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"
        return

    yield json.dumps({"type": "status", "status": "analyzing"}) + "\n"

    chart_match = re.search(
        r'(?:(?:show|display)\s+)?(?:me\s+)?(?:the\s+)?'
        r'(?:graph|chart|plot|candlestick|candle|candles)\s+(?:of\s+)?'
        r'(?!.*(?:and|vs|versus))([A-Za-z]{2,10})\b',
        question, re.IGNORECASE
    )
    if not chart_match:
        chart_match = re.search(
            r'(?!.*(?:and|vs|versus))'
            r'([A-Za-z]{2,10})\s+(?:chart|graph|plot|candle|candlestick)\b',
            question, re.IGNORECASE
        )
    candidate = None
    if chart_match:
        candidate = chart_match.group(1).strip().upper()
        if candidate.lower() in INDEX_TOKENS:
            chart_match = None
            candidate = None
    if chart_match:
        found = await fuzzy_search(candidate)
        if found:
            symbols = [found[0]["symbol"]]
            intent = "price"
        else:
            symbols = await extract_symbols(question)
            intent = detect_intent(question, symbols)
    else:
        symbols = await extract_symbols(question)
        intent = detect_intent(question, symbols)

    chart_intent = bool(chart_match)

    date_info = parse_date_query(question)
    start_date = date_info.get("start")
    end_date = date_info.get("end")

    symbol = symbols[0] if symbols else None

    fuzzy_suggestion = None
    symbol_match_type = None
    raw_clean = re.sub(
        r'\b(show|display|me|chart|graph|plot|candle|candlestick|of|the|a|an|for|in|to|'
        r'and|vs|is|what|how|who|tell|give|list|know|my|are|can|do|does|did|has|have|'
        r'like|need|want|would|could|should|will|get|find|see|check|compare|market|overview|'
        r'summary|gainers|losers|top|today|index|indices|sector|sectors|signal|signals|'
        r'rsi|macd|sma|price|ltp|current|rate|value|nepse|nepal|sensitive|float|stock|stocks|'
        r'trading|best|worst|now|level|benchmark|much|whats|please|just|there|help|doing|'
        r'been|all|most|recent|last|past|date|time|above|below|over|under|with|without|'
        r'start|open|close|high|low|volume|turnover|status|live|'
        r'hello|hi|hey|thanks|thank|bye|goodbye|namaste|okay|ok|yes|no|sure|see|'
        r'morning|evening|kati|cha|chha|ho|ke|yo|ko|ma|ra|pani|paryo)\b',
        '', question, flags=re.IGNORECASE
    )
    raw_clean = re.sub(r'[^A-Za-z ]', '', raw_clean).strip().upper()
    words = [w for w in raw_clean.split() if len(w) > 1]
    if words:
        check = await fuzzy_search(words[0])
        if check:
            symbol_match_type = check[0].get("match_type")
            if symbol_match_type not in ("exact",):
                fuzzy_suggestion = check[0]

    suggested_page = None
    data_context = ""

    skip_data = chart_intent or bool(fuzzy_suggestion) or (intent == "compare" and len(symbols) >= 2)

    if symbols and not skip_data:
        ctx_key = "ctx_" + "_".join(sorted(symbols))
        cached = await data_cache_get(ctx_key)
        if cached:
            data_context = cached
        else:
            yield json.dumps({"type": "status", "status": "searching"}) + "\n"
            data_context = await build_data_context(symbols)
            if data_context:
                await data_cache_set(ctx_key, data_context)
    elif intent == "overview":
        yield json.dumps({"type": "status", "status": "searching"}) + "\n"
        try:
            tops, indices, summary = await asyncio.gather(
                fetch_top_stocks(), fetch_indices(), fetch_market_summary(), return_exceptions=True
            )
            lines = [f"=== MARKET OVERVIEW (retrieved {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC) ==="]
            if not isinstance(indices, Exception) and indices:
                lines.append("\nIndices:")
                for idx in indices:
                    name = idx.get("index", "")
                    val = idx.get("currentValue")
                    chg = idx.get("change")
                    pct = idx.get("perChange")
                    high52 = idx.get("fiftyTwoWeekHigh")
                    low52 = idx.get("fiftyTwoWeekLow")
                    parts = [f"  {name}: {val}"]
                    if chg is not None:
                        parts.append(f"Chg: {chg:+.2f}")
                    if pct is not None:
                        parts.append(f"({pct:+.2f}%)")
                    if high52 and low52:
                        parts.append(f"52W: {low52} - {high52}")
                    lines.append(" | ".join(parts))
            if not isinstance(summary, Exception) and summary:
                lines.append("\nMarket Summary:")
                for item in summary[:6]:
                    if isinstance(item, dict):
                        detail = item.get("detail", "")
                        value = item.get("value", "")
                        if detail and value:
                            short = detail.replace("Total ", "").replace(" (Rs.)", "")
                            lines.append(f"  {short}: {value}")
            if not isinstance(tops, Exception) and tops:
                gainers = tops.get("top_gainer", [])
                if gainers:
                    lines.append(f"\nTop 5 Gainers:")
                    for g in gainers[:5]:
                        lines.append(f"  - {g.get('symbol')}: {g.get('percentageChange')}+%")
                losers = tops.get("top_loser", [])
                if losers:
                    lines.append(f"\nTop 5 Losers:")
                    for g in losers[:5]:
                        lines.append(f"  - {g.get('symbol')}: {g.get('percentageChange')}%")
            data_context = "\n".join(lines)
        except Exception as e:
            logger.warning("generate_answer: market overview build failed: %s", e)

    if chart_intent and not fuzzy_suggestion and symbol:
        system_prompt = (
            f"You are a NEPSE chart assistant. "
            f"When the user asks for a chart, respond with exactly one line: "
            f"'Chart of {symbol} displayed on the Trade page.'\n"
            f"Do not add any data, analysis, or additional text.\n"
            f"The stock market involves risk. This is not financial advice."
        )
    elif chart_intent and fuzzy_suggestion:
        system_prompt = (
            f"You are a NEPSE chart assistant. "
            f"The closest match is {fuzzy_suggestion['symbol']} ({fuzzy_suggestion.get('name', '')}). "
            f"Politely ask if they meant that symbol before proceeding. "
            f"Example: 'I couldn't find that symbol. Did you mean "
            f"{fuzzy_suggestion['symbol']}?'\n"
            f"Wait for the user to confirm before doing anything else.\n"
            f"The stock market involves risk. This is not financial advice."
        )
    elif fuzzy_suggestion and not chart_intent:
        data_context = ""
        system_prompt = (
            f"You are a NEPSE trading assistant. "
            f"The closest match is {fuzzy_suggestion['symbol']} ({fuzzy_suggestion.get('name', '')}). "
            f"Politely ask if they meant that symbol before proceeding. "
            f"Example: 'I couldn't find that symbol. Did you mean "
            f"{fuzzy_suggestion['symbol']}?'\n"
            f"Wait for the user to confirm before doing anything else.\n"
            f"Do NOT provide any data, analysis, or information about the suggested symbol.\n"
            f"The stock market involves risk. This is not financial advice."
        )
    elif intent == "guide" or not data_context:
        system_prompt = GUIDE_SYSTEM_PROMPT
    else:
        system_prompt = GUIDE_SYSTEM_PROMPT + (
            "\n\nADDITIONAL RULES (data analyst mode):\n" +
            "1. Prioritize the provided REAL market data below for all metrics.\n" +
            "2. If a metric is not in the provided data, say it is not available — do NOT use general knowledge.\n" +
            "3. Cite NEPSE as the data source.\n" +
            "4. Organize data into distinct sections with headers (e.g. Index, Gainers, NABIL).\n" +
            "5. Use compact bullet-point format: one fact per line, no run-on paragraphs.\n" +
            "6. Keep the total response under 12 lines."
        )

    if data_context and not fuzzy_suggestion:
        system_prompt += (
            "\n\nPROVIDED DATA:\n" + data_context +
            "\n\nUse this data for metrics when available."
        )

    meta_symbol = symbol if chart_intent and not fuzzy_suggestion else None
    meta_symbols = symbols if intent == "compare" and len(symbols) >= 2 else None
    suggested_page = "compare" if intent == "compare" and len(symbols) >= 2 else None

    yield json.dumps({
        "type": "meta", "suggested_page": suggested_page,
        "symbol": meta_symbol, "symbols": meta_symbols,
        "symbol_match_type": symbol_match_type,
        "fuzzy_suggestion": fuzzy_suggestion,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
    }) + "\n"

    yield json.dumps({"type": "status", "status": "thinking"}) + "\n"
    max_tokens = 1024
    timeout_secs = 90 if intent == "compare" else 45
    answer_parts: list[str] = []
    token_count = 0

    try:
        async for token in _stream_llm(system_prompt, question, max_tokens, timeout_secs, history):
            if token:
                cleaned = _strip_bold(token)
                answer_parts.append(cleaned)
                token_count += 1
                yield json.dumps({"type": "token", "token": cleaned}) + "\n"
    except Exception as e:
        logger.error("generate_answer streaming failed: %s", e)

    answer = "".join(answer_parts)
    if not answer or token_count == 0:
        answer = (
            "The AI assistant is currently unavailable. Try asking:\n"
            "- 'Compare NABIL and SCB'\n"
            "- 'What is RSI of NABIL?'\n"
            "- 'Top gainers today'\n"
            "- 'How do I start trading?'"
        )
        yield json.dumps({"type": "token", "token": answer}) + "\n"

    yield json.dumps({"type": "done"}) + "\n"