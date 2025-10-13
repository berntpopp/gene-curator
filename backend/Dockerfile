# Multi-stage build for production optimization
FROM python:3.11-slim AS base

# Set environment variables for Python and uv
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv_cache \
    UV_LINK_MODE=copy

# Install system dependencies and uv globally
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && cp /root/.local/bin/uv /usr/local/bin/uv \
    && cp /root/.local/bin/uvx /usr/local/bin/uvx \
    && chmod +x /usr/local/bin/uv /usr/local/bin/uvx

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Development stage
FROM base AS development

# Create non-root user first
RUN useradd --create-home --shell /bin/bash app

# Install dependencies including dev dependencies
RUN uv sync --frozen --extra dev && rm -rf $UV_CACHE_DIR

# Copy application code and set ownership
COPY . .
RUN chown -R app:app /app

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

# Install only production dependencies
RUN uv sync --frozen --no-dev && rm -rf $UV_CACHE_DIR

# Copy application code and set ownership
COPY . .
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Production command
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]