import sys
import os
import argparse
import logging
import pandas as pd
from tqdm import tqdm
from fredapi import Fred
from src.common.config import get_settings
from src.common.database import db_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("creditlens.loader")

class DataLoader:
    """Idempotent batch loader for CreditLens financial, macro and SEC data."""
    
    def __init__(self) -> None:
        self.settings = get_settings()

    def load_fred(self) -> None:
        """Pulls macroeconomic factors from FRED API and stores them in PostgreSQL."""
        if not self.settings.FRED_API_KEY:
            logger.warning("FRED_API_KEY is not defined in settings. Skipping macro-indicators loading.")
            return

        logger.info("Initializing FRED client connection...")
        fred = Fred(api_key=self.settings.FRED_API_KEY)
        
        series_map = {
            "FEDFUNDS": "Effective Federal Funds Rate",
            "UNRATE": "Civilian Unemployment Rate",
            "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
            "GDPC1": "Real Gross Domestic Product"
        }
        
        # Synchronous execution pattern for batch loads
        import psycopg2
        conn = psycopg2.connect(self.settings.POSTGRES_URL)
        cursor = conn.cursor()
        
        try:
            for series_id, name in series_map.items():
                logger.info(f"Downloading macro factor: {name} ({series_id})...")
                df = fred.get_series(series_id)
                if df.empty:
                    continue
                    
                records_inserted = 0
                for date_obs, val in df.items():
                    if pd.isna(val):
                        continue
                    # Idempotent load via UPSERT
                    cursor.execute("""
                        INSERT INTO raw.fred_indicators (series_id, observation_date, value, series_name)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (series_id, observation_date) DO UPDATE 
                        SET value = EXCLUDED.value, loaded_at = NOW();
                    """, (series_id, date_obs.date(), float(val), name))
                    records_inserted += 1
                conn.commit()
                logger.info(f"Loaded {records_inserted} records for {series_id}.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error loading FRED indicators: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    def load_lending_club(self, csv_path: str) -> None:
        """Idempotent chunked loader for massive 2.9M record loans dataset."""
        if not os.path.exists(csv_path):
            logger.error(f"Lending Club CSV file not found at path: {csv_path}")
            return

        logger.info(f"Beginning chunked ingestion of {csv_path}...")
        
        import psycopg2
        conn = psycopg2.connect(self.settings.POSTGRES_URL)
        cursor = conn.cursor()
        
        # Read file in 100k chunks to optimize RAM footprint
        chunksize = 100000
        try:
            for chunk in tqdm(pd.read_csv(csv_path, chunksize=chunksize, low_memory=False)):
                # Keep only valid rows
                chunk = chunk.dropna(subset=["id", "loan_amnt", "issue_d"])
                
                for _, row in chunk.iterrows():
                    # Parse dates helper
                    issue_date = pd.to_datetime(row["issue_d"]).date() if not pd.isna(row["issue_d"]) else None
                    earliest_cr = pd.to_datetime(row["earliest_cr_line"]).date() if not pd.isna(row["earliest_cr_line"]) else None
                    last_pymnt = pd.to_datetime(row["last_pymnt_d"]).date() if not pd.isna(row["last_pymnt_d"]) else None

                    cursor.execute("""
                        INSERT INTO raw.lc_loans (
                            loan_id, member_id, loan_amnt, funded_amnt, term, int_rate, installment,
                            grade, sub_grade, emp_title, emp_length, home_ownership, annual_inc,
                            verification_status, issue_date, loan_status, purpose, title, zip_code,
                            addr_state, dti, delinq_2yrs, earliest_cr_line, inq_last_6mths, open_acc,
                            pub_rec, revol_bal, revol_util, total_acc, total_pymnt, total_rec_prncp,
                            total_rec_int, recoveries, collection_recovery_fee, last_pymnt_date,
                            last_pymnt_amnt, application_type
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (loan_id) DO UPDATE SET
                            loan_status = EXCLUDED.loan_status,
                            total_pymnt = EXCLUDED.total_pymnt,
                            last_pymnt_date = EXCLUDED.last_pymnt_date,
                            loaded_at = NOW();
                    """, (
                        int(row["id"]),
                        int(row["member_id"]) if not pd.isna(row["member_id"]) else None,
                        float(row["loan_amnt"]),
                        float(row["funded_amnt"]) if not pd.isna(row["funded_amnt"]) else None,
                        row["term"],
                        float(row["int_rate"]) if not pd.isna(row["int_rate"]) else None,
                        float(row["installment"]) if not pd.isna(row["installment"]) else None,
                        row["grade"],
                        row["sub_grade"],
                        row["emp_title"] if not pd.isna(row["emp_title"]) else None,
                        row["emp_length"] if not pd.isna(row["emp_length"]) else None,
                        row["home_ownership"],
                        float(row["annual_inc"]) if not pd.isna(row["annual_inc"]) else 0.0,
                        row["verification_status"],
                        issue_date,
                        row["loan_status"],
                        row["purpose"],
                        row["title"] if not pd.isna(row["title"]) else None,
                        row["zip_code"],
                        row["addr_state"],
                        float(row["dti"]) if not pd.isna(row["dti"]) else 0.0,
                        int(row["delinq_2yrs"]) if not pd.isna(row["delinq_2yrs"]) else 0,
                        earliest_cr,
                        int(row["inq_last_6mths"]) if not pd.isna(row["inq_last_6mths"]) else 0,
                        int(row["open_acc"]) if not pd.isna(row["open_acc"]) else 0,
                        int(row["pub_rec"]) if not pd.isna(row["pub_rec"]) else 0,
                        float(row["revol_bal"]) if not pd.isna(row["revol_bal"]) else 0.0,
                        float(row["revol_util"]) if not pd.isna(row["revol_util"]) else 0.0,
                        int(row["total_acc"]) if not pd.isna(row["total_acc"]) else 0,
                        float(row["total_pymnt"]) if not pd.isna(row["total_pymnt"]) else 0.0,
                        float(row["total_rec_prncp"]) if not pd.isna(row["total_rec_prncp"]) else 0.0,
                        float(row["total_rec_int"]) if not pd.isna(row["total_rec_int"]) else 0.0,
                        float(row["recoveries"]) if not pd.isna(row["recoveries"]) else 0.0,
                        float(row["collection_recovery_fee"]) if not pd.isna(row["collection_recovery_fee"]) else 0.0,
                        last_pymnt,
                        float(row["last_pymnt_amnt"]) if not pd.isna(row["last_pymnt_amnt"]) else 0.0,
                        row["application_type"]
                    ))
                conn.commit()
            logger.info("Successfully completed Lending Club ingestion.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failure during chunked loading iteration: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CreditLens Data Ingestion Pipeline")
    parser.add_argument("--source", type=str, required=True, choices=["fred", "lending_club", "all"])
    parser.add_argument("--csv-path", type=str, help="Local file path for Lending Club CSV")
    
    args = parser.parse_args()
    loader = DataLoader()
    
    if args.source == "fred" or args.source == "all":
        loader.load_fred()
    if args.source == "lending_club" or args.source == "all":
        if not args.csv_path:
            logger.error("--csv-path is required when loading Lending Club data!")
            sys.exit(1)
        loader.load_lending_club(args.csv_path)
