import pathlib

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

SAMPLE_CSV = pathlib.Path(__file__).parent.parent / "test_sample.csv"


def _ingest_sample_csv() -> str:
    with open(SAMPLE_CSV, "rb") as f:
        response = client.post("/ingest", files={"file": ("test_sample.csv", f, "text/csv")})
    assert response.status_code == 200
    return response.json()["doc_id"]


def test_repeated_query_is_served_from_cache() -> None:
    doc_id = _ingest_sample_csv()
    payload = {"question": "What is the score of Alice?", "doc_id": doc_id}

    first = client.post("/query", json=payload)
    assert first.status_code == 200
    assert first.headers["X-Cache"] == "MISS"

    second = client.post("/query", json=payload)
    assert second.status_code == 200
    assert second.headers["X-Cache"] == "HIT"

    assert first.content == second.content
