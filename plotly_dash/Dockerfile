FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY dash_app.py .
COPY generate_static_graph.py .

ENV PATH=/app/.venv/bin:$PATH

CMD ["gunicorn", "dash_app:app", "-b", "0.0.0.0:8050", "--workers", "2"]
