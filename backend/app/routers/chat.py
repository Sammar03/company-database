"""Chat endpoint: retrieve + generate a grounded, cited answer."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_api_key
from ..config import get_settings
from ..generate import RateLimited, answer_question
from ..models import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    settings = get_settings()
    try:
        answer, sources, grounded = answer_question(
            req.message, req.history, settings.top_k
        )
    except RateLimited as err:
        detail = (
            f"Rate limit reached — try again in ~{int(err.retry_after)}s."
            if err.retry_after
            else "Rate limit reached — please retry shortly."
        )
        raise HTTPException(status_code=429, detail=detail) from err
    except Exception as err:  # noqa: BLE001
        msg = str(err).lower()
        if "rate" in msg or "429" in msg or "quota" in msg:
            raise HTTPException(
                status_code=429, detail="Provider rate limit hit. Please retry shortly."
            ) from err
        raise HTTPException(status_code=500, detail="Failed to generate an answer.") from err
    return ChatResponse(answer=answer, sources=sources, grounded=grounded)
