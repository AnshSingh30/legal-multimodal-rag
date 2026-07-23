import uuid

from langchain_core.embeddings import Embeddings

from rag.cache import CachedEmbeddings


class _CountingEmbeddings(Embeddings):
    """Fake embedder that records every text it was actually asked to embed,
    so tests can assert the cache avoided recomputation."""

    def __init__(self) -> None:
        self.embed_documents_calls: list[str] = []
        self.embed_query_calls: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.embed_documents_calls.extend(texts)
        return [[float(len(t)), 0.0] for t in texts]

    def embed_query(self, text: str) -> list[float]:
        self.embed_query_calls.append(text)
        return [float(len(text)), 0.0]


def test_embed_documents_skips_previously_seen_chunks() -> None:
    underlying = _CountingEmbeddings()
    # Unique namespace per test run so leftover keys from other runs can't cause false hits.
    cached = CachedEmbeddings(underlying, namespace=f"test-{uuid.uuid4().hex}")

    texts = ["Row 0: Name=Alice", "Row 1: Name=Bob"]
    first = cached.embed_documents(texts)
    assert underlying.embed_documents_calls == texts

    second = cached.embed_documents(texts)
    # Second call should be served entirely from cache — no new calls to the underlying model.
    assert underlying.embed_documents_calls == texts
    assert second == first


def test_embed_documents_only_computes_new_chunks() -> None:
    underlying = _CountingEmbeddings()
    cached = CachedEmbeddings(underlying, namespace=f"test-{uuid.uuid4().hex}")

    cached.embed_documents(["Row 0: Name=Alice"])
    assert underlying.embed_documents_calls == ["Row 0: Name=Alice"]

    cached.embed_documents(["Row 0: Name=Alice", "Row 1: Name=Bob"])
    # Only the unseen chunk should trigger a new embedding call.
    assert underlying.embed_documents_calls == ["Row 0: Name=Alice", "Row 1: Name=Bob"]


def test_embed_query_is_cached() -> None:
    underlying = _CountingEmbeddings()
    cached = CachedEmbeddings(underlying, namespace=f"test-{uuid.uuid4().hex}")

    cached.embed_query("What is the score of Alice?")
    cached.embed_query("What is the score of Alice?")
    assert underlying.embed_query_calls == ["What is the score of Alice?"]
