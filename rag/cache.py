import hashlib
import json
import logging
import os
from typing import Optional

import redis
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

QUERY_CACHE_TTL_SECONDS = int(os.getenv("QUERY_CACHE_TTL_SECONDS", "3600"))

_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Lazy singleton so importing this module never requires Redis to be up —
    connection attempts only happen when a cache operation actually runs."""
    global _client
    if _client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _client = redis.Redis.from_url(
            redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
    return _client


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def query_cache_key(doc_id: Optional[str], question: str, version: Optional[int] = None) -> str:
    """`version` must be the *resolved* version actually queried (not just
    whatever the caller passed in, which may be None meaning "latest") —
    otherwise re-ingesting a new version while repeatedly asking for "latest"
    would keep serving a stale cached answer from the old version."""
    return "query:" + _hash(f"{doc_id or ''}|{version if version is not None else ''}|{question}")


def get_cached_query(key: str) -> Optional[dict]:
    try:
        raw = get_redis_client().get(key)
    except redis.RedisError as e:
        logger.warning("Redis unavailable for query cache read (%s) — bypassing cache.", e)
        return None
    return json.loads(raw) if raw else None


def set_cached_query(key: str, value: dict) -> None:
    try:
        get_redis_client().set(key, json.dumps(value), ex=QUERY_CACHE_TTL_SECONDS)
    except redis.RedisError as e:
        logger.warning("Redis unavailable for query cache write (%s) — skipping cache.", e)


class CachedEmbeddings(Embeddings):
    """Wraps an Embeddings model with a Redis-backed cache keyed on a hash of
    the exact chunk/query text, so re-ingesting an identical document (or
    re-asking an identical question) skips recomputing those embeddings.
    Falls back to the underlying model, uncached, on any Redis error — a
    down/missing Redis should degrade performance, not break ingestion."""

    def __init__(self, underlying: Embeddings, namespace: str = "embed") -> None:
        self._underlying = underlying
        self._namespace = namespace

    def _key(self, text: str) -> str:
        return f"{self._namespace}:{_hash(text)}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            client = get_redis_client()
            cached_raw = client.mget([self._key(t) for t in texts])
        except redis.RedisError as e:
            logger.warning("Redis unavailable for embedding cache (%s) — computing all uncached.", e)
            return self._underlying.embed_documents(texts)

        results: list[Optional[list[float]]] = [
            json.loads(raw) if raw else None for raw in cached_raw
        ]
        misses = [i for i, r in enumerate(results) if r is None]

        if misses:
            computed = self._underlying.embed_documents([texts[i] for i in misses])
            for i, vec in zip(misses, computed):
                results[i] = vec
            try:
                client.mset({self._key(texts[i]): json.dumps(results[i]) for i in misses})
            except redis.RedisError:
                pass  # cache write is best-effort

        return results  # type: ignore[return-value]

    def embed_query(self, text: str) -> list[float]:
        key = self._key(text)
        try:
            client = get_redis_client()
            cached = client.get(key)
            if cached is not None:
                return json.loads(cached)
        except redis.RedisError as e:
            logger.warning("Redis unavailable for embedding cache (%s) — computing uncached.", e)
            return self._underlying.embed_query(text)

        vec = self._underlying.embed_query(text)
        try:
            client.set(key, json.dumps(vec))
        except redis.RedisError:
            pass
        return vec
