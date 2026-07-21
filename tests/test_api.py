import pathlib

import pytest
from fastapi.testclient import TestClient
from openai import AuthenticationError

from api.main import app

client = TestClient(app)

SAMPLE_CSV = pathlib.Path(__file__).parent.parent / "test_sample.csv"


def _ingest_sample_csv() -> str:
    with open(SAMPLE_CSV, "rb") as f:
        response = client.post(
            "/ingest",
            files={"file": ("test_sample.csv", f, "text/csv")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["chunks_indexed"] > 0
    return body["doc_id"]


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_sample_csv() -> None:
    doc_id = _ingest_sample_csv()
    assert doc_id


# xfail: OPENROUTER_API_KEY in .env is currently rejected by OpenRouter
# (401 "User not found"), independent of this code. Remove xfail once the
# key is rotated to a valid one and confirm this passes end-to-end.
@pytest.mark.xfail(raises=AuthenticationError, reason="OPENROUTER_API_KEY in .env is invalid/expired")
def test_query_sample_csv() -> None:
    doc_id = _ingest_sample_csv()

    query_response = client.post(
        "/query",
        json={"question": "What is the score of Alice?", "doc_id": doc_id},
    )
    assert query_response.status_code == 200
    query_body = query_response.json()
    assert query_body["answer"].strip() != ""
    assert query_body["confidence"] == "high"
    assert len(query_body["source_documents"]) > 0

    # Citations must be grounded in the document we actually ingested and reference a real page.
    assert len(query_body["citations"]) > 0
    for citation in query_body["citations"]:
        assert citation["doc_id"] == doc_id
        assert citation["page_number"] is not None
        assert citation["chunk_text"].strip() != ""


# xfail: same broken OPENROUTER_API_KEY as test_query_sample_csv.
@pytest.mark.xfail(raises=AuthenticationError, reason="OPENROUTER_API_KEY in .env is invalid/expired")
def test_query_unrelated_question_abstains() -> None:
    doc_id = _ingest_sample_csv()

    query_response = client.post(
        "/query",
        json={"question": "What is the capital of France?", "doc_id": doc_id},
    )
    assert query_response.status_code == 200
    query_body = query_response.json()
    assert query_body["confidence"] in ("low", "medium")
    assert query_body["answer"] != ""
    assert query_body["citations"] == []
    assert query_body["chart"] is None
