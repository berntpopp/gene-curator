# Base images are pinned by digest; Dependabot (docker ecosystem) bumps tag and digest together.
# All dependencies ship wheels, so no compiler or libpq is installed.
FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv

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
# X-Forwarded-For is trusted only from FORWARDED_ALLOW_IPS (uvicorn reads it; unset = 127.0.0.1).
# Set it to your reverse proxy's address only, never a Docker range: published ports show
# external clients as the bridge gateway, so a broad range lets anyone spoof their IP.
# ponytail: rate-limit buckets are per worker, so 4 workers allow up to 4x the configured rate
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
