from typing import Any, Literal, Optional

from pydantic import BaseModel


class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    chunks_indexed: int
    document_version: int


class QueryRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None
    document_version: Optional[int] = None  # None = latest version of doc_id


class SourceDocument(BaseModel):
    source: str
    page: Any
    chunk_text: str


class Citation(BaseModel):
    doc_id: str
    page_number: Any
    bbox: Optional[list[float]] = None
    chunk_text: str
    # "text" = native PDF extraction, bbox in PDF point space (matches pdf.js/react-pdf's
    # viewport directly). "ocr" = Tesseract, bbox in pixel space at the 300dpi render used
    # for OCR — the frontend must scale by 72/300 to overlay on a normally-rendered PDF page.
    method: Optional[str] = None


class RetrievalTraceEntry(BaseModel):
    chunk_id: str
    source: str
    page: Any
    # Raw similarity distance (lower = more similar) — see rag/retrieval.py's
    # score_retrieved_docs docstring for why this isn't a normalized 0-1 score.
    score: Optional[float] = None
    # Retrieval in this codebase is single-path dense MMR search — there is no
    # sparse/hybrid retriever to distinguish between (despite what the project
    # brief assumed). This is reported as-is rather than fabricating a split
    # that doesn't exist.
    retrieval_method: str = "dense (MMR)"


class QueryResponse(BaseModel):
    answer: str
    confidence: Literal["high", "medium", "low"]
    source_documents: list[SourceDocument]
    citations: list[Citation]
    retrieval_trace: list[RetrievalTraceEntry] = []
    chart: Optional[dict] = None
    chart_type: Optional[str] = None
    chart_reason: Optional[str] = None


class HealthResponse(BaseModel):
    status: str


class VersionInfo(BaseModel):
    document_version: int
    filename: str
    content_hash: Optional[str] = None
    date_ingested: Optional[str] = None
    chunk_count: int


class DiffEntry(BaseModel):
    key: str
    status: Literal["added", "removed", "changed"]
    from_text: Optional[str] = None
    to_text: Optional[str] = None
    diff: Optional[list[str]] = None


class DiffResponse(BaseModel):
    doc_id: str
    from_version: int
    to_version: int
    entries: list[DiffEntry]
