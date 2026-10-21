# Plan: adopt uv across `etl/` and `plotly_dash/`

Goal: replace `pip` with `uv` for faster Docker builds and a NixOS-friendly
local environment (pip does not work properly on NixOS, uv does).

Decisions made:

- **Full uv adoption** (`pyproject.toml` + `uv.lock` per component, `uv sync`
  in Dockerfiles) instead of a minimal `pip` → `uv pip` swap.
- **Testing stays Docker-only** (Compose + pytest entrypoint as today); uv is
  the local host env option, not a new test workflow.
- **BuildKit enabled** — drop `DOCKER_BUILDKIT=0` from CI so Docker cache
  mounts work (biggest rebuild speedup when only code changes).
- **Unify on Python 3.13** — bump `plotly_dash` from 3.10 to 3.13.
- **Multi-stage test build** — use multi-stage `target: test` inside `etl/Dockerfile`
  rather than a separate `Dockerfile.test` depending on an external image tag name.
- **Container link mode** — set `ENV UV_LINK_MODE=copy` for robust wheel installations
  across container mount boundaries.
- **SQLAlchemy <2.1 constraint** — constrain `SQLAlchemy>=2.0.36,<2.1` so that
  `postgresql://` continues to use `psycopg2-binary` instead of defaulting to `psycopg` (v3).

## 1. `etl/` → uv project

- **New `etl/pyproject.toml`**: declare direct deps and dev dependency group:

  ```toml
  [project]
  name = "ozi-etl"
  version = "0.1.0"
  requires-python = ">=3.13, <3.14"
  dependencies = [
      "httpx>=0.27.2",
      "requests>=2.32.3",
      "rich>=13.9.4",
      "SQLAlchemy>=2.0.36,<2.1",
      "tenacity>=9.0.0",
      "psycopg2-binary>=2.9.11",
      "pyyaml>=6.0.2",
  ]

  [dependency-groups]
  dev = [
      "pytest>=8.0.0",
      "pytest-asyncio>=0.24.0",
      "requests-mock>=1.12.0",
      "respx>=0.22.0",
  ]

  [tool.uv]
  package = false
  ```

- **Pinned python**: `etl/.python-version` set to `3.13`.
- **New `etl/uv.lock`** generated with `uv lock` and committed — reproducible
  builds everywhere (Docker, CI, NixOS host).
- **Multi-stage `etl/Dockerfile`**:

  ```dockerfile
  FROM python:3.13-slim AS base
  COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /bin/
  ENV UV_COMPILE_BYTECODE=1 \
      UV_LINK_MODE=copy
  WORKDIR /app
  COPY pyproject.toml uv.lock ./
  RUN --mount=type=cache,target=/root/.cache/uv \
      uv sync --frozen --no-dev --no-install-project
  COPY . /app/etl/
  RUN mkdir -p /app/etl/logs && chmod +x /app/etl/run.sh
  ENV PATH=/app/.venv/bin:$PATH

  FROM base AS test
  RUN --mount=type=cache,target=/root/.cache/uv \
      uv sync --frozen --no-install-project
  ```

  `PATH` includes `/app/.venv/bin` so the existing
  `docker compose run ozi-etl python3 …` invocations and CI
  `--entrypoint "pytest"` keep working unchanged.
- **Removed `etl/Dockerfile.test`**: Replaced by `target: test` in `docker-compose.test.yml`.

## 2. `plotly_dash/` → uv project

- **New `plotly_dash/pyproject.toml`**:
  `requires-python = ">=3.13, <3.14"`; deps: `dash>=2.18.0`, `plotly>=5.24.0`,
  `pandas>=2.2.0`, `sqlalchemy>=2.0.36,<2.1`, `psycopg2-binary>=2.9.11`, `gunicorn>=23.0.0`
  + `[tool.uv] package = false`.
- **Pinned python**: `plotly_dash/.python-version` set to `3.13`.
- **New `plotly_dash/uv.lock`** via `uv lock`.
- **Rewrite `plotly_dash/Dockerfile`**: base switched to `python:3.13-slim`,
  `ENV PATH=/app/.venv/bin:$PATH`, `UV_LINK_MODE=copy`, and `CMD ["gunicorn", "dash_app:app", …]`.

## 3. `.dockerignore` files

Build contexts are `./etl` and `./plotly_dash`, so the root `.dockerignore`
does **not** apply. Context-local `.dockerignore` files:

- `etl/.dockerignore`: `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `logs/`
- `plotly_dash/.dockerignore`: `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`

This prevents a local `uv sync` output or build cache from being baked into the image.

## 4. CI speedup (`.github/workflows/ci.yml`)

- Drop `DOCKER_BUILDKIT=0` from both steps so BuildKit cache mounts work.
- Update `docker-compose.test.yml` to target `test` stage in `etl/Dockerfile`.

## 5. Cleanup & docs

- Deleted `etl/requirements.txt`, `etl/requirements-dev.txt`, `etl/Dockerfile.test`,
  and `plotly_dash/requirements.txt`.
- README updated with "Local Development with uv" section for NixOS and local hosts.
- Updated `etl/config.sh` to auto-detect `.venv`.

## Verification checklist

1. `uv lock` in both dirs.
2. `docker compose build ozi-etl plotly-dash-app`.
3. `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm \
   --build --entrypoint "pytest" ozi-etl`.
4. Test-profile `docker compose up`; confirm the dash app serves on :8050.
