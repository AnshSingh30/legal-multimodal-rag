import io

from fastapi.testclient import TestClient

FILENAME = "test_versioning_sample.csv"
CONTENT_V1 = b"Name,Age,Score\nAlice,25,90\nBob,30,85\nCharlie,28,88\n"
CONTENT_V2 = b"Name,Age,Score\nAlice,25,90\nBob,30,95\nCharlie,28,88\n"  # Bob's score changed 85 -> 95


def _ingest(client: TestClient, content: bytes) -> dict:
    response = client.post(
        "/ingest", files={"file": (FILENAME, io.BytesIO(content), "text/csv")}
    )
    assert response.status_code == 200
    return response.json()


def test_reingesting_same_filename_increments_version(client: TestClient) -> None:
    first = _ingest(client, CONTENT_V1)
    second = _ingest(client, CONTENT_V2)

    assert first["doc_id"] == second["doc_id"]
    assert second["document_version"] == first["document_version"] + 1


def test_versions_endpoint_lists_both_versions(client: TestClient) -> None:
    first = _ingest(client, CONTENT_V1)
    second = _ingest(client, CONTENT_V2)

    response = client.get(f"/documents/{first['doc_id']}/versions")
    assert response.status_code == 200
    versions = {v["document_version"]: v for v in response.json()}

    assert first["document_version"] in versions
    assert second["document_version"] in versions
    assert versions[second["document_version"]]["chunk_count"] == second["chunks_indexed"]


def test_diff_reflects_the_changed_row(client: TestClient) -> None:
    first = _ingest(client, CONTENT_V1)
    second = _ingest(client, CONTENT_V2)

    response = client.get(
        f"/documents/{first['doc_id']}/diff",
        params={"from": first["document_version"], "to": second["document_version"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["doc_id"] == first["doc_id"]

    changed = [e for e in body["entries"] if e["status"] == "changed"]
    assert len(changed) > 0
    # At least one changed chunk must be the row where Bob's score actually changed.
    assert any(
        "85" in (e["from_text"] or "") and "95" in (e["to_text"] or "")
        for e in changed
    )
    # No chunks were added or removed — same number of rows in both versions.
    assert not any(e["status"] in ("added", "removed") for e in body["entries"])


def test_diff_unknown_version_returns_404(client: TestClient) -> None:
    first = _ingest(client, CONTENT_V1)
    response = client.get(
        f"/documents/{first['doc_id']}/diff",
        params={"from": first["document_version"], "to": 999999},
    )
    assert response.status_code == 404


def test_versions_for_unknown_doc_id_returns_404(client: TestClient) -> None:
    response = client.get("/documents/does-not-exist/versions")
    assert response.status_code == 404
