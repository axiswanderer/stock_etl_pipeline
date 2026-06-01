import yfinance as yf
import pandas as pd
import sqlalchemy
from sqlalchemy import text
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(filename='etl.log', level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(message)s')

load_dotenv()


# Extract
def extract_data(ticker):
    try:
        logging.info(f"Fetching data for {ticker}")
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo")

        if df.empty:
            raise Exception("No data returned from API")

        logging.info(f"Extracted {len(df)} rows")
        # print (df.head())
        return df
    except Exception as e:
        logging.error(f"Extract failed: {e}")
        raise


# Transform
def transform_data(df, ticker):
    df = df.reset_index()
    df['ticker'] = ticker
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df[['date', 'ticker', 'open', 'high', 'low', 'close', 'volume']]
    df['date'] = pd.to_datetime(df['date']).dt.date
    df['daily_return_pct'] = df['close'].pct_change() * 100
    df['ma_7'] = df['close'].rolling(7).mean()
    df['volatility_20d'] = df['daily_return_pct'].rolling(20).std()
    df = df.dropna(subset=['daily_return_pct', 'ma_7', 'volatility_20d'], how='all')
    logging.info(f"Transformed {len(df)} rows")
    print("\n\n\n")
    # print(df.head())
    return df


# Load (Upsert)
def load_data(df):
    try:
        engine = sqlalchemy.create_engine(
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )

        # Drop previous table (Clean data)
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS stock_prices"))
            conn.commit()

        # Create table (Fresh)
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS stock_prices (
                    date DATE,
                    ticker VARCHAR(10),
                    open FLOAT,
                    high FLOAT,
                    low FLOAT,
                    close FLOAT,
                    volume BIGINT,
                    daily_return_pct FLOAT,
                    ma_7 FLOAT,
                    volatility_20d FLOAT,
                    PRIMARY KEY (ticker, date)
                )
            """))
            conn.commit()

        # Upsert
        for _, row in df.iterrows():
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO stock_prices 
                    (date, ticker, open, high, low, close, volume, 
                     daily_return_pct, ma_7, volatility_20d)
                    VALUES (:date, :ticker, :open, :high, :low, :close, :volume,
                            :daily_return_pct, :ma_7, :volatility_20d)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        daily_return_pct = EXCLUDED.daily_return_pct,
                        ma_7 = EXCLUDED.ma_7,
                        volatility_20d = EXCLUDED.volatility_20d
                """), row.to_dict())
                conn.commit()

        # Data quality check
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM stock_prices"))
            count = result.scalar()
            assert count > 0, "No rows in table"

            result = conn.execute(text("SELECT MIN(close) FROM stock_prices"))
            min_close = result.scalar()
            assert min_close > 0, f"Invalid close price: {min_close}"

        logging.info(f"Loaded {len(df)} rows. Total records: {count}")
        engine.dispose()
        return count
    except Exception as e:
        logging.error(f"Load failed: {e}")
        raise


# Generate SQL report
def generate_report():
    engine = sqlalchemy.create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )

    queries = {
        "top_5_volume_days": """
            SELECT date, ticker, volume, close
            FROM stock_prices
            ORDER BY volume DESC
            LIMIT 5
        """,
        "avg_daily_return_by_month": """
            SELECT ticker, 
                   DATE_TRUNC('month', date) as month,
                   AVG(daily_return_pct) as avg_return
            FROM stock_prices
            GROUP BY ticker, DATE_TRUNC('month', date)
            ORDER BY month DESC
        """,
        "max_drawdown": """
            WITH max_so_far AS (
                SELECT ticker, date, close,
                       MAX(close) OVER (PARTITION BY ticker ORDER BY date) as peak
                FROM stock_prices
            )
            SELECT ticker, 
                   MAX((peak - close) / peak * 100) as max_drawdown_pct
            FROM max_so_far
            GROUP BY ticker
        """
    }

    for name, query in queries.items():
        df_report = pd.read_sql(query, engine)
        df_report.to_csv(f"{name}.csv", mode ='w', index=False)
        logging.info(f"Report saved: {name}.csv ({len(df_report)} rows)")

    engine.dispose()


if __name__ == "__main__":
    try:
        ticker = input("Enter ticker: ")
        df_raw = extract_data(ticker)
        df_clean = transform_data(df_raw, ticker)
        row_count = load_data(df_clean)
        generate_report()
        logging.info(f"Pipeline SUCCESS - {row_count} rows affected")
        print(f"SUCCESS: {row_count} rows loaded")
    except Exception as e:
        logging.error(f"Pipeline FAILED: {e}")
        print(f"FAILED: {e}")
        exit(1)