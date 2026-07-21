from typing import Any, Literal, Optional

from pydantic import BaseModel


class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    chunks_indexed: int


class QueryRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None


class SourceDocument(BaseModel):
    source: str
    page: Any
    chunk_text: str


class Citation(BaseModel):
    doc_id: str
    page_number: Any
    bbox: Optional[list[float]] = None
    chunk_text: str


class QueryResponse(BaseModel):
    answer: str
    confidence: Literal["high", "medium", "low"]
    source_documents: list[SourceDocument]
    citations: list[Citation]
    chart: Optional[dict] = None
    chart_type: Optional[str] = None
    chart_reason: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
