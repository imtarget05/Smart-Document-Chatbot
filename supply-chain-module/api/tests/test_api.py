import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from api.main import create_app
from api.services import (detect_anomalies, forecast_demand,
                          inventory_optimal_order, optimize_route,
                          supplier_risk)

client = TestClient(create_app())


# ---------------- services ----------------

def test_forecast_returns_periods():
    r = forecast_demand([10, 12, 11, 13, 14, 12, 15, 16, 14, 13, 15, 17, 16, 18], periods=7)
    assert len(r["forecast"]) == 7
    assert all(v >= 0 for v in r["forecast"])


def test_forecast_insufficient_history():
    assert forecast_demand([1, 2, 3])["method"] == "insufficient_history"


def test_supplier_risk_grades():
    low = supplier_risk(1.0, 0.01, 0.98)
    high = supplier_risk(14.0, 0.09, 0.5)
    assert low["risk_grade"] == "A" and high["risk_score"] > low["risk_score"]
    assert 0 <= low["risk_score"] <= 100


def test_optimize_route_visits_all_and_returns():
    matrix = [[0, 10, 20, 30], [10, 0, 15, 25], [20, 15, 0, 10], [30, 25, 10, 0]]
    r = optimize_route(matrix, num_vehicles=1)
    route = r["routes"][0]["stops"]
    assert route[0] == 0 and route[-1] == 0
    assert sorted(route[:-1]) == [0, 1, 2, 3]
    assert r["total_distance"] <= 75  # naive order = 10+15+10+30 = 65... just sanity


def test_detect_anomalies_finds_spike():
    values = [10, 11, 10, 12, 11, 10, 100, 11, 10, 12]
    r = detect_anomalies(values)
    assert r["count"] >= 1 and r["anomalies"][0]["index"] == 6


def test_inventory_eoq():
    r = inventory_optimal_order(1200, 50, 2, std_demand=5, lead_time_days=7)
    assert abs(r["eoq"] - 244.95) < 1  # sqrt(2*1200*50/2) = 244.95
    assert r["safety_stock"] > 0 and r["reorder_point"] > r["safety_stock"]


# ---------------- API ----------------

def test_api_forecast_endpoint():
    resp = client.post("/forecast", json={"history": [10, 12, 11, 13, 14, 12, 15, 16], "periods": 5})
    assert resp.status_code == 200 and len(resp.json()["forecast"]) == 5


def test_api_supplier_risk_endpoint():
    resp = client.post("/supplier-risk", json={"lead_time_std": 2, "defect_rate": 0.02, "on_time_rate": 0.95})
    assert resp.status_code == 200 and "risk_score" in resp.json()


def test_api_health():
    assert client.get("/health").json()["status"] == "ok"