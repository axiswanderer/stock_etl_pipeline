```markdown
# Automated Stock Market ETL Pipeline

A production-ready ETL pipeline that fetches stock and cryptocurrency data from Yahoo Finance, transforms it with financial indicators, and stores it in a PostgreSQL database. Includes automated reporting and bash scripting for scheduled execution.

## Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Pipeline Components](#pipeline-components)
- [Database Schema](#database-schema)
- [Reports Generated](#reports-generated)
- [Automation](#automation)
- [Troubleshooting](#troubleshooting)
- [Future Improvements](#future-improvements)

## Project Overview

This project implements an automated ETL (Extract, Transform, Load) pipeline for financial market data. It extracts daily OHLCV (Open, High, Low, Close, Volume) data for any stock or cryptocurrency ticker, calculates technical indicators, stores the results in a relational database, and generates analytical reports. The entire pipeline can be automated using bash scripts and cron jobs.

This is the type of data engineering pattern used at investment banks like Morgan Stanley for market data processing, risk management, and quantitative research.

## Tech Stack

- Python 3.x
- PostgreSQL (or SQLite for local development)
- Pandas for data transformation
- yfinance for market data API
- SQLAlchemy for database ORM
- Bash for orchestration
- Cron for scheduling (Linux/Mac) or Task Scheduler (Windows)

## Features

- Extract real-time and historical market data from Yahoo Finance
- Support for stocks, ETFs, and cryptocurrencies
- Transform raw data into analyzable format
- Calculate financial metrics:
  - Daily percentage returns
  - 7-day moving average
  - 20-day rolling volatility
- Upsert logic to prevent duplicate records
- Data quality validation
- Automated CSV report generation
- Comprehensive logging
- Bash script for one-click execution
- Configurable for scheduled runs

## Architecture

The pipeline follows a linear ETL flow:

Extract -> Transform -> Load -> Report -> Automate

Extract Phase: Fetches raw OHLCV data from yfinance API for the specified ticker covering the last 30 days.

Transform Phase: Converts data types, renames columns to snake_case, calculates derived financial metrics, and handles null values.

Load Phase: Establishes connection to PostgreSQL, creates table structure if not exists, and performs upsert operations to avoid duplicates while updating existing records.

Report Phase: Executes SQL queries against the loaded data and exports results to CSV files.

Automation Phase: Bash script orchestrates the entire process with logging and error handling, scheduled via cron.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher (or SQLite as alternative)
- Git
- Bash shell (Git Bash on Windows, native on Linux/Mac)

## Installation

1. Clone the repository

```bash
git clone https://github.com/yourusername/stock-etl-pipeline.git
cd stock-etl-pipeline
```

2. Create and activate virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
source .venv/Scripts/activate   # Windows Git Bash
.venv\Scripts\activate          # Windows CMD
```

3. Install dependencies

```bash
pip install yfinance pandas sqlalchemy psycopg2-binary python-dotenv
```

4. Install and setup PostgreSQL

Ubuntu/Debian:
```bash
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql
```

Windows: Download from https://www.postgresql.org/download/windows/

5. Create database and user

```sql
CREATE DATABASE stock_db;
CREATE USER youruser WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE stock_db TO youruser;
\q
```

## Configuration

Create a `.env` file in the project root directory:

```env
DB_NAME=stock_db
DB_USER=youruser
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
```

For SQLite alternative, modify the connection string in the Python script:

```python
engine = sqlalchemy.create_engine('sqlite:///stock_data.db')
```

## Usage

### Manual Run

Run the pipeline for a single ticker:

```bash
python fetch_and_load.py
```

You will be prompted to enter a ticker symbol (e.g., AAPL, MSFT, BTC-USD).

### Automated Run with Bash Script

```bash
chmod +x run_pipeline.sh
./run_pipeline.sh
```

### Process Multiple Tickers

Modify the bash script to loop through tickers:

```bash
TICKERS=("AAPL" "MSFT" "GOOGL" "TSLA" "BTC-USD")
for ticker in "${TICKERS[@]}"; do
    echo "Processing $ticker"
    python -c "import fetch_and_load; fetch_and_load.main('$ticker')"
done
```

## Pipeline Components

### Extract

The extract_data function fetches data from Yahoo Finance using the yfinance library. It requests 30 days of historical data including open, high, low, close, and volume. Error handling captures API failures and network issues.

### Transform

The transform_data function performs several operations:
- Resets the index to make date a column
- Renames columns to snake_case for database compatibility
- Converts date to proper datetime format
- Calculates daily return percentage using pct_change()
- Computes 7-day simple moving average
- Computes 20-day rolling volatility as standard deviation of returns
- Drops rows where all calculated fields are null

### Load

The load_data function handles database operations:
- Creates a connection using SQLAlchemy
- Drops existing table for clean state (configurable)
- Creates fresh table with primary key on (ticker, date)
- Performs upsert using INSERT ON CONFLICT DO UPDATE
- Validates data quality with row count and price checks
- Logs total records after load

### Reports

The generate_report function creates three CSV outputs:
- top_5_volume_days.csv: Highest volume trading days
- avg_daily_return_by_month.csv: Monthly average returns by ticker
- max_drawdown.csv: Maximum peak-to-trough decline for each ticker

## Database Schema

Table: stock_prices

| Column | Type | Description |
|--------|------|-------------|
| date | DATE | Trading date |
| ticker | VARCHAR(10) | Stock or crypto symbol |
| open | FLOAT | Opening price |
| high | FLOAT | Daily high price |
| low | FLOAT | Daily low price |
| close | FLOAT | Closing price |
| volume | BIGINT | Trading volume |
| daily_return_pct | FLOAT | Percentage change from previous close |
| ma_7 | FLOAT | 7-day moving average of close |
| volatility_20d | FLOAT | 20-day standard deviation of returns |

Primary Key: (ticker, date)

## Reports Generated

After each successful pipeline run, the following files are created:

top_5_volume_days.csv
Contains the five trading days with highest volume across all loaded tickers. Useful for identifying unusual market activity.

avg_daily_return_by_month.csv
Shows average daily return percentage grouped by ticker and calendar month. Enables performance comparison across time periods.

max_drawdown.csv
Calculates the maximum percentage decline from a historical peak for each ticker. Critical metric for risk assessment.

## Automation

### Bash Script (run_pipeline.sh)

The bash script orchestrates the entire pipeline with the following features:
- Timestamped logging to pipeline_YYYYMMDD.log
- Virtual environment activation
- Error code capture and handling
- Success/failure status logging

To make the script executable:

```bash
chmod +x run_pipeline.sh
```

### Cron Scheduling (Linux/Mac)

To run the pipeline every weekday at 9 AM:

```bash
crontab -e
```

Add the following line:

```bash
0 9 * * 1-5 /path/to/stock_etl_pipeline/run_pipeline.sh
```

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to daily at 9 AM
4. Set action to start program: C:\path\to\stock_etl_pipeline\run_pipeline.bat

### Logging

Two log files are maintained:
- etl.log: Detailed Python logging with timestamps and status messages
- pipeline_YYYYMMDD.log: Bash script execution logs with start/end times and exit codes

## Troubleshooting

Common Issues and Solutions

Module not found errors

Activate the virtual environment and verify installation:
```bash
source .venv/Scripts/activate
pip list | grep yfinance
```

PostgreSQL connection refused

Ensure PostgreSQL service is running:
```bash
sudo systemctl status postgresql    # Linux
Get-Service postgresql              # Windows PowerShell
```

No data extracted

Check internet connection and ticker symbol validity. Test with known tickers like AAPL or MSFT.

Primary key violation

The ON CONFLICT clause handles duplicates automatically. If errors persist, check that date and ticker are properly formatted.

CSV files not updating

Verify write permissions in the project directory. The script uses mode='w' which overwrites existing files.

## Future Improvements

Add incremental loading with date filtering instead of full table refresh

Implement data quality checks with alerting via email or webhook

Create visualization dashboard using Streamlit or Tableau

Add support for multiple timeframes (1min, 5min, 1hour)

Implement configuration file for ticker lists and schedules

Add unit tests for each pipeline component

Containerize with Docker for consistent deployment

Add Airflow or Prefect for workflow orchestration

Implement retry logic with exponential backoff for API failures

Add support for corporate actions (splits, dividends, stock buybacks)

## License

MIT License

## Author

Muhammad Hanzala Khan (axiswanderer)

```