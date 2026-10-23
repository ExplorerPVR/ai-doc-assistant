"""Main application entrypoint for the AI Document Assistant service."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import init_db
from app.routers import documents, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Execute startup database initialization and directory setup."""
    logger.info("Initializing document assistant service...")
    init_db()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Service shutdown completed.")


app = FastAPI(
    title="doc-assistant",
    lifespan=lifespan,
    docs_url="/docs",
)

app.include_router(health.router)
app.include_router(documents.router)
