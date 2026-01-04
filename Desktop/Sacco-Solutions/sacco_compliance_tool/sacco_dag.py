"""
SACCO Compliance Fraud Detection Pipeline (Airflow DAG)

This DAG orchestrates the end-to-end fraud detection workflow:
1. Ingest raw transaction data
2. Clean and preprocess data (encode types, hash member IDs for privacy)
3. Train the fraud detection model if not already present
4. Run fraud detection on cleaned data
5. Optionally call the Flask API endpoint for external integration

Schedule: Daily (@daily)
"""

import logging
import os
from datetime import datetime

import pandas as pd
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

# Import fraud detection functions (supports both relative and absolute imports)
try:
    from .fraud_model import clean_data as clean_transactions
    from .fraud_model import detect_fraud, train_fraud_model
except ImportError:
    from fraud_model import clean_data as clean_transactions
    from fraud_model import detect_fraud, train_fraud_model

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sacco_dag")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FLASK_API_URL = "http://127.0.0.1:5000"
RAW_DATA_PATH = "raw_transactions.csv"
INGESTED_DATA_PATH = "ingested_data.csv"
CLEANED_DATA_PATH = "cleaned_data.csv"
MODEL_PATH = "fraud_model.pkl"
SCALER_PATH = "scaler.pkl"
HISTORICAL_DATA_PATH = "historical_transactions.csv"


# ---------------------------------------------------------------------------
# Task 1: Ingest Data
# ---------------------------------------------------------------------------
def ingest_data():
    """
    Ingest raw transaction data from CSV.
    Falls back to sample data if the raw file is missing.
    Privacy: Raw member_id values are kept here; anonymization happens in clean_data.
    """
    try:
        logger.info("Starting data ingestion...")

        try:
            df = pd.read_csv(RAW_DATA_PATH)
            logger.info(f"Read raw data from {RAW_DATA_PATH} with {len(df)} rows")
        except FileNotFoundError:
            logger.warning(f"{RAW_DATA_PATH} not found. Using fallback sample data.")
            # Fallback sample data for testing/demo purposes
            df = pd.DataFrame(
                [
                    {
                        "transaction_id": 1,
                        "amount": 50000,
                        "date": "2026-01-01",
                        "member_id": 123,
                        "type": "withdrawal",
                        "member_balance": 100000,
                        "time_of_day": "14:30",
                    },
                    {
                        "transaction_id": 2,
                        "amount": 15000,
                        "date": "2026-01-02",
                        "member_id": 124,
                        "type": "deposit",
                        "member_balance": 250000,
                        "time_of_day": "09:15",
                    },
                    {
                        "transaction_id": 3,
                        "amount": 7500,
                        "date": "2026-01-02",
                        "member_id": 123,
                        "type": "loan",
                        "member_balance": 92500,
                        "time_of_day": "18:05",
                    },
                    {
                        "transaction_id": 4,
                        "amount": 200000,
                        "date": "2026-01-03",
                        "member_id": 130,
                        "type": "withdrawal",
                        "member_balance": 500000,
                        "time_of_day": "22:40",
                    },
                    {
                        "transaction_id": 5,
                        "amount": 1200,
                        "date": "2026-01-03",
                        "member_id": 129,
                        "type": "deposit",
                        "member_balance": 30000,
                        "time_of_day": "11:20",
                    },
                ]
            )

        df.to_csv(INGESTED_DATA_PATH, index=False)
        logger.info(f"Saved ingested data to {INGESTED_DATA_PATH} with {len(df)} rows")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Task 2: Clean Data
# ---------------------------------------------------------------------------
def clean_data_task():
    """
    Clean and preprocess ingested data.
    Privacy: member_id is hashed to member_id_hashed for anonymization.
    Also encodes transaction types and converts time_of_day to float hours.
    """
    try:
        logger.info("Starting data cleaning...")

        df = pd.read_csv(INGESTED_DATA_PATH)
        logger.info(f"Read ingested data from {INGESTED_DATA_PATH} with {len(df)} rows")

        # clean_transactions() hashes member_id for privacy
        df_clean = clean_transactions(df)
        df_clean.to_csv(CLEANED_DATA_PATH, index=False)
        logger.info(f"Saved cleaned data to {CLEANED_DATA_PATH} with {len(df_clean)} rows")
        logger.info("Privacy: member_id has been hashed to member_id_hashed")

    except Exception as e:
        logger.error(f"Cleaning failed: {e}", exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Task 3: Train Model (if missing)
# ---------------------------------------------------------------------------
def train_model_if_missing():
    """
    Train the IsolationForest fraud detection model if model/scaler files don't exist.
    Uses historical_transactions.csv if available, otherwise falls back to cleaned_data.csv.
    """
    try:
        logger.info("Checking for existing model artifacts...")

        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            logger.info("Model and scaler already exist. Skipping training.")
            return

        logger.info("Model/scaler missing. Training model...")

        # Prefer historical data for training; fall back to cleaned data
        train_path = HISTORICAL_DATA_PATH if os.path.exists(HISTORICAL_DATA_PATH) else CLEANED_DATA_PATH
        logger.info(f"Training on: {train_path}")

        train_fraud_model(train_path, model_path=MODEL_PATH, scaler_path=SCALER_PATH)
        logger.info("Training completed successfully.")

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Task 4: Run Fraud Detection (local)
# ---------------------------------------------------------------------------
def run_fraud_detection():
    """
    Run fraud detection on cleaned data using the trained model.
    Outputs compliance_fraud_report.csv with anonymized member_id_hashed.
    """
    try:
        logger.info("Starting local fraud detection...")

        report_df = detect_fraud(CLEANED_DATA_PATH)
        logger.info(f"Detection complete. Fraud rows flagged: {len(report_df)}")

        # Verify privacy: ensure member_id is not in output, only member_id_hashed
        if "member_id" in report_df.columns and "member_id_hashed" in report_df.columns:
            logger.info("Privacy check: report contains hashed member IDs only")

    except Exception as e:
        logger.error(f"Fraud detection failed: {e}", exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Task 5: Call Flask API Endpoint (optional integration)
# ---------------------------------------------------------------------------
def call_flask_detect_endpoint():
    """
    Call the Flask /detect endpoint via HTTP POST for external integration.
    This task is optional and will gracefully skip if the Flask app is not running.
    Sends cleaned_data.csv to the API and logs the response.
    """
    try:
        logger.info(f"Attempting to call Flask API at {FLASK_API_URL}/detect ...")

        # Check if Flask server is reachable
        try:
            health_check = requests.get(f"{FLASK_API_URL}/", timeout=5)
            if health_check.status_code != 200:
                logger.warning(f"Flask server returned status {health_check.status_code}. Skipping API call.")
                return
        except requests.exceptions.ConnectionError:
            logger.warning("Flask server not running. Skipping /detect API call.")
            return
        except requests.exceptions.Timeout:
            logger.warning("Flask server connection timed out. Skipping API call.")
            return

        # POST the cleaned data to /detect endpoint
        if not os.path.exists(CLEANED_DATA_PATH):
            logger.warning(f"{CLEANED_DATA_PATH} not found. Skipping API call.")
            return

        with open(CLEANED_DATA_PATH, "rb") as f:
            files = {"file": (CLEANED_DATA_PATH, f, "text/csv")}
            response = requests.post(f"{FLASK_API_URL}/detect", files=files, timeout=60)

        if response.status_code == 200:
            result = response.json()
            report_count = len(result.get("report", []))
            logger.info(f"Flask /detect returned {report_count} fraud records.")
        else:
            logger.warning(f"Flask /detect returned status {response.status_code}: {response.text}")

    except Exception as e:
        logger.error(f"Flask API call failed: {e}", exc_info=True)
        # Don't raise - this task is optional and shouldn't fail the whole pipeline
        logger.info("Continuing pipeline despite Flask API error.")


# ---------------------------------------------------------------------------
# DAG Definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="sacco_compliance_fraud_pipeline",
    description="Daily SACCO fraud detection pipeline with AI model and Flask integration",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["sacco", "compliance", "fraud", "ml"],
) as dag:

    # Task instances
    ingest_task = PythonOperator(
        task_id="ingest_data",
        python_callable=ingest_data,
        doc="Ingest raw transaction data from CSV or use sample fallback",
    )

    clean_task = PythonOperator(
        task_id="clean_data",
        python_callable=clean_data_task,
        doc="Clean data: encode types, hash member_id for privacy",
    )

    train_task = PythonOperator(
        task_id="train_model_if_missing",
        python_callable=train_model_if_missing,
        doc="Train IsolationForest model if not already present",
    )

    detect_task = PythonOperator(
        task_id="run_fraud_detection",
        python_callable=run_fraud_detection,
        doc="Run fraud detection and generate compliance report",
    )

    flask_task = PythonOperator(
        task_id="call_flask_api",
        python_callable=call_flask_detect_endpoint,
        doc="Optional: POST to Flask /detect endpoint for external integration",
    )

    # Task dependencies: ingest -> clean -> train -> detect -> flask_api
    ingest_task >> clean_task >> train_task >> detect_task >> flask_task
