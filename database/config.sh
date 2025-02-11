export DBUSER=ozi_dashboard
export DBNAME=ozi_dashboard
export DBHOST=ozi-dashboard-db2.cm7ygcoo08e0.us-east-1.rds.amazonaws.com

echo "Please enter the database passsword (user postgres)"
read -s PGPASSWORD
export PGPASSWORD=$PGPASSWORD
