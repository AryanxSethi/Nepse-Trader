"""Chat route — streaming AI assistant answers via SSE."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.llm_service import generate_answer

router = APIRouter()


class QuestionRequest(BaseModel):
    question: str
    history: list[dict] = []


@router.post("/api/ask")
async def ask_question(req: QuestionRequest) -> StreamingResponse:
    """POST /api/ask — ask the AI assistant a question; returns a streaming SSE response."""
    return StreamingResponse(generate_answer(req.question, req.history), media_type="text/event-stream")