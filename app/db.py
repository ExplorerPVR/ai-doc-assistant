"""Database connectivity, table initialization, and session dependency."""

import logging
import time
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

logger = logging.getLogger("app.db")

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)


def init_db(retries: int = 5, delay: float = 2.0) -> None:
    """Create database tables with startup retries for Postgres availability."""
    for attempt in range(1, retries + 1):
        try:
            SQLModel.metadata.create_all(engine)
            logger.info("Database tables initialized successfully.")
            return
        except Exception as err:
            logger.warning(
                f"Database connection attempt {attempt}/{retries} failed: {err}."
            )
            if attempt == retries:
                logger.error("Could not initialize database after maximum retries.")
                raise
            time.sleep(delay)


def get_session() -> Generator[Session, None, None]:
    """Yield a database session for each request lifecycle."""
    with Session(engine) as session:
        yield session
