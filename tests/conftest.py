"""Shared test setup.

Unit tests (test_security, test_health) need no services.
The integration test (test_integration_flow) needs a running Postgres+pgvector;
it is skipped automatically if the database is unreachable. Embeddings and the
LLM are mocked, so no API keys are required.
"""
import os

# Must be set BEFORE any `app.*` import so cached settings/engines bind to these.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://documind:documind@localhost:5432/documind",
    ),
)
