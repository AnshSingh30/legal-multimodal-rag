from typing import Optional

from langchain_chroma import Chroma
from langchain_core.retrievers import BaseRetriever

def build_retriever(vectorstore: Chroma, filter: Optional[dict] = None) -> BaseRetriever:
    # Use MMR search without Cohere reranker
    search_kwargs = {
        "k": 5,
        "fetch_k": 20,
        "lambda_mult": 0.7
    }
    if filter:
        search_kwargs["filter"] = filter
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs
    )
