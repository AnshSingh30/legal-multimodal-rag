import pathlib

from rag.chunking import chunk_pages
from rag.ingestion import smart_extract

SAMPLE_PDF = pathlib.Path(__file__).parent.parent / "uploads" / "NexGen_SLA_DPA_v2.pdf"


def test_native_pdf_chunks_get_page_and_bbox() -> None:
    pages = smart_extract(str(SAMPLE_PDF))
    docs = chunk_pages(pages)

    assert len(docs) > 0
    for doc in docs:
        assert isinstance(doc.metadata.get("page"), int)
        bbox = doc.metadata.get("bbox")
        assert bbox is not None
        assert len(bbox) == 4
        assert all(isinstance(v, (int, float)) for v in bbox)


def test_doc_id_tag_propagates_through_chunking() -> None:
    pages = smart_extract(str(SAMPLE_PDF))
    docs = chunk_pages(pages)
    for doc in docs:
        doc.metadata["doc_id"] = "test-doc-id"

    assert all(doc.metadata["doc_id"] == "test-doc-id" for doc in docs)
    assert all(doc.metadata.get("page") is not None for doc in docs)
