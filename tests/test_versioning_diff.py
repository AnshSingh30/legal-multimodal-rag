from rag.versioning import _diff_key, diff_versions


def test_diff_key_uses_row_index_for_tabular() -> None:
    assert _diff_key({"data_type": "tabular", "row_index": 2}) == "row:2"
    assert _diff_key({"data_type": "tabular", "chunk_type": "schema_summary"}) == "row:schema_summary"


def test_diff_key_uses_page_and_chunk_index_for_text() -> None:
    assert _diff_key({"page": 3, "chunk_index": 1}) == "page:3:chunk:1"


def test_diff_versions_detects_changed_chunk() -> None:
    from_chunks = {"row:0": {"text": "Alice, 90", "metadata": {}}}
    to_chunks = {"row:0": {"text": "Alice, 95", "metadata": {}}}

    entries = diff_versions(from_chunks, to_chunks)
    assert len(entries) == 1
    assert entries[0]["status"] == "changed"
    assert entries[0]["from_text"] == "Alice, 90"
    assert entries[0]["to_text"] == "Alice, 95"
    assert entries[0]["diff"] is not None


def test_diff_versions_detects_added_and_removed() -> None:
    from_chunks = {"row:0": {"text": "Alice", "metadata": {}}}
    to_chunks = {"row:0": {"text": "Alice", "metadata": {}}, "row:1": {"text": "Bob", "metadata": {}}}

    entries = diff_versions(from_chunks, to_chunks)
    assert len(entries) == 1
    assert entries[0] == {"key": "row:1", "status": "added", "from_text": None, "to_text": "Bob", "diff": None}


def test_diff_versions_omits_unchanged_chunks() -> None:
    from_chunks = {"row:0": {"text": "Alice", "metadata": {}}}
    to_chunks = {"row:0": {"text": "Alice", "metadata": {}}}

    assert diff_versions(from_chunks, to_chunks) == []
