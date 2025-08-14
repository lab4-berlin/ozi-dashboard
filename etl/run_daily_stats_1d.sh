#!/bin/bash

# Script to run daily STATS_1D ETL job
# This script should be run inside the ozi-etl container

echo "[$(date)] Starting daily STATS_1D ETL job"

# Get the date range for the ETL job
DATE_RANGE_OUTPUT=$(python3 /app/etl/get_stats_1d_date_range.py)
DATE_RANGE=$(echo "$DATE_RANGE_OUTPUT" | grep -v "^#" | tr -d '\n')

# Check if there's anything to do
if [[ $DATE_RANGE_OUTPUT == *"Nothing to do"* ]]; then
    echo "[$(date)] $DATE_RANGE_OUTPUT"
    exit 0
fi

echo "[$(date)] $DATE_RANGE_OUTPUT"

# Run the ETL job for one country for testing
echo "[$(date)] Running ETL job with parameters: $DATE_RANGE"
python3 /app/etl/main.py -t STATS_1D -c CZ $DATE_RANGE -dr D

if [ $? -eq 0 ]; then
    echo "[$(date)] Daily STATS_1D ETL job completed successfully"
else
    echo "[$(date)] Daily STATS_1D ETL job failed"
    exit 1
fi