"""Pytest fixtures for isolated in-memory testing."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.db as app_db
from app.config import settings
from app.db import get_session
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(name="session")
def session_fixture(monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    """Yield an isolated in-memory SQLite session with initialized tables."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(app_db, "engine", engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    """Provide a TestClient with temporary upload directory and SQLite."""
    temp_upload_dir = tmp_path / "uploads"
    temp_upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "upload_dir", temp_upload_dir)

    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
