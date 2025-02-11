# ozi-dashboard

1. Create Postgres instance on GCP, name it `asn-stats`
2. Use strong password for user `postgres` while creating DB
3. Go to `asn-stats`'s console
4. Download code by cloning Git Repository
```
  git clone https://github.com/ilja-vladi/as-stats.git
```
5. Create database, user and tables for asn_stats project
  - when asked for password use postgres password from step 2 first
  - and asn_data password for the second sql script

```
  cd as-stats
  ./init_database.sh
  
```
## TMP
```
cat sql/*.sql | gcloud sql connect asn-stats2 --user=asn_stats
```

## Dagster
```
sudo apt install python3-pip
sudo apt install python3.12-venv
python3 -m venv dagster_env
source dagster_env/bin/activate
pip install dagster dagster-webserver dagster-postgres
dagster project scaffold --name=dagster_etl
```
