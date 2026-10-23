# AI Document Assistant (`doc-assistant`)

A production-grade Python backend service representing Stage 1 of an AI Document Assistant platform. Future milestones extend this service with LLMs, vector embeddings, and Retrieval-Augmented Generation (RAG).

This initial service provides:
1. **Customer Review CSV Cleaner Pipeline (`scripts/clean_reviews.py`)**: Cleans messy datasets, strips whitespace, drops invalid/empty rows, removes duplicates, and features resilient I/O retry logic.
2. **FastAPI Document Ingestion Service (`app/`)**: High-performance asynchronous API providing PostgreSQL-backed file cataloging, strict MIME/extension validation (`.pdf`, `.txt`), disk persistence, and a health check probe (`/health`).
3. **Containerized Deployment (`Dockerfile`, `docker-compose.yml`)**: Single-command orchestrated multi-container setup with PostgreSQL 16 and automated health checks.
4. **CI/CD Quality Automation (`.github/workflows/ci.yml`)**: Automated formatting, linting, and testing pipeline with `ruff` and `pytest`.

---

## Quickstart: Run with Docker Compose

Run the entire application stack (PostgreSQL + FastAPI) with a single command:

```bash
# 1. Copy sample environment file
cp .env.example .env

# 2. Build and start services in detached mode
docker compose up --build
```

Once started:
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Service Health Probe**: [http://localhost:8000/health](http://localhost:8000/health)

---

## API Endpoints & Example `curl` Commands

### 1. Health Check Probe
Probes database connectivity using `SELECT 1`.

```bash
curl http://localhost:8000/health
```
**Response (`200 OK`)**:
```json
{"status": "ok"}
```

---

### 2. Upload a Document
Uploads and validates a `.pdf` or `.txt` document, saves bytes to disk with a collision-safe UUID prefix, and catalogs metadata in PostgreSQL.

```bash
# Upload a PDF document
curl -F "file=@sample.pdf" http://localhost:8000/documents

# Upload a plain text document
curl -F "file=@sample.txt" http://localhost:8000/documents
```
**Response (`201 Created`)**:
```json
{
  "id": 1,
  "filename": "sample.pdf",
  "content_type": "application/pdf",
  "size_bytes": 1024,
  "uploaded_at": "2026-10-23T09:30:00.000000Z"
}
```

**Validation & Error Responses**:
- Missing `file` field: `422 Unprocessable Entity`
- Unsupported file type or extension: `415 Unsupported Media Type` (`{"detail": "Unsupported file type. Allowed: PDF, TXT"}`)
- Empty file (0 bytes): `400 Bad Request` (`{"detail": "Empty file"}`)

---

### 3. List All Uploaded Documents
Lists all cataloged documents ordered by newest upload time first.

```bash
curl http://localhost:8000/documents
```
**Response (`200 OK`)**:
```json
[
  {
    "id": 2,
    "filename": "sample.txt",
    "content_type": "text/plain",
    "size_bytes": 512,
    "uploaded_at": "2026-10-23T09:35:00.000000Z"
  },
  {
    "id": 1,
    "filename": "sample.pdf",
    "content_type": "application/pdf",
    "size_bytes": 1024,
    "uploaded_at": "2026-10-23T09:30:00.000000Z"
  }
]
```

---

## Customer Reviews Cleaner CLI (`scripts/clean_reviews.py`)

Cleans customer reviews from messy CSV files, dropping empty rows and deduplicating records while preserving column order and row hierarchy. Decorated with an automated retry handler for fault-tolerant disk I/O.

### Command Line Usage:
```bash
uv run python scripts/clean_reviews.py input.csv output.csv
```

### Features:
- Preserves UTF-8 encoding, header row, and column ordering.
- Strips surrounding whitespace from each cell value.
- Detects and drops rows where all fields are empty or whitespace.
- Deduplicates matching rows, retaining the first occurrence.
- Outputs detailed summary counts to console and logger.
- Built-in `@retry(times=3, delay=0.5, exceptions=(OSError,))` decorator.

---

## Local Development & Testing

Ensure Python 3.12 and `uv` are installed.

```bash
# 1. Install dependencies into virtual environment
uv sync

# 2. Run Ruff Lint Check
uv run ruff check .

# 3. Run Ruff Format Check
uv run ruff format --check .

# 4. Run Pytest Suite (includes in-memory SQLite engine tests)
uv run pytest -v
```

---

## Dependencies Rationale

In strict accordance with project constraints, only the following core and dev packages are included:
- `fastapi`: High-performance async web framework.
- `uvicorn`: ASGI web server implementation.
- `sqlmodel`: Pydantic-powered ORM and schema modeling.
- `psycopg[binary]`: PostgreSQL 3 driver.
- `python-multipart`: Streaming parser for multipart form-data file uploads.
- `pydantic-settings`: Strongly-typed 12-factor configuration management.
- Dev only:
  - `pytest`: Automated test runner and fixture framework.
  - `httpx`: Async and sync HTTP test client for FastAPI.
  - `ruff`: High-speed linter and code formatter.

No additional external libraries have been added.

---

## Project Repository Layout

```text
doc-assistant/
  app/
    __init__.py
    main.py              # FastAPI app and lifespan management
    config.py            # Pydantic Settings configuration
    db.py                # Database engine and get_session dependency
    models.py            # SQLModel Document table and DocumentRead schema
    routers/
      __init__.py
      health.py          # GET /health probe endpoint
      documents.py       # POST /documents & GET /documents endpoints
    services/
      __init__.py
      storage.py         # File validation, byte reading, and disk storage
  scripts/
    __init__.py
    clean_reviews.py     # CSV cleaner CLI script with retry decorator
  tests/
    __init__.py
    conftest.py          # In-memory SQLite fixtures and test client overrides
    test_health.py       # Unit tests for /health probe
    test_documents.py    # Unit tests for upload validation and document listing
    test_clean_reviews.py# Unit tests for cleaner script and retry logic
  .github/
    workflows/
      ci.yml             # GitHub Actions CI workflow (lint + test)
  .dockerignore
  .env.example
  .gitignore
  Dockerfile
  docker-compose.yml
  pyproject.toml
  uv.lock
  README.md
```
