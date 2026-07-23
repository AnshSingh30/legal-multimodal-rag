import threading
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.retrievers import BaseRetriever

from rag.embedding import load_vectorstore
from rag.retrieval import build_retriever


class VectorStoreState:
    """Holds the single shared, persisted Chroma vectorstore for the API process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vectorstore: Optional[Chroma] = None

    def get_vectorstore(self) -> Chroma:
        with self._lock:
            if self._vectorstore is None:
                self._vectorstore = load_vectorstore()
            return self._vectorstore

    def is_empty(self) -> bool:
        vectorstore = self.get_vectorstore()
        return vectorstore._collection.count() == 0

    def get_retriever(self, filter: Optional[dict] = None) -> BaseRetriever:
        vectorstore = self.get_vectorstore()
        return build_retriever(vectorstore, filter=filter)

    def invalidate(self) -> None:
        """Force the next get_vectorstore() call to reload from disk, picking up newly ingested chunks."""
        with self._lock:
            self._vectorstore = None


vectorstore_state = VectorStoreState()
