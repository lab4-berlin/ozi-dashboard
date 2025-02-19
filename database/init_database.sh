echo "WARNING: this script will drop asn_stats database and re-create it. Type 'confirm' to proceed..."
read user_input

if [ "$user_input" == "confirm" ]; then
    echo "Let's rock!"
else
    echo "Not today..."
    exit
fi

source config.sh

echo "Please choose the database passsword ($DBUSER user)"
read -s DBPASSWORD

echo 'Creating the use and database...'
psql --host=$DBHOST --username=postgres postgres -c "DROP DATABASE IF EXISTS $DBNAME;"
psql --host=$DBHOST --username=postgres postgres -c "CREATE DATABASE $DBNAME;"
psql --host=$DBHOST --username=postgres $DBNAME  -c "CREATE USER $DBUSER WITH PASSWORD '$DBPASSWORD';"
psql --host=$DBHOST --username=postgres $DBNAME  -c "GRANT ALL PRIVILEGES ON DATABASE $DBNAME TO $DBUSER;"

export PGPASSWORD=$DBPASSWORD
echo 'Creating the database schema...'
psql --host=$DBHOST --username=$DBUSER $DBNAME -f create_database_schema.sql
psql --host=$DBHOST --username=$DBUSER $DBNAME -f insert_countries.sql
