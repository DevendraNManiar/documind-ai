"""Embedding provider. Defaults to OpenAI; swap here for bge-base / Gemini."""
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from app.config import settings


@lru_cache
def get_embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    return get_embedder().embed_documents(texts)


def embed_query(text: str) -> list[float]:
    return get_embedder().embed_query(text)
