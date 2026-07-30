# Architecture

## Overview

DocuMind AI is a multi-tenant Retrieval-Augmented Generation (RAG) SaaS. It separates
the **fast path** (API request/response) from the **slow path** (document ingestion),
so uploads never block the user and heavy embedding work is done off the request thread.

## Components

| Component | Responsibility |
|---|---|
| **FastAPI (`app/`)** | HTTP API: auth, uploads, chat, billing. Stateless, horizontally scalable. |
| **PostgreSQL + pgvector** | System of record + vector store. One row per chunk with a `Vector` column. |
| **Redis** | Celery broker/result backend + rate-limit counters. |
| **Celery worker** | Async ingestion: read → chunk → embed → persist. |
| **LLM provider** | OpenAI / Gemini via LangChain for answer generation. |
| **Langfuse** | Traces every LLM call: prompt, cost, latency, retrieval quality. |
| **Stripe** | Subscription billing; webhook flips `user.plan` to `pro`. |

## Ingestion (slow path)

```
POST /documents
  → save Document(status=pending) + write file to disk
  → ingest_document_task.delay(...)          # returns 202 immediately
Celery worker:
  → status=processing
  → read text (pypdf / plain)
  → RecursiveCharacterTextSplitter → chunks
  → embed_texts(chunks)                      # OpenAI embeddings
  → bulk insert Chunk rows (with vectors)
  → status=ready   (or failed + error on exception, with retry)
```

## Query (fast path)

```
POST /chat
  → auth (JWT) → per-plan rate limit (Redis)
  → embed_query(question)
  → pgvector cosine_distance ORDER BY ... LIMIT top_k   # tenant-scoped
  → build numbered context + citations
  → LLM answer (grounded, cite-or-refuse)  ── traced to Langfuse
  → return answer + citations   (or SSE stream via /chat/stream)
```

## Multi-tenancy & security

- Every `Chunk` and `Document` carries `owner_id`; all retrieval is filtered by it.
- JWT bearer auth on all data endpoints; passwords hashed with bcrypt.
- Rate limiting is per-user and per-plan (free vs pro).

## Scaling notes

- API and worker are separate processes — scale them independently.
- Swap the IVFFlat/HNSW index on `chunks.embedding` for larger corpora.
- Move uploads from local disk to S3 for multi-node deployments.

## Production checklist (roadmap)

- [ ] Alembic migrations (replace `init_db` create_all)
- [ ] S3-backed uploads
- [ ] Hybrid retrieval + reranking
- [ ] RAGAS eval gate in CI
