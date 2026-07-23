import io

from fastapi.testclient import TestClient

CONTENT = b"Name,Age,Score\nAlice,25,90\n"


def test_ingest_strips_path_traversal_from_filename(client: TestClient) -> None:
    response = client.post(
        "/ingest",
        files={"file": ("../../etc/evil_traversal_test.csv", io.BytesIO(CONTENT), "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    # The path components must be stripped — only the basename should survive.
    assert body["filename"] == "evil_traversal_test.csv"
    assert "/" not in body["filename"] and ".." not in body["filename"]


def test_document_file_serves_ingested_bytes(client: TestClient) -> None:
    ingest_response = client.post(
        "/ingest",
        files={"file": ("test_document_file_sample.csv", io.BytesIO(CONTENT), "text/csv")},
    )
    assert ingest_response.status_code == 200
    doc_id = ingest_response.json()["doc_id"]

    file_response = client.get(f"/documents/{doc_id}/file")
    assert file_response.status_code == 200
    assert file_response.content == CONTENT


def test_document_file_unknown_doc_id_returns_404(client: TestClient) -> None:
    response = client.get("/documents/does-not-exist/file")
    assert response.status_code == 404
