"""Guide routes — knowledge base search and broker directory."""

import logging

import httpx
from fastapi import APIRouter

from app.core.config import OLLAMA_MODEL, OLLAMA_URL
from app.guide.broker_directory import _ensure_brokers as _ensure_broker_cache
from app.guide.broker_directory import search_brokers
from app.guide.knowledge_base import find_guide_entry, get_popular_entries
from app.services.llm_service import GUIDE_SYSTEM_PROMPT

router = APIRouter()
logger = logging.getLogger('routers.guide')


@router.get("/api/guide/search")
async def guide_search(q: str = "") -> dict:
    """GET /api/guide/search — search the knowledge base or fall back to Ollama for answers."""
    if not q:
        return {"entries": get_popular_entries()}
    entry = find_guide_entry(q)
    if entry:
        return {"entries": [entry], "llm_answer": None, "popular": get_popular_entries()}
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": GUIDE_SYSTEM_PROMPT},
                        {"role": "user", "content": q},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.5, "num_predict": 512},
                },
            )
            data = resp.json()
            llm_answer = data.get("message", {}).get("content", "")
    except Exception as e:
        logger.error("Guide search Ollama failed: %s", e)
        llm_answer = ""

    return {"entries": [], "llm_answer": llm_answer or None, "popular": get_popular_entries()}


@router.get("/api/guide/brokers")
async def guide_brokers(search: str = "") -> dict:
    """GET /api/guide/brokers — search the broker directory (guide context)."""
    await _ensure_broker_cache()
    return {"brokers": search_brokers(search)}