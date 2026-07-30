"""Optional Langfuse tracing. No-op if keys are not configured."""
from functools import lru_cache

from app.config import settings


@lru_cache
def get_langfuse_handler():
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    try:
        from langfuse.callback import CallbackHandler

        return CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception:  # pragma: no cover - observability must never break requests
        return None
