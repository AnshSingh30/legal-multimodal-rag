from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

MMR_K = 5
MMR_FETCH_K = 20
MMR_LAMBDA_MULT = 0.7


def build_retriever(vectorstore: Chroma, filter: Optional[dict] = None) -> BaseRetriever:
    # Use MMR search without Cohere reranker
    search_kwargs = {
        "k": MMR_K,
        "fetch_k": MMR_FETCH_K,
        "lambda_mult": MMR_LAMBDA_MULT
    }
    if filter:
        search_kwargs["filter"] = filter
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs
    )


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
