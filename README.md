# ozi-dashboard

## Quickstart

1. **Create a Postgres instance on GCP**, name it `asn-stats`.
2. **Set a strong password** for user `postgres` while creating the DB.
3. **Go to the `asn-stats` console**.
4. **Download the code by cloning the Git repository:**

    ```sh
    git clone https://github.com/lab4-berlin/ozi-dashboard
    cd ozi-dashboard
    ```

5. **Create the database, user, and tables for the asn_stats project:**

    - When prompted, use the `postgres` password from step 2 first,
    - and the `asn_data` password for the second SQL script.

    ```sh
    ./init_database.sh
    ```

## Temporary: Running SQL Scripts Manually

```sh
cat sql/*.sql | gcloud sql connect asn-stats --user=asn_stats
```

## Dagster (Optional)

If you want to use Dagster for orchestration:

```sh
sudo apt install python3-pip
sudo apt install python3.12-venv
python3 -m venv dagster_env
source dagster_env/bin/activate
pip install dagster dagster-webserver dagster-postgres
dagster project scaffold --name=dagster_etl
```

## Dockerization

This application can be built and run as a Docker container.

### Prerequisites

- Docker installed on your system.
- A running PostgreSQL database accessible to the container.
- The database schema should be initialized (e.g., by running the SQL scripts like `create_database_schema.sql` and `insert_countries.sql` against your target database).

### Building the Image

To build the Docker image, navigate to the root directory of the project (where the `etl/Dockerfile` is located) and run:

```sh
docker build -t as-stats-etl -f etl/Dockerfile etl
```

### Running the Container

To run the Docker container, provide environment variables for database configuration and specify the path to the job YAML file you want to execute.

**Environment Variables:**

- `DB_USER`: The username for the database.
- `DB_PASS`: The password for the database user.
- `DB_NAME`: The name of the database.
- `DB_HOST`: The hostname or IP address of the database server.
- `DB_PORT`: The port number for the database server (default for PostgreSQL is 5432).

**Command-line Argument:**

- Append the path to the specific job YAML file (located within the `etl/jobs/` directory in the container) to the `docker run` command.

**Example `docker run` command:**

```sh
docker run --rm \
  -e DB_USER=your_db_user \
  -e DB_PASS=your_db_password \
  -e DB_NAME=your_db_name \
  -e DB_HOST=your_db_host \
  -e DB_PORT=5432 \
  as-stats-etl etl/jobs/load_asns_report_May25.yaml
```

Replace `your_db_user`, `your_db_password`, `your_db_name`, and `your_db_host` with your actual database credentials and host. The `--rm` flag automatically removes the container when it exits.

## Running with Docker Compose

This project uses Docker Compose to manage the ETL and PostgreSQL services.

### Prerequisites

- Docker Engine
- Docker Compose

### Setup

1. **Environment Variables:**

    Create a `.env` file in the root of the project. This file will store the credentials for the PostgreSQL database and any other sensitive configuration. Add the following content to it, replacing the placeholder values with your desired credentials:

    ```env
    POSTGRES_USER=your_username
    POSTGRES_PASSWORD=your_strong_password
    POSTGRES_DB=as_stats_db
    ```

    The `docker-compose.yml` file is configured to use these variables. If `.env` is not present, it will use default values (`user`, `password`, `as_stats_db`).

2. **Build and Run:**

    To build the images and start the services, run the following command from the project root:

    ```sh
    docker-compose up --build
    ```

    - `--build`: Forces Docker to rebuild the images if there are any changes to the Dockerfiles or build contexts.
    - `-d`: (Optional) Add `-d` to run the containers in detached mode: `docker-compose up --build -d`

3. **Accessing Services:**

    - **PostgreSQL:** If you keep the default port mapping in `docker-compose.yml`, the PostgreSQL database will be accessible on `localhost:5432`.
    - **ETL Service:** The ETL service will start and connect to the PostgreSQL database as defined. Check its logs to see its activity:

      ```sh
      docker-compose logs -f etl
      ```

4. **Stopping Services:**

    To stop the services, press `Ctrl+C` in the terminal where `docker-compose up` is running, or run:

    ```sh
    docker-compose down
    ```

    If you want to remove the volumes (including PostgreSQL data), use:

    ```sh
    docker-compose down -v
    ```

### ETL Job Execution

The ETL service is configured to run `etl/jobs/load_asns_report_May25.yaml` by default. To run a different job, you can override the command:

```sh
docker-compose run etl etl/jobs/your_job.yaml
```

Or modify the `command` in the `docker-compose.yml` for the `etl` service.
