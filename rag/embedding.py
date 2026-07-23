from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from rag.cache import CachedEmbeddings

PERSIST_DIR = "./chroma_db"
embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
# Chroma reads/writes go through the Redis-backed cache; RAGAS scoring
# (rag/confidence.py, rag/evaluator.py) uses the raw `embedder` above directly,
# since caching doesn't matter for those one-off calls.
_cached_embedder = CachedEmbeddings(embedder)

def build_vectorstore(docs: list[Document]) -> Chroma:
    return Chroma.from_documents(docs, _cached_embedder,
                                  persist_directory=PERSIST_DIR)

def load_vectorstore() -> Chroma:
    return Chroma(persist_directory=PERSIST_DIR,
                  embedding_function=_cached_embedder)
