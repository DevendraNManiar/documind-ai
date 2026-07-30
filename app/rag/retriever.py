"""pgvector cosine-similarity retrieval, scoped to the requesting tenant."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Chunk, Document
from app.rag.embeddings import embed_query


async def retrieve(
    db: AsyncSession,
    owner_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None = None,
    k: int | None = None,
) -> list[tuple[Chunk, str]]:
    """Return the top-k (Chunk, filename) tuples most similar to the question."""
    k = k or settings.top_k
    query_vec = embed_query(question)

    stmt = (
        select(Chunk, Document.filename)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.owner_id == owner_id)
    )
    if document_id is not None:
        stmt = stmt.where(Chunk.document_id == document_id)

    # pgvector cosine distance operator via SQLAlchemy: .cosine_distance(...)
    stmt = stmt.order_by(Chunk.embedding.cosine_distance(query_vec)).limit(k)

    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]
