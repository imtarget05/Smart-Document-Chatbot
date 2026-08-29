"""Train & register 3 ML models vào MLflow registry.

Chạy:  supply-chain-module/api/.venv/bin/python supply-chain-module/mlops/train_models.py

Models:
  - prophet_forecasting  (Prophet  seasonal, alias challenger)
  - supplier_risk        (LogisticRegression, alias challenger)
  - anomaly_detection    (IsolationForest, alias challenger)

MLflow tracking: sqlite:///supply-chain-module/mlops/mlflow.db
Mlruns:         supply-chain-module/mlruns
"""
import os
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent  # supply-chain-module/
MLFLOW_DB = ROOT / "mlops" / "mlflow.db"
MLRUNS_DIR = ROOT / "mlruns"

# Ensure dirs
MLFLOW_DB.parent.mkdir(parents=True, exist_ok=True)
MLRUNS_DIR.mkdir(parents=True, exist_ok=True)

import mlflow
from mlflow.tracking import MlflowClient

TRACKING_URI = f"sqlite:///{MLFLOW_DB}"
mlflow.set_tracking_uri(TRACKING_URI)
client = MlflowClient()

EXPERIMENT_NAME = "supply_chain"
exp = client.get_experiment_by_name(EXPERIMENT_NAME)
if exp is None:
    exp_id = client.create_experiment(EXPERIMENT_NAME)
else:
    exp_id = exp.experiment_id
mlflow.set_experiment(EXPERIMENT_NAME)

print(f"Tracking: {TRACKING_URI}")
print(f"Experiment: {EXPERIMENT_NAME} ({exp_id})")

# ── 1. Prophet forecasting ──────────────────────────────────────
def train_prophet():
    print("\n=== Prophet forecasting ===")
    from prophet import Prophet

    # Synthetic daily sales: trend + weekly seasonality + noise
    np.random.seed(42)
    n = 365
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    trend = np.linspace(100, 140, n)
    weekly = 10 * np.sin(2 * np.pi * np.arange(n) / 7)
    noise = np.random.normal(0, 5, n)
    y = trend + weekly + noise
    df = pd.DataFrame({"ds": dates, "y": y})

    with mlflow.start_run(run_name="prophet_forecasting"):
        model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=False,
        )
        model.fit(df)
        # Quick eval MAE on last 30 days holdout
        future = model.make_future_dataframe(periods=30)
        forecast = model.predict(future)
        mae = float(np.abs(forecast["yhat"].iloc[-30:].values - (trend[-30:] + weekly[-30:])).mean())
        print(f"  Prophet trained, MAE ~ {mae:.2f}")

        mlflow.prophet.log_model(model, artifact_path="model",
                                  registered_model_name="prophet_forecasting")
        mlflow.log_metric("mae", mae)
        run_id = mlflow.active_run().info.run_id

    # Set alias challenger to latest version
    versions = client.get_latest_versions("prophet_forecasting")
    if versions:
        v = max(versions, key=lambda x: int(x.version))
        client.set_registered_model_alias("prophet_forecasting", "challenger", v.version)
        print(f"  -> prophet_forecasting v{v.version} alias challenger (run {run_id[:8]})")

# ── 2. Supplier risk — LogisticRegression ──────────────────────
def train_supplier_risk():
    print("\n=== Supplier risk (LogisticRegression) ===")
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, roc_auc_score

    np.random.seed(42)
    n = 2000
    X = pd.DataFrame({
        "lead_time_std": np.random.uniform(0, 15, n),
        "defect_rate": np.random.uniform(0, 0.10, n),
        "on_time_rate": np.random.uniform(0.60, 1.0, n),
    })
    # Label: high risk if weighted score > 0.5
    score = X["lead_time_std"] / 15 * 0.3 + X["defect_rate"] / 0.10 * 0.4 + (1 - X["on_time_rate"]) * 0.3
    y = (score > 0.45).astype(int)  # 0=low risk, 1=high risk

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    with mlflow.start_run(run_name="supplier_risk"):
        model = LogisticRegression(max_iter=500)
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
        print(f"  LogisticRegression acc={acc:.3f} auc={auc:.3f}")

        mlflow.sklearn.log_model(model, artifact_path="model",
                                  registered_model_name="supplier_risk")
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("auc", auc)
        run_id = mlflow.active_run().info.run_id

    versions = client.get_latest_versions("supplier_risk")
    if versions:
        v = max(versions, key=lambda x: int(x.version))
        client.set_registered_model_alias("supplier_risk", "challenger", v.version)
        print(f"  -> supplier_risk v{v.version} alias challenger (run {run_id[:8]})")

# ── 3. Anomaly detection — IsolationForest ─────────────────────
def train_anomaly():
    print("\n=== Anomaly detection (IsolationForest) ===")
    from sklearn.ensemble import IsolationForest

    np.random.seed(42)
    # Normal values ~ N(50, 10), anomalies ~ spikes
    normal = np.random.normal(50, 10, 500)
    X = normal.reshape(-1, 1)

    with mlflow.start_run(run_name="anomaly_detection"):
        model = IsolationForest(contamination=0.05, random_state=42)
        model.fit(X)
        # Sanity: should flag ~5% as anomaly
        preds = model.predict(X)
        anomaly_rate = (preds == -1).mean()
        print(f"  IsolationForest anomaly_rate={anomaly_rate:.3f}")

        mlflow.sklearn.log_model(model, artifact_path="model",
                                  registered_model_name="anomaly_detection")
        mlflow.log_metric("anomaly_rate", float(anomaly_rate))
        run_id = mlflow.active_run().info.run_id

    versions = client.get_latest_versions("anomaly_detection")
    if versions:
        v = max(versions, key=lambda x: int(x.version))
        client.set_registered_model_alias("anomaly_detection", "challenger", v.version)
        print(f"  -> anomaly_detection v{v.version} alias challenger (run {run_id[:8]})")

if __name__ == "__main__":
    train_prophet()
    train_supplier_risk()
    train_anomaly()
    print("\nDone. Registry:")
    for name in ["prophet_forecasting", "supplier_risk", "anomaly_detection"]:
        try:
            v = client.get_model_version_by_alias(name, "challenger")
            print(f"  {name}@{v.aliases} -> v{v.version} status={v.status}")
        except Exception as e:
            print(f"  {name}: {e}")
