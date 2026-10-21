# Multi-stage build for ETL production and test images using uv
FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install production dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY . /app/etl/

RUN mkdir -p /app/etl/logs && chmod +x /app/etl/run.sh

ENV PATH=/app/.venv/bin:$PATH

# Test stage: install dev dependencies into the existing virtualenv
FROM base AS test

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
