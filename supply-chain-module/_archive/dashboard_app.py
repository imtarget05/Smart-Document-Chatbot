"""Supply Chain Automation — Streamlit Dashboard

Chạy:  supply-chain-module/api/.venv/bin/streamlit run supply-chain-module/dashboard/app.py

Gọi FastAPI backend tại SUPPLY_CHAIN_API_URL (mặc định http://127.0.0.1:8000)
Khi chạy Docker: http://supply-chain-module:8000
"""
import os
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

API_URL = os.getenv("SUPPLY_CHAIN_API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="Supply Chain Automation", layout="wide")
st.title("📦 Supply Chain Automation Dashboard")
st.caption(f"API: {API_URL} · Models: Prophet / LogisticRegression / IsolationForest / OR-Tools")

# Health
try:
    h = requests.get(f"{API_URL}/health", timeout=3).json()
    st.success(f"API {h.get('status')} — {h.get('service')}")
except Exception as e:
    st.error(f"API không kết nối được ({API_URL}): {e}")
    st.stop()

tabs = st.tabs(["📈 Forecast", "⚠️ Supplier Risk", "🚚 Route", "🔍 Anomaly", "📦 Inventory"])

# ── Forecast ──
with tabs[0]:
    st.subheader("Demand Forecasting — Prophet (MLflow)")
    hist_str = st.text_area("Lịch sử (CSV, 14+ điểm)", "10,12,11,13,14,12,15,16,14,13,15,17,16,18", key="hist")
    periods = st.slider("Số ngày forecast", 3, 30, 7, key="periods")
    if st.button("Forecast", key="btn_fc"):
        hist = [float(x.strip()) for x in hist_str.split(",") if x.strip()]
        r = requests.post(f"{API_URL}/forecast", json={"history": hist, "periods": periods}, timeout=15).json()
        st.json(r)
        if "forecast" in r and r["forecast"]:
            df = pd.DataFrame({"day": range(len(hist) + len(r["forecast"])),
                               "value": hist + r["forecast"],
                               "type": ["history"]*len(hist) + ["forecast"]*len(r["forecast"])})
            fig = px.line(df, x="day", y="value", color="type", markers=True, title="Forecast")
            st.plotly_chart(fig, use_container_width=True)

# ── Supplier Risk ──
with tabs[1]:
    st.subheader("Supplier Risk — LogisticRegression (MLflow)")
    c1, c2, c3 = st.columns(3)
    lt = c1.number_input("lead_time_std", 0.0, 30.0, 5.0)
    dr = c2.number_input("defect_rate", 0.0, 0.2, 0.02, format="%.3f")
    otr = c3.number_input("on_time_rate", 0.0, 1.0, 0.95)
    if st.button("Score", key="btn_risk"):
        r = requests.post(f"{API_URL}/supplier-risk", json={"lead_time_std": lt, "defect_rate": dr, "on_time_rate": otr}, timeout=10).json()
        st.json(r)
        if "risk_score" in r:
            score = r["risk_score"]
            color = "green" if score < 25 else "orange" if score < 50 else "red"
            st.metric("Risk Score", score, delta=r.get("risk_grade"))
            fig = go.Figure(go.Indicator(mode="gauge+number", value=score, gauge={"axis": {"range": [0,100]}, "bar": {"color": color}}))
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)

# ── Route ──
with tabs[2]:
    st.subheader("Route Optimization — OR-Tools VRP")
    st.caption("Nhập distance matrix (JSON). Ví dụ 4 điểm:")
    matrix_str = st.text_area("distance_matrix", "[[0,10,20,30],[10,0,15,25],[20,15,0,10],[30,25,10,0]]", key="matrix", height=80)
    nv = st.number_input("num_vehicles", 1, 5, 1, key="nv")
    if st.button("Optimize", key="btn_route"):
        import json
        try:
            mat = json.loads(matrix_str)
        except Exception as e:
            st.error(f"JSON lỗi: {e}")
            mat = None
        if mat is not None:
            r = requests.post(f"{API_URL}/optimize-route", json={"distance_matrix": mat, "num_vehicles": int(nv)}, timeout=15).json()
            st.json(r)
            if "routes" in r:
                for i, route in enumerate(r["routes"]):
                    st.write(f"Vehicle {i}: {' → '.join(map(str, route['stops']))} (dist {route['distance']})")

# ── Anomaly ──
with tabs[3]:
    st.subheader("Anomaly Detection — IsolationForest (MLflow)")
    vals_str = st.text_area("values (CSV)", "10,11,10,12,11,10,100,11,10,12", key="vals")
    thr = st.slider("threshold (fallback z-score)", 1.0, 5.0, 3.0, key="thr")
    if st.button("Detect", key="btn_anom"):
        vals = [float(x.strip()) for x in vals_str.split(",") if x.strip()]
        r = requests.post(f"{API_URL}/anomaly-detect", json={"values": vals, "threshold": thr}, timeout=10).json()
        st.json(r)
        if "anomalies" in r and r["anomalies"]:
            df = pd.DataFrame({"index": range(len(vals)), "value": vals, "anomaly": [False]*len(vals)})
            for a in r["anomalies"]:
                df.loc[a["index"], "anomaly"] = True
            fig = px.scatter(df, x="index", y="value", color="anomaly", title="Anomalies (red)")
            st.plotly_chart(fig, use_container_width=True)

# ── Inventory ──
with tabs[4]:
    st.subheader("Inventory — EOQ / Safety Stock / Reorder Point")
    c1, c2, c3 = st.columns(3)
    ad = c1.number_input("annual_demand", 1.0, 100000.0, 1200.0)
    oc = c2.number_input("order_cost", 1.0, 1000.0, 50.0)
    hc = c3.number_input("holding_cost", 0.1, 100.0, 2.0)
    c4, c5, c6 = st.columns(3)
    sd = c4.number_input("std_demand", 0.0, 100.0, 5.0)
    lt2 = c5.number_input("lead_time_days", 1.0, 30.0, 7.0)
    sl = c6.selectbox("service_level", [0.90, 0.95, 0.98, 0.99], index=1)
    if st.button("Calculate", key="btn_inv"):
        r = requests.post(f"{API_URL}/inventory-optimal-order", json={
            "annual_demand": ad, "order_cost": oc, "holding_cost": hc,
            "std_demand": sd, "lead_time_days": lt2, "service_level": sl}, timeout=10).json()
        st.json(r)
        if "eoq" in r:
            c1, c2, c3 = st.columns(3)
            c1.metric("EOQ", r["eoq"])
            c2.metric("Safety Stock", r["safety_stock"])
            c3.metric("Reorder Point", r["reorder_point"])
