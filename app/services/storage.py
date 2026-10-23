"""Storage service handling file upload validation and disk persistence."""

import logging
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger("app.services.storage")

ALLOWED_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}


async def validate_and_save_file(
    file: UploadFile,
    upload_dir: Path,
) -> tuple[str, str, int, Path]:
    """Validate file type and size constraints, then write bytes to disk."""
    filename = file.filename or ""
    base_name = Path(filename).name
    ext = Path(base_name).suffix.lower()

    # Step 2: Type validation - allow only .pdf and .txt with exact content types
    if ext not in ALLOWED_TYPES or file.content_type != ALLOWED_TYPES[ext]:
        logger.warning(
            f"Rejected file '{base_name}': unsupported file type "
            f"(ext='{ext}', content_type='{file.content_type}')."
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Allowed: PDF, TXT",
        )

    # Step 3: Byte read and empty content check
    content = await file.read()
    size_bytes = len(content)
    if size_bytes == 0:
        logger.warning(f"Rejected file '{base_name}': empty file (0 bytes).")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    # Step 4: Save file to disk under upload directory
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}_{base_name}"
    stored_path = upload_dir / stored_name

    with open(stored_path, "wb") as f:
        f.write(content)

    logger.info(f"Successfully saved file '{base_name}' ({size_bytes} bytes).")
    return base_name, file.content_type, size_bytes, stored_path
