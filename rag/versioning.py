import difflib
import hashlib
import pathlib
from typing import Any, Optional

from langchain_chroma import Chroma


def compute_doc_id(filename: str) -> str:
    """Stable identifier for a logical document, derived from its filename so
    re-ingesting a file by the same name is recognized as a new version of
    the same document rather than an unrelated one."""
    return hashlib.sha256(filename.encode("utf-8")).hexdigest()[:16]


def compute_content_hash(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def get_filename_for_doc(vectorstore: Chroma, doc_id: str) -> Optional[str]:
    """The original filename for a doc_id, taken from any of its chunks
    (all versions share the same filename by construction — see compute_doc_id).
    None if no chunks exist for this doc_id at all.

    rag/ingestion.py's extractors store "source" as the full save path (e.g.
    "uploads/foo.pdf"), not the bare filename — .name strips that back down
    so callers can safely join it under their own upload directory without
    ending up with a doubled "uploads/uploads/foo.pdf"."""
    result = vectorstore._collection.get(where={"doc_id": doc_id}, include=["metadatas"], limit=1)
    if not result["metadatas"]:
        return None
    source = result["metadatas"][0].get("source")
    return pathlib.Path(source).name if source else None


def get_latest_version(vectorstore: Chroma, doc_id: str) -> int:
    """0 if no *versioned* chunks exist yet for this doc_id — either nothing
    has been ingested for it, or only pre-versioning legacy chunks exist
    (no document_version metadata at all, since that field is new). Only
    counting chunks that actually carry the field keeps this consistent with
    the $and doc_id+document_version filter used elsewhere: a chunk without
    the field wouldn't match that filter regardless of what default we'd
    otherwise assume for it."""
    result = vectorstore._collection.get(where={"doc_id": doc_id}, include=["metadatas"])
    versions = [m["document_version"] for m in result["metadatas"] if "document_version" in m]
    return max(versions, default=0)


def list_versions(vectorstore: Chroma, doc_id: str) -> list[dict]:
    result = vectorstore._collection.get(where={"doc_id": doc_id}, include=["metadatas"])
    by_version: dict[int, dict] = {}
    for meta in result["metadatas"]:
        if "document_version" not in meta:
            continue
        version = meta["document_version"]
        entry = by_version.setdefault(version, {
            "document_version": version,
            "filename": meta.get("source", "unknown"),
            "content_hash": meta.get("content_hash"),
            "date_ingested": meta.get("date_ingested"),
            "chunk_count": 0,
        })
        entry["chunk_count"] += 1
    return sorted(by_version.values(), key=lambda v: v["document_version"])


def _diff_key(metadata: dict) -> str:
    """Alignment key for matching a chunk across two versions. Not robust to
    chunk-boundary reflow from unrelated edits — a straightforward
    position/row-based alignment, not semantic diffing, per spec."""
    if metadata.get("data_type") == "tabular":
        return f"row:{metadata.get('row_index', metadata.get('chunk_type', 'schema'))}"
    return f"page:{metadata.get('page')}:chunk:{metadata.get('chunk_index')}"


def get_chunks_for_version(vectorstore: Chroma, doc_id: str, version: int) -> dict[str, dict]:
    """{diff_key: {"text": ..., "metadata": ...}} for every chunk in this version."""
    result = vectorstore._collection.get(
        where={"$and": [{"doc_id": doc_id}, {"document_version": version}]},
        include=["metadatas", "documents"],
    )
    chunks = {}
    for text, meta in zip(result["documents"], result["metadatas"]):
        chunks[_diff_key(meta)] = {"text": text, "metadata": meta}
    return chunks


def diff_versions(from_chunks: dict[str, dict], to_chunks: dict[str, dict]) -> list[dict[str, Any]]:
    """Chunk-level diff between two chunk sets keyed by _diff_key(). Only
    added/removed/changed entries are returned — unchanged chunks are omitted."""
    entries = []
    all_keys = sorted(set(from_chunks) | set(to_chunks), key=str)

    for key in all_keys:
        before = from_chunks.get(key)
        after = to_chunks.get(key)

        if before is None:
            entries.append({"key": key, "status": "added", "from_text": None, "to_text": after["text"], "diff": None})
        elif after is None:
            entries.append({"key": key, "status": "removed", "from_text": before["text"], "to_text": None, "diff": None})
        elif before["text"] != after["text"]:
            diff_lines = list(difflib.unified_diff(
                before["text"].splitlines(), after["text"].splitlines(),
                lineterm="", fromfile=f"{key} (from)", tofile=f"{key} (to)",
            ))
            entries.append({
                "key": key, "status": "changed",
                "from_text": before["text"], "to_text": after["text"], "diff": diff_lines,
            })
        # else: unchanged — omitted

    return entries
