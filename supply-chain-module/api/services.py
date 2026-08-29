"""Supply chain service layer — deterministic implementations.

Tương đương logic trong notebooks nhưng nhẹ (numpy-only, không cần
Prophet/ortools/sklearn) để chạy nhanh trong container nhỏ. Mỗi hàm
deterministic — cùng input luôn ra cùng output (grounded cho agent).

Nâng cấp Phase 2: load model thật từ MLflow registry (prophet_forecasting,
supplier_risk, anomaly_detection). Fallback deterministic khi model
không available.
"""
import os
from typing import Any

import numpy as np

try:
    from . import mlflow_models
except ImportError:
    mlflow_models = None  # MLflow unavailable — fallback mode

# ----------------------------------------------------------------------
# Demand forecasting — Prophet from MLflow registry, fallback linear trend
# ----------------------------------------------------------------------

def forecast_demand(history: list[float], periods: int = 30) -> dict:
    """Forecast demand từ chuỗi lịch sử: Prophet MLflow (hoặc fallback)."""
    if len(history) < 7:
        return {"forecast": [], "method": "insufficient_history",
                "detail": "cần ít nhất 7 điểm dữ liệu"}

    # Try MLflow Prophet
    if mlflow_models is not None:
        try:
            model = mlflow_models.load_registered_model("prophet_forecasting")
            import pandas as pd
            from datetime import datetime, timedelta
            future = pd.DataFrame({"ds": pd.date_range(
                datetime.utcnow(), periods=periods, freq="D")})
            fc = model.predict(future)
            return {
                "forecast": [round(float(v), 2) for v in fc["yhat"].tolist()],
                "method": "prophet_mlflow",
                "history_points": len(history),
            }
        except Exception:  # noqa: BLE001
            pass  # fallback below

    # Fallback deterministic — linear trend + weekly seasonality
    y = np.asarray(history, dtype=float)
    n = len(y)
    x = np.arange(n)
    slope, intercept = np.polyfit(x, y, 1)
    trend = intercept + slope * np.arange(n, n + periods)
    dow = np.arange(n) % 7
    global_mean = y.mean()
    seasonal = {d: y[dow == d].mean() - global_mean for d in range(7)}
    future_dow = (np.arange(n, n + periods)) % 7
    forecast = trend + np.array([seasonal[d] for d in future_dow])
    forecast = np.maximum(forecast, 0.0)
    return {
        "forecast": [round(float(v), 2) for v in forecast],
        "method": "linear_trend_weekly_seasonal",
        "history_points": n,
        "trend_per_period": round(float(slope), 4),
    }

# ---------------------------------------------------------------------
# Supplier risk scoring — LogisticRegression MLflow, fallback rule-based
# ---------------------------------------------------------------------

def supplier_risk(lead_time_std: float, defect_rate: float,
                  on_time_rate: float) -> dict:
    """Risk score 0-100 từ lead time variability, defect rate, on-time rate."""
    if not (0 <= on_time_rate <= 1) or defect_rate < 0 or lead_time_std < 0:
        return {"error": "invalid_input",
                "detail": "on_time_rate in [0,1]; defect_rate, lead_time_std >= 0"}

    if mlflow_models is not None:
        try:
            model = mlflow_models.load_registered_model("supplier_risk")
            X = np.array([[lead_time_std, defect_rate, on_time_rate]], dtype=float)
            proba = model.predict_proba(X)[0]
            risk_score = float(proba[1]) * 100 if len(proba) > 1 else float(proba[0]) * 100
            grade = "A" if risk_score < 25 else "B" if risk_score < 50 \
                    else "C" if risk_score < 75 else "D"
            return {
                "risk_score": round(risk_score, 1),
                "risk_grade": grade,
                "method": "logreg_mlflow",
                "components": {
                    "lead_time_variability": round(min(lead_time_std / 15.0, 1.0) * 30, 1),
                    "defect_rate": round(min(defect_rate / 0.10, 1.0) * 40, 1),
                    "on_time": round((1.0 - on_time_rate) * 30, 1),
                },
            }
        except Exception:  # noqa: BLE001 — fallback below
            pass

    # Fallback deterministic rule-based
    score = (
        min(lead_time_std / 15.0, 1.0) * 30.0
        + min(defect_rate / 0.10, 1.0) * 40.0
        + (1.0 - on_time_rate) * 30.0
    )
    grade = "A" if score < 25 else "B" if score < 50 \
            else "C" if score < 75 else "D"
    return {
        "risk_score": round(float(score), 1),
        "risk_grade": grade,
        "method": "rule_based_fallback",
        "components": {
            "lead_time_variability": round(min(lead_time_std / 15.0, 1.0) * 30, 1),
            "defect_rate": round(min(defect_rate / 0.10, 1.0) * 40, 1),
            "on_time": round((1.0 - on_time_rate) * 30, 1),
        },
    }


# ----------------------------------------------------------------------
# Route optimization (thay OR-Tools bằng nearest-neighbor + 2-opt)
# ----------------------------------------------------------------------

def optimize_route(distance_matrix: list[list[float]],
                   num_vehicles: int = 1, depot: int = 0) -> dict:
    """TSP/VRP heuristic: nearest-neighbor rồi 2-opt improvement."""
    n = len(distance_matrix)
    if n < 2 or not (0 <= depot < n):
        return {"error": "invalid_input"}
    d = np.asarray(distance_matrix, dtype=float)

    def route_length(route: list[int]) -> float:
        return sum(d[route[i]][route[i + 1]] for i in range(len(route) - 1))

    stops = [i for i in range(n) if i != depot]
    if num_vehicles > 1 and stops:
        angles = sorted(stops, key=lambda i: (
            np.arctan2(i - depot, 0.5 * (i + depot)), i))
        chunks = [angles[k::num_vehicles] for k in range(num_vehicles)]
    else:
        chunks = [stops]

    routes = []
    total = 0.0
    for chunk in chunks:
        if not chunk:
            continue
        route = [depot]
        remaining = list(chunk)
        while remaining:
            last = route[-1]
            nxt = min(remaining, key=lambda j: d[last][j])
            route.append(nxt)
            remaining.remove(nxt)
        route.append(depot)
        improved = True
        while improved:
            improved = False
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    if d[route[i - 1]][route[i]] + d[route[j]][route[j + 1]] > \
                       d[route[i - 1]][route[j]] + d[route[i]][route[j + 1]]:
                        route[i:j + 1] = route[i:j + 1][::-1]
                        improved = True
        total += route_length(route)
        routes.append({"stops": route, "distance": round(float(route_length(route)), 2)})

    return {"routes": routes, "total_distance": round(float(total), 2),
            "method": "nearest_neighbor_2opt"}


# ---------------------------------------------------------------------
# Anomaly detection — IsolationForest MLflow, fallback modified z-score
# ---------------------------------------------------------------------

def detect_anomalies(values: list[float], threshold: float = 3.0) -> dict:
    """Modified z-score anomaly detection trên chuỗi giá trị."""
    arr = np.asarray(values, dtype=float)
    if len(arr) < 5:
        return {"error": "insufficient_data", "detail": "cần ít nhất 5 điểm"}

    if mlflow_models is not None:
        try:
            model = mlflow_models.load_registered_model("anomaly_detection")
            X = arr.reshape(-1, 1)
            preds = model.predict(X)  # -1 anomaly, 1 normal
            decision = model.decision_function(X)
            anomalies = [
                {"index": int(i), "value": float(arr[i]),
                 "score": round(float(decision[i]), 2)}
                for i in range(len(arr)) if preds[i] == -1
            ]
            return {
                "anomalies": anomalies,
                "count": len(anomalies),
                "threshold": threshold,
                "method": "isolation_forest_mlflow",
            }
        except Exception:  # noqa: BLE001 — fallback below
            pass

    # Fallback: modified z-score
    median = np.median(arr)
    mad = np.median(np.abs(arr - median)) or 1e-9
    z = 0.6745 * (arr - median) / (1.4826 * mad)
    anomalies = [
        {"index": int(i), "value": float(arr[i]), "z": round(float(z[i]), 2)}
        for i in range(len(arr)) if abs(z[i]) > threshold
    ]
    return {
        "anomalies": anomalies,
        "count": len(anomalies),
        "threshold": threshold,
        "method": "modified_z_score_fallback",
    }


# ----------------------------------------------------------------------
# Inventory optimization (EOQ, safety stock, reorder point)
# ----------------------------------------------------------------------

def inventory_optimal_order(annual_demand: float, order_cost: float,
                            holding_cost: float, std_demand: float = 0.0,
                            lead_time_days: float = 1.0,
                            service_level: float = 0.95) -> dict:
    """EOQ + safety stock + reorder point."""
    if annual_demand <= 0 or order_cost <= 0 or holding_cost <= 0:
        return {"error": "invalid_input",
                "detail": "demand, order_cost, holding_cost phải > 0"}
    from math import sqrt
    z_table = {0.90: 1.2816, 0.95: 1.6449, 0.98: 2.0537, 0.99: 2.3263}
    z_score = min(z_table.items(), key=lambda kv: abs(kv[0] - service_level))[1]
    eoq = sqrt(2 * annual_demand * order_cost / holding_cost)
    daily = annual_demand / 365.0
    safety = z_score * std_demand * sqrt(lead_time_days)
    rop = daily * lead_time_days + safety
    return {
        "eoq": round(float(eoq), 2),
        "safety_stock": round(float(safety), 2),
        "reorder_point": round(float(rop), 2),
        "daily_demand": round(float(daily), 2),
        "service_level": service_level,
        "z_score": z_score,
    }
