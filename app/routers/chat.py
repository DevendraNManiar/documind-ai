from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import rate_limited_user
from app.models import User
from app.rag.chain import answer_question, stream_answer
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(rate_limited_user),
) -> ChatResponse:
    answer, citations = await answer_question(db, user.id, payload.question, payload.document_id)
    return ChatResponse(answer=answer, citations=citations)


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(rate_limited_user),
) -> StreamingResponse:
    async def event_source():
        async for token in stream_answer(db, user.id, payload.question, payload.document_id):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
