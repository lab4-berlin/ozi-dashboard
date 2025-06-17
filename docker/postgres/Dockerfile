# Use an official PostgreSQL image
FROM postgres:13-alpine

# Copy initialization SQL script
COPY create_database_schema.sql /docker-entrypoint-initdb.d/
# Expose the default PostgreSQL port
EXPOSE 5432
