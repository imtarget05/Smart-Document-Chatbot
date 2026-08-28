# Supply Chain Automation Sprint — 6-Day Plan

Ngày hiện tại sau sprint SmartDoc (agentic layer + supply-chain API đã có).

## Trạng thái đã xong (baseline)

- `supply-chain-module/api`: FastAPI service deterministic (forecast, VRP,
  risk, anomaly, EOQ) — 9/9 tests, Dockerfile, deploy trên Render Blueprint
- Agent (`llm-router/agent/graph.py`) đã nối thật qua `SUPPLY_CHAIN_API_URL`
- Notebooks gốc: demand forecasting (Prophet), inventory (EOQ), supplier risk
  (RandomForest), anomaly (IsolationForest), route (OR-Tools), EDA

## Day 1 — Data foundation

- Chọn dataset: Kaggle "DataCo Smart Supply Chain" hoặc UCI "Online Retail II"
- Đặt `supply-chain-module/data/` (+ .gitignore dữ liệu lớn, commit schema only)
- EDA notebook: clean, feature engineering (rolling demand, lead-time stats)
- Output: `features.csv` dùng chung cho tất cả models

## Day 2 — Models thật thay service-layer heuristic

- `api/services.py` nâng cấp: train models thật (job offline, load artifact lúc serve)
  - Forecast: Prophet (hoặc statsmodels SARIMAX — nhẹ hơn) → lưu `models/forecast.pkl`
  - Risk: RandomForest → `models/risk.pkl` + feature importances (giải thích được)
  - Anomaly: IsolationForest → `models/anomaly.pkl`
- Giữ deterministic fallback khi artifact không load được (grounded principle)
- Tests: mỗi endpoint có test với model thật + test fallback

## Day 3 — Route optimization + warehouse slotting

- Thay NN+2-opt bằng OR-Tools VRP khi số stops > 15 (routing_enums, time limit 5s)
- Thêm endpoint `POST /warehouse-slotting`: ABC-XYZ classification → slot assignment
- Benchmark: so OR-Tools vs heuristic trên 50 stops (latency + gap %)

## Day 4 — Streamlit dashboard

- `supply-chain-module/dashboard/app.py`: Streamlit multi-page
  - Page Demand: upload/history input → forecast chart + MAE
  - Page Risk: bảng suppliers + risk grade distribution
  - Page Routes: map (folium) của VRP solution
  - Page Inventory: EOQ/safety stock calculator
- Gọi qua HTTP tới API (không import trực tiếp) — cùng contract với agent

## Day 5 — Deploy + CI/CD

- Render deploy supply-chain-api (Blueprint đã có) + dashboard (Docker runtime)
- GitHub Actions: test workflow cho `supply-chain-module/api` (mirror llm-router CI)
- Smoke test script `scripts/smoke_supply_chain.sh`: health → forecast → VRP → agent e2e
- Verify agent e2e trên staging: `POST /agent/invoke` với `SUPPLY_CHAIN_API_URL` trỏ Render

## Day 6 — Portfolio + case study

- Case study write-up: business problem → approach → metrics (MAE forecast,
  risk AUC, VRP gap, latency) → architecture diagram (agent → tools)
- GitHub Pages portfolio: project cards + architecture diagrams + demo GIF
- Screenshot Langfuse traces (agent tool calls) làm bằng chứng observability

## Nguyên tắc xuyên suốt

1. Mọi model call đều deterministic-reproducible (seed cố định) hoặc có fallback
2. Mọi endpoint test-covered trước khi wire vào agent
3. Mỗi ngày kết thúc bằng commit + push + smoke test xanh
