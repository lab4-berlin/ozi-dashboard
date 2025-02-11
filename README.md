# ozi-dashboard

## Setup database
- Get Postgres server (anywhere - locally or in the cloud), you will need it's hostnamem and password for the user postgres
- Go to your ETL instance (any Unix machine with access to the Postgres Database)
- Download code by cloning Git Repository
```
  git clone https://github.com/lab4-berlin/ozi-dashboard.git
```
- Create database, user and tables 
```
  cd ozi-dashboard
  ./init_database.sh
```

## Dagster
```
sudo apt install python3-pip
sudo apt install python3.12-venv
python3 -m venv dagster_env
source dagster_env/bin/activate
pip install dagster dagster-webserver dagster-postgres
dagster project scaffold --name=dagster_etl

dagster dev --host 0.0.0.0 --port 3000
```
