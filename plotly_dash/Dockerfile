FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

ENV PATH="/app/.venv/bin:$PATH"

COPY dash_app.py .
COPY generate_static_graph.py .

CMD ["gunicorn", "dash_app:app", "-b", "0.0.0.0:8050", "--workers", "2"]
