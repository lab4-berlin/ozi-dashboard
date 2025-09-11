# ozi-dashboard

This project provides an ETL pipeline and a PostgreSQL database to store and analyze AS (Autonomous System) statistics. It also includes an optional Redash service for data visualization.

## Prerequisites

- Docker Engine
- Docker Compose

## Quick Start

For a quick start, you can use the provided example files:

```sh
cp .env.ozi.example .env.ozi
cp .env.redash.example .env.redash
```

This will create the required `.env.ozi` and `.env.redash` files with default credentials that you can use to get started quickly.

## Setup

1.  **Environment Variables:**

    Create two environment files in the root of the project: `.env.ozi` and `.env.redash`.

    **`.env.ozi`**

    This file stores the credentials for the OZI PostgreSQL database. Create the file and add the following content, replacing the placeholder values with your desired credentials:

    ```env
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=password
    POSTGRES_OZI_USER=ozi
    POSTGRES_OZI_PASSWORD=ozi_password
    POSTGRES_DB=ozi_db2
    ```

    You can also copy the `.env.ozi.example` file:

    ```sh
    cp .env.ozi.example .env.ozi
    ```

    **`.env.redash`**

    This file stores the credentials for the Redash services. Create the file and add the following content:

    ```env
    REDASH_COOKIE_SECRET=placeholder
    REDASH_SECRET_KEY=placeholder
    REDASH_POSTGRES_PASSWORD=placeholder
    ```

    You can also copy the `.env.redash.example` file:

    ```sh
    cp .env.redash.example .env.redash
    ```

    To generate strong random values for `REDASH_COOKIE_SECRET`, `REDASH_SECRET_KEY`, and `REDASH_POSTGRES_PASSWORD`, you can use the following command:

    ```sh
    # For REDASH_COOKIE_SECRET and REDASH_SECRET_KEY
    openssl rand -hex 32

    # For REDASH_POSTGRES_PASSWORD
    openssl rand -hex 16
    ```

    Copy the generated values into the `.env.redash` file.

2.  **Build and Run:**

    To build the images and start the services, run the following command from the project root:

    ```sh
    docker compose up -d
    ```

    This will start the `ozi-postgres` and `ozi-etl` services.

3.  **Running Redash (Optional):**

    To run the Redash services, you first need to create the database tables. Run the following command:

    ```sh
    docker compose run --rm redash-server create_db
    ```

    Then, to start the Redash services, use the `redash` profile:

    ```sh
    docker compose --profile redash up -d
    ```

## Accessing Services

Services are accessible in two ways:

-   **From your local machine (the host):** Services with published ports can be accessed via `localhost`.
    -   **OZI PostgreSQL:** `localhost:5432`
    -   **Redash:** `http://localhost:5000`
-   **From other services within Docker:** Services connect to each other using their service names as hostnames. For example, the `ozi-etl` service connects to the database at `ozi-postgres:5432`.

You can monitor the ETL service logs with:
```sh
docker compose logs -f ozi-etl
```

## Running a Specific ETL Job

The ETL service can be used to run specific jobs by passing command-line arguments to the `etl` service. The available tasks are `ASNS`, `STATS_1D`, `STATS_5M`, `ASN_NEIGHBOURS`, `TRAFFIC`, and `INTERNET_QUALITY`.

Here is an example of how to run the `ASN_NEIGHBOURS` task for the Czech Republic for May 2025:

```sh
docker compose run ozi-etl -t ASN_NEIGHBOURS -c CZ -df 2025-05-01 -dt 2025-05-31 -dr D
```

## Running Tests

To run the ETL tests, which utilize a separate named volume for the PostgreSQL database to ensure a clean and isolated test environment, use the following command:

```sh
DOCKER_BUILDKIT=0 docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build --entrypoint "pytest" ozi-etl
```

*   `DOCKER_BUILDKIT=0`: This disables Docker BuildKit, which can sometimes cause issues with `act` or specific Docker Compose setups.
*   `-f docker-compose.yml`: Includes your main Docker Compose configuration.
*   `-f docker-compose.test.yml`: Overrides the volume configuration for the `ozi-postgres` service, ensuring tests use a named volume instead of a bind mount.
*   `--rm`: Removes the container after the command exits.
*   `--build`: Builds the `ozi-etl` service image if it's not up-to-date.
*   `--entrypoint "pytest"`: Overrides the default entrypoint of the `ozi-etl` container to run `pytest`.
*   `ozi-etl`: Specifies the service to run the command against.

## Local CI Simulation with `act`

You can simulate the GitHub Actions CI workflow locally using `act`. This is useful for debugging and testing your CI pipeline without pushing to GitHub.

**Prerequisites for `act`:**

*   `act` installed, https://github.com/nektos/act.
*   Docker Engine running on your machine.

To run the `pull_request` workflow defined in `.github/workflows/ci.yml` locally:

```sh
act pull_request
```

## Running Daily STATS_1D Job

The daily STATS_1D ETL job is now scheduled and managed via a GitHub Actions workflow. This workflow automatically fetches the latest STATS_1D data. The job:

1. Determines the last date in the database
2. Runs the ETL job from that date to today
3. Prevents duplicate data by only inserting new records

The workflow is configured to run daily at 2:00 AM UTC.

You can find the workflow definition at `.github/workflows/etl_daily_stats.yml`.

To manually trigger this job, you can navigate to the "Actions" tab in your GitHub repository, select the "ETL Daily Stats" workflow, and click "Run workflow".

## Stopping Services

To stop the services, run:

```sh
docker compose down
```

To stop the Redash services as well, run:

```sh
docker compose --profile redash down
```

If you want to remove the volumes (including PostgreSQL data), use:

```sh
docker compose down -v
```
