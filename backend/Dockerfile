# Multi-stage build for production optimization
FROM python:3.12-slim AS base

# Install uv from official image (replaces curl-based install)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set environment variables for Python and uv
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv_cache \
    UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Development stage
FROM base AS development

# Create non-root user first
RUN useradd --create-home --shell /bin/bash app

# Install dependencies including dev dependencies
RUN uv sync --frozen --extra dev && rm -rf $UV_CACHE_DIR

# Copy application code with correct ownership
COPY --chown=app:app . .

# Switch to non-root user and set environment
USER app
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Development command (will be overridden by docker-compose)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production

# Create non-root user first
RUN useradd --create-home --shell /bin/bash app

# Enable bytecode compilation for production performance
ENV UV_COMPILE_BYTECODE=1

# Install only production dependencies (two-step for layer caching)
RUN uv sync --frozen --no-dev --no-install-project && rm -rf $UV_CACHE_DIR

# Copy application code with correct ownership
COPY --chown=app:app . .

# Install project itself (separate layer for better caching)
RUN uv sync --frozen --no-dev && rm -rf $UV_CACHE_DIR

# Switch to non-root user
USER app
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Production command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
