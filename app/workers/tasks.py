"""Background ingestion task. Runs in the Celery worker with a SYNC session."""
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Document
from app.rag.ingest import ingest_document
from app.workers.celery_app import celery

# Celery tasks are synchronous -> use a sync SQLAlchemy engine (psycopg v3).
_sync_url = settings.database_url.replace("+asyncpg", "+psycopg")
_sync_engine = create_engine(_sync_url, pool_pre_ping=True)
SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)


@celery.task(name="ingest_document", bind=True, max_retries=2)
def ingest_document_task(self, document_id: str, file_path: str) -> dict:
    session: Session = SyncSession()
    try:
        document = session.get(Document, uuid.UUID(document_id))
        if document is None:
            return {"status": "missing", "document_id": document_id}

        document.status = "processing"
        session.commit()

        count = ingest_document(session, document, Path(file_path))
        document.status = "ready"
        session.commit()
        return {"status": "ready", "chunks": count, "document_id": document_id}
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        document = session.get(Document, uuid.UUID(document_id))
        if document is not None:
            document.status = "failed"
            document.error = str(exc)[:1000]
            session.commit()
        raise self.retry(exc=exc, countdown=10)
    finally:
        session.close()
