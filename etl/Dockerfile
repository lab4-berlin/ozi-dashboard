# Use an official Python runtime as a parent image
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory in the container
WORKDIR /app

# Install production dependencies from uv.lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

ENV PATH="/app/.venv/bin:$PATH"

# Copy the etl directory content into the container at /app/etl
COPY . /app/etl/

RUN mkdir -p /app/etl/logs

# Ensure the run script within etl is executable (if it's used by the python code)
# Although our primary CMD is different, this maintains its executable state if needed.
RUN chmod +x /app/etl/run.sh
