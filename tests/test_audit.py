import os
import pathlib
import uuid

from fastapi.testclient import TestClient

SAMPLE_CSV = pathlib.Path(__file__).parent.parent / "test_sample.csv"
ADMIN_KEY = os.getenv("ADMIN_KEY")


def _ingest_sample_csv(client: TestClient) -> str:
    with open(SAMPLE_CSV, "rb") as f:
        response = client.post("/ingest", files={"file": ("test_sample.csv", f, "text/csv")})
    assert response.status_code == 200
    return response.json()["doc_id"]


def test_audit_recent_requires_admin_key(client: TestClient) -> None:
    response = client.get("/audit/recent")
    assert response.status_code == 403


def test_audit_recent_rejects_wrong_admin_key(client: TestClient) -> None:
    response = client.get("/audit/recent", headers={"X-Admin-Key": "wrong-key"})
    assert response.status_code == 403


def test_query_shows_up_in_audit_recent(client: TestClient) -> None:
    assert ADMIN_KEY, "ADMIN_KEY must be set in the environment for this test to run"

    doc_id = _ingest_sample_csv(client)
    # Unique question so this test can find *its* entry even if other tests already logged queries.
    question = f"What is the score of Alice? (test marker {uuid.uuid4().hex})"

    query_response = client.post("/query", json={"question": question, "doc_id": doc_id})
    assert query_response.status_code == 200

    audit_response = client.get(
        "/audit/recent", params={"limit": 20}, headers={"X-Admin-Key": ADMIN_KEY}
    )
    assert audit_response.status_code == 200
    entries = audit_response.json()
    matching = [e for e in entries if e["query_text"] == question]
    assert len(matching) == 1

    entry = matching[0]
    assert entry["doc_id"] == doc_id
    assert entry["final_answer"] == query_response.json()["answer"]
    assert entry["confidence"] == query_response.json()["confidence"]
    assert entry["cache_hit"] is False
