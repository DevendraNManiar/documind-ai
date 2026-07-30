from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import init_db
from app.routers import auth, billing, chat, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For local/dev convenience. In production, run Alembic migrations instead.
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Production Document-Q&A SaaS (RAG) — FastAPI + pgvector.",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(billing.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name}
