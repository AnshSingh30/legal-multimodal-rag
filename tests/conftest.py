import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="session")
def client():
    """Session-scoped so FastAPI's lifespan (which creates the audit_log
    table) runs exactly once, and every test shares one event loop for the
    async DB engine — a fresh TestClient per test file leaks the engine's
    pooled connections across event loops and breaks on the second one."""
    with TestClient(app) as c:
        yield c
