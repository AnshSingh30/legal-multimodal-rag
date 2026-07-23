import re
from typing import Optional

from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

# k was 5, which sat just under the rank of the chunk actually answering short
# factoid questions ("name of college" put it at dense rank 6), so the generator
# refused for lack of context. Widened to leave headroom for that case.
MMR_K = 8
MMR_FETCH_K = 30
MMR_LAMBDA_MULT = 0.7
BM25_K = 8
BM25_WEIGHT = 0.5
DENSE_WEIGHT = 0.5


def build_retriever(vectorstore: Chroma, filter: Optional[dict] = None) -> BaseRetriever:
    # Use MMR search without Cohere reranker
    search_kwargs = {
        "k": MMR_K,
        "fetch_k": MMR_FETCH_K,
        "lambda_mult": MMR_LAMBDA_MULT
    }
    if filter:
        search_kwargs["filter"] = filter
    dense_retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs
    )

    bm25_retriever = _build_bm25_retriever(vectorstore, filter)
    if bm25_retriever is None:
        return dense_retriever

    # Dense embeddings can bury an exact term or proper noun (e.g. an institution
    # name) inside a chunk whose overall content is dominated by unrelated text,
    # so a pure dense MMR search never surfaces it. BM25 catches that lexical
    # match directly; ensembling the two covers both failure modes.
    return EnsembleRetriever(
        retrievers=[bm25_retriever, dense_retriever],
        weights=[BM25_WEIGHT, DENSE_WEIGHT],
    )


_TOKEN_RE = re.compile(r"\w+")


def _bm25_preprocess(text: str) -> list[str]:
    """BM25's default tokenizer splits on whitespace only, keeping case and
    punctuation, so a document's "Specialization:" never matches a query's
    "specialization" — the lexical half of the ensemble silently matched almost
    nothing. Lowercase and split on word characters so it actually does."""
    return _TOKEN_RE.findall(text.lower())


def _build_bm25_retriever(vectorstore: Chroma, filter: Optional[dict]) -> Optional[BM25Retriever]:
    raw = vectorstore.get(where=filter, include=["documents", "metadatas"])
    docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(raw["documents"], raw["metadatas"])
    ]
    if not docs:
        return None
    bm25_retriever = BM25Retriever.from_documents(docs, preprocess_func=_bm25_preprocess)
    bm25_retriever.k = BM25_K
    return bm25_retriever


def score_retrieved_docs(
    vectorstore: Chroma, query: str, docs: list[Document], filter: Optional[dict] = None
) -> list[tuple[Document, Optional[float]]]:
    """Best-effort similarity distance for each of `docs` (e.g. already
    MMR-selected) — lower means more similar. Chroma's MMR search doesn't
    return scores directly, so this re-queries a plain similarity search over
    the same candidate pool (MMR's fetch_k) and matches by page_content. A doc
    not found in that pool (shouldn't normally happen) gets score=None.

    Deliberately using similarity_search_with_score (raw distance) rather than
    similarity_search_with_relevance_scores: the latter's 0-1 normalization
    picks a relevance-score function based on assumptions about the
    collection's distance metric that didn't hold for this one — it was
    observed returning negative values (a logged UserWarning: "Relevance
    scores must be between 0 and 1"). Raw distance has no such normalization
    step to get wrong.
    """
    pool_size = max(len(docs), MMR_FETCH_K)
    scored = vectorstore.similarity_search_with_score(query, k=pool_size, filter=filter)
    score_by_content = {d.page_content: score for d, score in scored}
    return [(d, score_by_content.get(d.page_content)) for d in docs]
