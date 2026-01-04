
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

try:
    from .ace_integration import Curator, Generator, Reflector, load_playbook, save_playbook
except ImportError:
    from ace_integration import Curator, Generator, Reflector, load_playbook, save_playbook


TYPE_ENCODING = {"withdrawal": 0, "deposit": 1, "loan": 2}


def _time_of_day_to_float_hours(time_of_day: pd.Series) -> pd.Series:
    def _parse(value):
        if pd.isna(value):
            return pd.NA

        if isinstance(value, (int, float)):
            return float(value)

        value_str = str(value).strip()
        if not value_str:
            return pd.NA

        parts = value_str.split(":")
        if len(parts) < 2:
            try:
                return float(value_str)
            except ValueError:
                raise ValueError(f"Invalid time_of_day format: {value_str}")

        try:
            hours = float(parts[0])
            minutes = float(parts[1])
        except ValueError as e:
            raise ValueError(f"Invalid time_of_day format: {value_str}") from e

        return hours + (minutes / 60.0)

    return time_of_day.apply(_parse).astype("float64")


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["member_id_hashed"] = df.get("member_id").apply(lambda x: hash(str(x)))

    df["transaction_type_encoded"] = (
        df.get("type")
        .astype("string")
        .str.lower()
        .map(TYPE_ENCODING)
        .astype("float64")
    )

    df = df.dropna(subset=["amount"])
    df["time_of_day"] = _time_of_day_to_float_hours(df.get("time_of_day"))

    return df


def _prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()

    features = ["amount", "transaction_type_encoded", "member_balance", "time_of_day"]
    X = df.loc[:, features].copy()

    X = X.fillna(X.median(numeric_only=True)).fillna(0.0)

    return df, X


def train_fraud_model(
    data_path: str,
    model_path: str = "fraud_model.pkl",
    scaler_path: str = "scaler.pkl",
):
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"File not found: {data_path}")
        return

    try:
        df = clean_data(df)
    except ValueError as e:
        print(str(e))
        return

    df, X = _prepare_features(df)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(contamination=0.01, random_state=42)
    model.fit(X_scaled)

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)


def detect_fraud(
    new_data_path: str,
    model_path: str = "fraud_model.pkl",
    scaler_path: str = "scaler.pkl",
):
    try:
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
    except FileNotFoundError as e:
        print(str(e))
        raise

    try:
        df = pd.read_csv(new_data_path)
    except FileNotFoundError:
        print(f"File not found: {new_data_path}")
        raise

    try:
        df = clean_data(df)
    except ValueError as e:
        print(str(e))
        raise

    df_prepared, X = _prepare_features(df)
    X_scaled = scaler.transform(X)

    preds = model.predict(X_scaled)
    fraud_score = model.decision_function(X_scaled)

    df_prepared["fraud_score"] = fraud_score
    df_prepared["is_fraud"] = preds == -1
    df_prepared["compliance_flag"] = "Normal"
    df_prepared.loc[df_prepared["fraud_score"] < -0.5, "compliance_flag"] = "High Risk"

    report_df = df_prepared.loc[df_prepared["is_fraud"]].copy()

    # Privacy: Remove raw member_id from report, keep only hashed version
    if "member_id" in report_df.columns:
        report_df = report_df.drop(columns=["member_id"])

    try:
        playbook = load_playbook("playbook.json")
        generator = Generator()
        reflector = Reflector()
        curator = Curator()

        for _, row in report_df.iterrows():
            query = (
                f"transaction_id={row.get('transaction_id')}, amount={row.get('amount')}, "
                f"type={row.get('type')}, time_of_day={row.get('time_of_day')}, "
                f"member_id_hashed={row.get('member_id_hashed')}"
            )

            response = generator.generate(query=query, playbook=playbook)
            ground_truth = {
                "expected": "Detected fraud",
                "label": "true_positive" if row.get("fraud_score", 0) < -0.5 else "false_positive",
            }
            insights = reflector.reflect(response=response, ground_truth=ground_truth)
            playbook = curator.curate(playbook=playbook, insights=insights)

        save_playbook(playbook, "playbook.json")
    except Exception as e:
        print(f"[ACE] Skipping ACE integration due to error: {e}")

    report_df.to_csv("compliance_fraud_report.csv", index=False)
    return report_df


if __name__ == "__main__":
    train_fraud_model("historical_transactions.csv")
    report = detect_fraud("new_transactions.csv")
    print(report.head())
