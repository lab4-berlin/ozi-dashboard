# ozi-dashboard

1. Create Postgres Database (anywhere - locally or in the cloud)
2. Use strong password for user `postgres` while creating DB
3. Go to your ETL instance
4. Download code by cloning Git Repository
```
  git clone https://github.com/lab4-berlin/ozi-dashboard.git
```
5. Create database, user and tables 
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
