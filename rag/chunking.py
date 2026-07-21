from datetime import date
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def _bbox_for_chunk(chunk_text: str, lines: list[dict]) -> Optional[list[float]]:
    """Approximate a chunk's bounding box as the union of every source line
    it contains. The splitter operates on the page's flattened text, so
    alignment here is done by substring containment against reconstructed
    line text rather than exact character offsets — an approximation, not
    a pixel-perfect span mapping."""
    matched = [line["bbox"] for line in lines if line["text"] and line["text"] in chunk_text]
    if not matched:
        return None
    return [
        min(b[0] for b in matched),
        min(b[1] for b in matched),
        max(b[2] for b in matched),
        max(b[3] for b in matched),
    ]


def chunk_pages(pages: list[dict]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    docs = []
    for page in pages:
        if page.get("metadata", {}).get("data_type") == "tabular":
            docs.append(Document(
                page_content=page["text"],
                metadata={
                    **page["metadata"],
                    "page": page["metadata"].get("page"),
                    "bbox": page["metadata"].get("bbox"),
                    "date_ingested": str(date.today())
                }
            ))
        else:
            lines = page.get("lines", [])
            chunks = splitter.split_text(page["text"])
            for i, chunk in enumerate(chunks):
                docs.append(Document(
                    page_content=chunk,
                    metadata={
                        "source": page["source"],
                        "page": page["page"],
                        "chunk_index": i,
                        "method": page.get("method", "text"),
                        "bbox": _bbox_for_chunk(chunk, lines),
                        "date_ingested": str(date.today())
                    }
                ))
    return docs
