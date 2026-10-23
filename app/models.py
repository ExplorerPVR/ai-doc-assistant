"""SQLModel models for database tables and public API schemas."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    """Document database model storing file metadata."""

    id: int | None = Field(default=None, primary_key=True)
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stored_path: str


class DocumentRead(SQLModel):
    """Public schema for returning document metadata without internal storage path."""

    id: int
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
