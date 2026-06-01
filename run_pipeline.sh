#!/bin/bash

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="pipeline_$(date '+%Y%m%d').log"

echo "$TIMESTAMP | Starting ETL pipeline" >> $LOG_FILE

cd "/c/DevOps/stock_etl_pipeline"
source .venv/Scripts/activate 2>/dev/null

# Run normally - will ask for ticker input
python fetch_and_load.py
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$TIMESTAMP | SUCCESS | Pipeline completed" >> $LOG_FILE
else
    echo "$TIMESTAMP | FAILED | Exit code: $EXIT_CODE" >> $LOG_FILE
fi