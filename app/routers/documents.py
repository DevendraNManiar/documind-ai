from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import Document, User
from app.schemas import DocumentOut
from app.workers.tasks import ingest_document_task

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED = {".pdf", ".txt", ".md"}


@router.post("", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Document:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Unsupported type. Allowed: {sorted(ALLOWED)}")

    document = Document(owner_id=user.id, filename=file.filename or "document", status="pending")
    db.add(document)
    await db.commit()
    await db.refresh(document)

    dest = UPLOAD_DIR / f"{document.id}{suffix}"
    dest.write_bytes(await file.read())

    # Fire-and-forget: heavy work happens in the Celery worker.
    ingest_document_task.delay(str(document.id), str(dest))
    return document


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Document]:
    result = await db.scalars(
        select(Document).where(Document.owner_id == user.id).order_by(Document.created_at.desc())
    )
    return list(result.all())
