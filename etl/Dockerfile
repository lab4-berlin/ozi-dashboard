# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

ENV DUCKDB_EXTENSION_DIRECTORY=/opt/duckdb/extensions

# Copy the requirements file into the container at /app
COPY etl/requirements.txt requirements.txt
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pre-bake DuckDB extensions to /opt/duckdb/extensions
RUN python3 -c "import duckdb; con = duckdb.connect(); con.execute(\"SET extension_directory='/opt/duckdb/extensions'; INSTALL sqlite; INSTALL ducklake; INSTALL httpfs; INSTALL postgres_scanner;\")"

# Copy common package and etl directory content into container
COPY common /app/common
COPY etl /app/etl/
COPY lake_schema.sql /app/lake_schema.sql
COPY insert_countries.sql /app/insert_countries.sql

RUN mkdir -p /app/etl/logs

# Ensure the run script within etl is executable
RUN chmod +x /app/etl/run.sh
