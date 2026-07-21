import os
import pathlib
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from langchain_core.documents import Document

from rag.cache import get_cached_query, query_cache_key, set_cached_query
from rag.chunking import chunk_pages
from rag.confidence import apply_confidence
from rag.embedding import build_vectorstore
from rag.generation import ask
from rag.ingestion import smart_extract
from rag.retrieval import score_retrieved_docs
from rag.versioning import (
    compute_content_hash,
    compute_doc_id,
    diff_versions,
    get_chunks_for_version,
    get_latest_version,
    list_versions,
)

from api.audit import get_recent, init_audit_log, record_query
from api.schemas import (
    Citation,
    DiffResponse,
    HealthResponse,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SourceDocument,
    VersionInfo,
)
from api.state import vectorstore_state

UPLOAD_DIR = pathlib.Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".xls", ".sql", ".docx"}
ADMIN_KEY = os.getenv("ADMIN_KEY")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_audit_log()
    yield


app = FastAPI(title="Legal Multi-Modal RAG API", lifespan=lifespan)


def _chunk_id(doc: Document) -> str:
    doc_id = doc.metadata.get("doc_id", "unknown")
    page = doc.metadata.get("page", "?")
    index = doc.metadata.get("chunk_index", doc.metadata.get("row_index", "?"))
    return f"{doc_id}:{page}:{index}"


def _resolve_query_filter(doc_id: Optional[str], version: Optional[int]) -> tuple[Optional[dict], Optional[int]]:
    """Returns (chroma_filter, resolved_version). If doc_id is given and no
    version is specified, resolves to that document's latest version so
    retrieval doesn't silently mix chunks across versions. Falls back to a
    plain doc_id filter (no version constraint) if this doc_id has no
    versioned chunks at all — e.g. it predates this feature."""
    if not doc_id:
        return None, None
    if version is not None:
        return {"$and": [{"doc_id": doc_id}, {"document_version": version}]}, version

    vectorstore = vectorstore_state.get_vectorstore()
    latest = get_latest_version(vectorstore, doc_id)
    if latest == 0:
        return {"doc_id": doc_id}, None
    return {"$and": [{"doc_id": doc_id}, {"document_version": latest}]}, latest


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile) -> IngestResponse:
    ext = pathlib.Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    save_path = UPLOAD_DIR / file.filename
    contents = await file.read()
    save_path.write_bytes(contents)

    doc_id = compute_doc_id(file.filename)
    content_hash = compute_content_hash(contents)
    vectorstore = vectorstore_state.get_vectorstore()
    version = await run_in_threadpool(get_latest_version, vectorstore, doc_id) + 1

    def _ingest_and_index() -> list[Document]:
        pages = smart_extract(str(save_path))
        docs = chunk_pages(pages)
        for doc in docs:
            doc.metadata["doc_id"] = doc_id
            doc.metadata["document_version"] = version
            doc.metadata["content_hash"] = content_hash
        build_vectorstore(docs)
        return docs

    docs = await run_in_threadpool(_ingest_and_index)
    vectorstore_state.invalidate()

    return IngestResponse(doc_id=doc_id, filename=file.filename, chunks_indexed=len(docs), document_version=version)


@app.get("/documents/{doc_id}/versions", response_model=list[VersionInfo])
async def document_versions(doc_id: str) -> list[dict]:
    vectorstore = vectorstore_state.get_vectorstore()
    versions = await run_in_threadpool(list_versions, vectorstore, doc_id)
    if not versions:
        raise HTTPException(status_code=404, detail=f"No versions found for doc_id '{doc_id}'.")
    return versions


@app.get("/documents/{doc_id}/diff", response_model=DiffResponse)
async def document_diff(
    doc_id: str, from_: int = Query(alias="from"), to: int = Query()
) -> DiffResponse:
    vectorstore = vectorstore_state.get_vectorstore()
    from_chunks = await run_in_threadpool(get_chunks_for_version, vectorstore, doc_id, from_)
    to_chunks = await run_in_threadpool(get_chunks_for_version, vectorstore, doc_id, to)
    if not from_chunks:
        raise HTTPException(status_code=404, detail=f"Version {from_} not found for doc_id '{doc_id}'.")
    if not to_chunks:
        raise HTTPException(status_code=404, detail=f"Version {to} not found for doc_id '{doc_id}'.")
    entries = diff_versions(from_chunks, to_chunks)
    return DiffResponse(doc_id=doc_id, from_version=from_, to_version=to, entries=entries)


@app.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest, response: Response) -> QueryResponse:
    if vectorstore_state.is_empty():
        raise HTTPException(status_code=400, detail="No documents have been ingested yet.")

    doc_filter, resolved_version = await run_in_threadpool(
        _resolve_query_filter, payload.doc_id, payload.document_version
    )

    # Cache key uses the *resolved* version, not payload.document_version (which may be
    # None/"latest") — otherwise re-ingesting a new version while repeatedly asking for
    # "latest" would keep serving the stale cached answer from the old version.
    cache_key = query_cache_key(payload.doc_id, payload.question, resolved_version)
    cached = await run_in_threadpool(get_cached_query, cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        await record_query(
            query_text=payload.question,
            doc_id=payload.doc_id,
            retrieved_chunks=[],  # not recomputed on a cache hit — see cache_hit flag
            final_answer=cached["answer"],
            confidence=cached["confidence"],
            citations=cached["citations"],
            abstained=cached["confidence"] != "high",
            cache_hit=True,
        )
        return QueryResponse(**cached)
    response.headers["X-Cache"] = "MISS"

    retriever = vectorstore_state.get_retriever(filter=doc_filter)

    result = await run_in_threadpool(ask, payload.question, retriever)

    contexts = [doc.page_content for doc in result["source_documents"]]
    final_answer, confidence, _score = await run_in_threadpool(
        apply_confidence, payload.question, result["answer"], contexts
    )
    abstained = final_answer != result["answer"]

    source_documents = [
        SourceDocument(
            source=doc.metadata.get("source", "unknown"),
            page=doc.metadata.get("page", "?"),
            chunk_text=doc.page_content,
        )
        for doc in result["source_documents"]
    ]

    # An abstained answer supersedes the discarded one, so don't attach citations
    # or a chart that were only ever grounded in the answer we just threw away.
    citations = [] if abstained else [
        Citation(
            doc_id=doc.metadata.get("doc_id", "unknown"),
            page_number=doc.metadata.get("page", "?"),
            bbox=doc.metadata.get("bbox"),
            chunk_text=doc.page_content,
        )
        for doc in result["citations"]
    ]

    chart_fig = None if abstained else result.get("chart")
    chart_json = chart_fig.to_plotly_json() if chart_fig is not None else None

    query_response = QueryResponse(
        answer=final_answer,
        confidence=confidence,
        source_documents=source_documents,
        citations=citations,
        chart=chart_json,
        chart_type=None if abstained else result.get("chart_type"),
        chart_reason=None if abstained else result.get("chart_reason"),
    )
    await run_in_threadpool(set_cached_query, cache_key, query_response.model_dump())

    vectorstore = vectorstore_state.get_vectorstore()
    scored_docs = await run_in_threadpool(
        score_retrieved_docs, vectorstore, payload.question, result["source_documents"], doc_filter
    )
    await record_query(
        query_text=payload.question,
        doc_id=payload.doc_id,
        # "score" here is a raw similarity distance (lower = more similar), not a 0-1 relevance score.
        retrieved_chunks=[{"chunk_id": _chunk_id(doc), "score": score} for doc, score in scored_docs],
        final_answer=final_answer,
        confidence=confidence,
        citations=[c.model_dump() for c in citations],
        abstained=confidence != "high",
        cache_hit=False,
    )

    return query_response


@app.get("/audit/recent")
async def audit_recent(limit: int = 50, x_admin_key: Optional[str] = Header(default=None)) -> list[dict]:
    if not ADMIN_KEY:
        raise HTTPException(status_code=503, detail="Admin endpoint not configured (ADMIN_KEY not set).")
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Missing or invalid X-Admin-Key header.")
    return await get_recent(limit)
