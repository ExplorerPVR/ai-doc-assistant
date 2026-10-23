"""Integration tests for /documents upload and listing endpoints."""

import io
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.models import Document


def test_get_documents_with_no_uploads(client: TestClient) -> None:
    """Verify GET /documents returns 200 and [] when no documents have been uploaded."""
    response = client.get("/documents")
    assert response.status_code == 200
    assert response.json() == []


def test_upload_small_valid_pdf(client: TestClient) -> None:
    """Verify upload of valid PDF returns 201 without stored_path."""
    pdf_content = b"%PDF-1.4 Mock valid PDF binary header and content"
    files = {"file": ("report.pdf", io.BytesIO(pdf_content), "application/pdf")}

    response = client.post("/documents", files=files)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] is not None
    assert data["filename"] == "report.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["size_bytes"] == len(pdf_content)
    assert "uploaded_at" in data
    assert "stored_path" not in data


def test_upload_valid_txt(client: TestClient) -> None:
    """Verify upload of valid text file returns 201 and stores metadata."""
    txt_content = b"Sample text content for testing purposes."
    files = {"file": ("notes.txt", io.BytesIO(txt_content), "text/plain")}

    response = client.post("/documents", files=files)
    assert response.status_code == 201

    data = response.json()
    assert data["filename"] == "notes.txt"
    assert data["content_type"] == "text/plain"
    assert data["size_bytes"] == len(txt_content)


def test_upload_empty_txt_returns_400(client: TestClient, session: Session) -> None:
    """Verify upload of empty file returns 400 and persists nothing to disk or DB."""
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}

    response = client.post("/documents", files=files)
    assert response.status_code == 400
    assert response.json() == {"detail": "Empty file"}

    # Verify nothing was saved in the database
    docs = session.exec(select(Document)).all()
    assert len(docs) == 0

    # Verify nothing was written to upload_dir
    files_on_disk = list(settings.upload_dir.glob("*"))
    assert len(files_on_disk) == 0


def test_upload_png_returns_415(client: TestClient, session: Session) -> None:
    """Verify upload of unsupported image type returns 415 and persists nothing."""
    png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    files = {"file": ("avatar.png", io.BytesIO(png_content), "image/png")}

    response = client.post("/documents", files=files)
    assert response.status_code == 415
    assert response.json() == {"detail": "Unsupported file type. Allowed: PDF, TXT"}

    # Verify nothing was saved in the database
    docs = session.exec(select(Document)).all()
    assert len(docs) == 0

    # Verify nothing was written to upload_dir
    files_on_disk = list(settings.upload_dir.glob("*"))
    assert len(files_on_disk) == 0


def test_post_documents_with_no_file(client: TestClient) -> None:
    """Verify POST /documents without file field returns 422 Unprocessable Entity."""
    response = client.post("/documents")
    assert response.status_code == 422


def test_get_documents_after_two_uploads(client: TestClient) -> None:
    """Verify GET /documents returns 200 with two uploaded documents, newest first."""
    first_file = {"file": ("first.txt", io.BytesIO(b"first file"), "text/plain")}
    res1 = client.post("/documents", files=first_file)
    assert res1.status_code == 201

    second_file = {
        "file": ("second.pdf", io.BytesIO(b"%PDF-1.4 second"), "application/pdf")
    }
    res2 = client.post("/documents", files=second_file)
    assert res2.status_code == 201

    list_resp = client.get("/documents")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 2
    # Verify newest first order
    assert items[0]["filename"] == "second.pdf"
    assert items[1]["filename"] == "first.txt"


def test_uploaded_file_exists_on_disk_in_temp_upload_folder(client: TestClient) -> None:
    """Verify uploaded file is written to temp upload dir and matches size_bytes."""
    content = b"%PDF-1.4 test document on disk payload"
    files = {"file": ("sample.pdf", io.BytesIO(content), "application/pdf")}

    response = client.post("/documents", files=files)
    assert response.status_code == 201
    size_bytes = response.json()["size_bytes"]

    # Check file exists on disk in the temp upload directory
    stored_files = list(Path(settings.upload_dir).glob("*_sample.pdf"))
    assert len(stored_files) == 1
    disk_file = stored_files[0]
    assert disk_file.is_file()
    assert disk_file.stat().st_size == len(content) == size_bytes
    assert disk_file.read_bytes() == content
