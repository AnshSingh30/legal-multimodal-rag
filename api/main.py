import pathlib
import uuid

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from langchain_core.documents import Document

from rag.chunking import chunk_pages
from rag.confidence import apply_confidence
from rag.embedding import build_vectorstore
from rag.generation import ask
from rag.ingestion import smart_extract

from api.schemas import Citation, HealthResponse, IngestResponse, QueryRequest, QueryResponse, SourceDocument
from api.state import vectorstore_state

UPLOAD_DIR = pathlib.Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".xls", ".sql", ".docx"}

app = FastAPI(title="Legal Multi-Modal RAG API")


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

    doc_id = uuid.uuid4().hex

    def _ingest_and_index() -> list[Document]:
        pages = smart_extract(str(save_path))
        docs = chunk_pages(pages)
        for doc in docs:
            doc.metadata["doc_id"] = doc_id
        build_vectorstore(docs)
        return docs

    docs = await run_in_threadpool(_ingest_and_index)
    vectorstore_state.invalidate()

    return IngestResponse(doc_id=doc_id, filename=file.filename, chunks_indexed=len(docs))


@app.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest) -> QueryResponse:
    if vectorstore_state.is_empty():
        raise HTTPException(status_code=400, detail="No documents have been ingested yet.")

    retriever = vectorstore_state.get_retriever(doc_id=payload.doc_id)

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

    return QueryResponse(
        answer=final_answer,
        confidence=confidence,
        source_documents=source_documents,
        citations=citations,
        chart=chart_json,
        chart_type=None if abstained else result.get("chart_type"),
        chart_reason=None if abstained else result.get("chart_reason"),
    )
