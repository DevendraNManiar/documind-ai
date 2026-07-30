"""Load a document, split into chunks, embed, and persist to pgvector."""
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Chunk, Document
from app.rag.embeddings import embed_texts


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def _split(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    return [c for c in splitter.split_text(text) if c.strip()]


def ingest_document(db: Session, document: Document, file_path: Path) -> int:
    """Synchronous ingest (called from the Celery worker). Returns chunk count."""
    text = _read_text(file_path)
    chunks = _split(text)
    if not chunks:
        raise ValueError("No extractable text found in document.")

    vectors = embed_texts(chunks)

    # idempotent re-ingest: clear any existing chunks first
    db.execute(delete(Chunk).where(Chunk.document_id == document.id))
    db.add_all(
        [
            Chunk(
                document_id=document.id,
                owner_id=document.owner_id,
                content=content,
                chunk_index=i,
                embedding=vector,
            )
            for i, (content, vector) in enumerate(zip(chunks, vectors, strict=True))
        ]
    )
    return len(chunks)
