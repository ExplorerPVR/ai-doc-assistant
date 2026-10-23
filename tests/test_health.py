"""Unit tests for the /health endpoint."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db import get_session
from app.main import app


def test_health_check_success(client: TestClient) -> None:
    """Verify GET /health returns 200 and {'status': 'ok'} when database is healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_database_unreachable(client: TestClient) -> None:
    """Verify GET /health returns 503 when the database probe fails."""
    mock_session = MagicMock(spec=Session)
    mock_session.exec.side_effect = Exception("Connection dropped")

    def override_broken_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_broken_session
    try:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"detail": "database unreachable"}
    finally:
        app.dependency_overrides.clear()
