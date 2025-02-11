# ozi-dashboard

## Setup database
- Get Postgres server (anywhere - locally or in the cloud), you will need it's hostnamem and password for the user postgres
- Go to your ETL instance (any Unix machine with access to the Postgres Database)
- Download code by cloning Git Repository
```bash
  git clone https://github.com/lab4-berlin/ozi-dashboard.git
```
- Create database, user and tables 
```bash
  cd ozi-dashboard
  ./init_database.sh
```

## Secrets
```bash
create file .env in ozi-dashboard
assure that it is added to .gitignore and does net end up in your repository

.env content:
------------------------------------
DB_NAME=my_database
DB_USER=my_user
DB_PASSWORD=my_secure_password
DB_HOST=ip-or-url
DB_PORT=5432
------------------------------------
```

## Dagster
```bash
sudo apt install python3-pip
sudo apt install python3.12-venv
python3 -m venv dagster_env
source dagster_env/bin/activate
pip install dagster dagster-webserver dagster-postgres
dagster project scaffold --name=dagster_etl

dagster dev --host 0.0.0.0 --port 3000
```
