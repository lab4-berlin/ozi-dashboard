FROM python:3.10-slim

WORKDIR /app

ENV DUCKDB_EXTENSION_DIRECTORY=/opt/duckdb/extensions

COPY plotly_dash/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pre-bake DuckDB extensions to /opt/duckdb/extensions
RUN python3 -c "import duckdb; con = duckdb.connect(); con.execute(\"SET extension_directory='/opt/duckdb/extensions'; INSTALL sqlite; INSTALL ducklake; INSTALL httpfs;\")"

COPY common /app/common
COPY plotly_dash/dash_app.py .
COPY plotly_dash/generate_static_graph.py .

CMD ["gunicorn", "dash_app:app", "-b", "0.0.0.0:8050", "--workers", "2"]
