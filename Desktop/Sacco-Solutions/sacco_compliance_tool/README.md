# SACCO Compliance Tool

AI-powered fraud detection system for SACCO (Savings and Credit Cooperative) transaction monitoring.

## Features

- **Fraud Detection Model**: IsolationForest-based anomaly detection
- **Airflow DAG**: Automated daily pipeline for ingestion, cleaning, training, and detection
- **Flask Dashboard**: REST API and HTML dashboard for manual uploads and viewing reports
- **ACE Framework**: Simulated Generator/Reflector/Curator loop for adaptive playbook updates
- **Privacy**: All `member_id` values are hashed before processing and reporting

## Quick Start

### 1. Set Up Environment

```bash
# Create and activate virtual environment
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux/macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Flask Dashboard

```bash
# Start the Flask server (runs on http://127.0.0.1:5000)
python app.py
```

**API Endpoints:**
- `GET /` – Welcome message
- `POST /train` – Upload CSV to train model
- `POST /detect` – Upload CSV to run fraud detection
- `GET /dashboard` – View HTML fraud report table

### 3. Run Airflow Pipeline

```bash
# Initialize Airflow database (first time only)
airflow db init

# Start scheduler (in one terminal)
airflow scheduler

# Start webserver (in another terminal)
airflow webserver --port 8080
```

Access Airflow UI at: http://localhost:8080

**DAG**: `sacco_compliance_fraud_pipeline` (runs daily)

**Tasks:**
1. `ingest_data` – Load raw transactions
2. `clean_data` – Preprocess and anonymize member IDs
3. `train_model_if_missing` – Train IsolationForest if needed
4. `run_fraud_detection` – Generate compliance report
5. `call_flask_api` – Optional POST to Flask /detect endpoint

### 4. Run Tests

```bash
python -m pytest tests.py -v
```

## Project Structure

```
sacco_compliance_tool/
├── app.py                  # Flask web dashboard
├── fraud_model.py          # ML model (train/detect)
├── sacco_dag.py            # Airflow DAG definition
├── ace_integration.py      # Simulated ACE framework
├── tests.py                # Pytest unit tests
├── requirements.txt        # Python dependencies
├── historical_transactions.csv  # Sample training data
├── new_transactions.csv         # Sample test data
└── README.md
```

## Output Files

- `fraud_model.pkl` – Trained IsolationForest model
- `scaler.pkl` – Fitted StandardScaler
- `compliance_fraud_report.csv` – Flagged fraud transactions
- `playbook.json` – ACE framework rules and insights

## Privacy

All reports use `member_id_hashed` instead of raw `member_id` to ensure member anonymity.
