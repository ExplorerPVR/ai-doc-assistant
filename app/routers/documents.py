"""Document management endpoints for uploading and querying stored documents."""

import logging
from collections.abc import Sequence

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models import Document, DocumentRead
from app.services.storage import validate_and_save_file

logger = logging.getLogger("app.routers.documents")
router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> DocumentRead:
    """Validate upload, store bytes on disk, and persist metadata in database."""
    base_name, content_type, size_bytes, stored_path = await validate_and_save_file(
        file=file,
        upload_dir=settings.upload_dir,
    )

    doc = Document(
        filename=base_name,
        content_type=content_type,
        size_bytes=size_bytes,
        stored_path=str(stored_path),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    logger.info(f"Persisted document record ID {doc.id} for '{doc.filename}'.")
    return DocumentRead.model_validate(doc)


@router.get("", response_model=list[DocumentRead], status_code=status.HTTP_200_OK)
def list_documents(
    session: Session = Depends(get_session),
) -> Sequence[Document]:
    """Retrieve all document records ordered by newest upload first."""
    statement = select(Document).order_by(Document.uploaded_at.desc())
    return session.exec(statement).all()
