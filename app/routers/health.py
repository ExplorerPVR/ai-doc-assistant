"""Health check endpoint to probe database availability."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlmodel import Session

from app.db import get_session

logger = logging.getLogger("app.routers.health")
router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(session: Session = Depends(get_session)) -> dict[str, str]:
    """Execute SELECT 1 query to confirm database connectivity."""
    try:
        session.exec(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as err:
        logger.error(f"Health check probe failed: {err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unreachable",
        )
