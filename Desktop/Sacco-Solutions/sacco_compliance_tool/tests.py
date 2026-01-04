
import os
from pathlib import Path

import pandas as pd
import pytest

from fraud_model import *


@pytest.fixture
def sample_transactions_df() -> pd.DataFrame:
    return pd.DataFrame(
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


def test_train(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_transactions_df: pd.DataFrame):
    monkeypatch.chdir(tmp_path)

    data_path = tmp_path / "train.csv"
    sample_transactions_df.to_csv(data_path, index=False)

    model_path = "fraud_model.pkl"
    scaler_path = "scaler.pkl"

    train_fraud_model(str(data_path), model_path=model_path, scaler_path=scaler_path)

    assert os.path.exists(model_path)
    assert os.path.exists(scaler_path)


def test_detect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_transactions_df: pd.DataFrame):
    monkeypatch.chdir(tmp_path)

    train_path = tmp_path / "train.csv"
    detect_path = tmp_path / "new.csv"
    sample_transactions_df.to_csv(train_path, index=False)
    sample_transactions_df.to_csv(detect_path, index=False)

    train_fraud_model(str(train_path), model_path="fraud_model.pkl", scaler_path="scaler.pkl")
    report_df = detect_fraud(str(detect_path), model_path="fraud_model.pkl", scaler_path="scaler.pkl")

    assert "is_fraud" in report_df.columns
    assert "fraud_score" in report_df.columns
    assert "compliance_flag" in report_df.columns

    if len(report_df) > 0:
        assert report_df["is_fraud"].all()
        assert set(report_df["compliance_flag"].unique()).issubset({"Normal", "High Risk"})


def test_dag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_transactions_df: pd.DataFrame):
    pytest.importorskip("airflow")
    monkeypatch.chdir(tmp_path)

    (tmp_path / "historical_transactions.csv").write_text(
        sample_transactions_df.to_csv(index=False), encoding="utf-8"
    )

    from sacco_dag import clean_data_task, ingest_data, run_fraud_detection, train_model_if_missing

    ingest_data()
    clean_data_task()
    train_model_if_missing()
    run_fraud_detection()

    assert os.path.exists("ingested_data.csv")
    assert os.path.exists("cleaned_data.csv")
    assert os.path.exists("fraud_model.pkl")
    assert os.path.exists("scaler.pkl")
    assert os.path.exists("compliance_fraud_report.csv")
