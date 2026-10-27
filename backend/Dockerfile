# syntax=docker/dockerfile:1
# Base images are pinned by digest; Dependabot (docker ecosystem) bumps tag and digest together.
# All dependencies ship wheels, so no compiler or libpq is installed.
FROM ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa AS uv

FROM python:3.12-slim@sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin app
WORKDIR /app
EXPOSE 8000

# Development stage (docker-compose.dev.yml mounts the source over /app)
FROM base AS development
COPY --from=uv /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --extra dev --no-install-project
COPY --chown=app:app . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --extra dev
USER app
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Build stage: dependencies first (cached until uv.lock changes), then the code
FROM base AS build
COPY --from=uv /uv /usr/local/bin/
ENV UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Production stage: no uv, no build cache; code and venv stay root-owned (read-only to the app user)
FROM base AS production
COPY --from=build /app /app
USER app
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
