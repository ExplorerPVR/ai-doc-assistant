FROM python:3.12-slim

# Install uv binary from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory inside container
WORKDIR /app

# Enable bytecode compilation and use installed virtual environment
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

# Copy project specification and lock files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies without development tooling
RUN uv sync --frozen --no-dev

# Copy application source code
COPY app ./app
COPY scripts ./scripts

# Run as non-root user and ensure upload directory permissions
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/uploads && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
