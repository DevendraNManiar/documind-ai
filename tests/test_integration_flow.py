"""Full auth -> upload -> ingest -> chat flow against a real Postgres+pgvector.

Embeddings and the LLM are mocked (deterministic), so no API keys or network
are needed. Celery runs in eager mode so ingestion happens inline. The whole
test is skipped automatically if Postgres is not reachable.

Run it with the compose database up:
    docker compose up -d db redis
    pytest -q -m integration
"""
import hashlib
import random

import httpx
import pytest
import pytest_asyncio

pytestmark = pytest.mark.integration


def _fake_vector(text: str) -> list[float]:
    from app.config import settings

    seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "little")
    rng = random.Random(seed)
    return [rng.random() for _ in range(settings.embedding_dim)]


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeLLM:
    async def ainvoke(self, messages, config=None):  # noqa: ANN001
        return _FakeResponse("Based on the provided context, the budget is 42 thousand dollars. [1]")


@pytest_asyncio.fixture
async def client(monkeypatch):
    # --- mock embeddings + LLM (no keys / network) ---
    import app.rag.chain as chain_mod
    import app.rag.ingest as ingest_mod
    import app.rag.retriever as retriever_mod

    monkeypatch.setattr(ingest_mod, "embed_texts", lambda texts: [_fake_vector(t) for t in texts])
    monkeypatch.setattr(retriever_mod, "embed_query", _fake_vector)
    monkeypatch.setattr(chain_mod, "_llm", lambda: _FakeLLM())

    # --- run Celery tasks inline ---
    from app.workers.celery_app import celery

    celery.conf.task_always_eager = True
    celery.conf.task_eager_propagates = True

    # --- database (skip if unreachable) ---
    from app.database import Base, engine, init_db

    try:
        await init_db()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres+pgvector not reachable: {exc}")

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_signup_upload_chat_flow(client):
    # 1. signup -> token
    r = await client.post("/auth/signup", json={"email": "jaimin@test.com", "password": "password123"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. upload a document (ingestion runs inline via eager Celery)
    content = b"The quarterly meeting is on Monday. The approved budget is 42 thousand dollars."
    files = {"file": ("notes.txt", content, "text/plain")}
    r = await client.post("/documents", files=files, headers=headers)
    assert r.status_code == 202, r.text

    # 3. document should be fully ingested
    r = await client.get("/documents", headers=headers)
    assert r.status_code == 200
    docs = r.json()
    assert docs, "no documents returned"
    assert docs[0]["status"] == "ready", f"unexpected status: {docs[0]}"

    # 4. chat -> grounded answer with citations
    r = await client.post("/chat", json={"question": "What is the approved budget?"}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"], "empty answer"
    assert len(body["citations"]) >= 1, "expected at least one citation"
    assert body["citations"][0]["filename"] == "notes.txt"


async def test_chat_requires_auth(client):
    r = await client.post("/chat", json={"question": "anything"})
    assert r.status_code == 401
