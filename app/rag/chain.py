"""Build a grounded prompt from retrieved chunks and call the LLM."""
import uuid
from collections.abc import AsyncGenerator

from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.observability import get_langfuse_handler
from app.rag.retriever import retrieve
from app.schemas import Citation

SYSTEM_PROMPT = (
    "You are DocuMind, a helpful assistant that answers strictly from the provided "
    "context. If the answer is not in the context, say you don't know. "
    "Cite sources inline as [n] using the numbered context blocks."
)


def _build_context(pairs) -> tuple[str, list[Citation]]:
    blocks, citations = [], []
    for i, (chunk, filename) in enumerate(pairs, start=1):
        blocks.append(f"[{i}] (from {filename})\n{chunk.content}")
        citations.append(
            Citation(
                document_id=chunk.document_id,
                filename=filename,
                chunk_index=chunk.chunk_index,
                snippet=chunk.content[:200],
            )
        )
    return "\n\n".join(blocks), citations


def _llm() -> ChatOpenAI:
    return ChatOpenAI(model=settings.chat_model, api_key=settings.openai_api_key, temperature=0.1)


async def answer_question(
    db: AsyncSession,
    owner_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None = None,
) -> tuple[str, list[Citation]]:
    pairs = await retrieve(db, owner_id, question, document_id)
    if not pairs:
        return "I couldn't find anything relevant in your documents.", []

    context, citations = _build_context(pairs)
    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", f"Context:\n{context}\n\nQuestion: {question}"),
    ]
    config = {"callbacks": [h]} if (h := get_langfuse_handler()) else {}
    response = await _llm().ainvoke(messages, config=config)
    return response.content, citations


async def stream_answer(
    db: AsyncSession,
    owner_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None = None,
) -> AsyncGenerator[str, None]:
    """Yield answer tokens for Server-Sent Events streaming."""
    pairs = await retrieve(db, owner_id, question, document_id)
    if not pairs:
        yield "I couldn't find anything relevant in your documents."
        return

    context, _ = _build_context(pairs)
    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", f"Context:\n{context}\n\nQuestion: {question}"),
    ]
    config = {"callbacks": [h]} if (h := get_langfuse_handler()) else {}
    async for chunk in _llm().astream(messages, config=config):
        if chunk.content:
            yield chunk.content
