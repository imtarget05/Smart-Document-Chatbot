# Review Card — MAIA-diff + prune n8n/supply-chain (2026-09-14)

**Verdict: PASS (approve-with-notes, 0 critical)**

## Intended vs Actual
- Intended (plan T1-T10): xoá n8n-workflows + dọn compose/env/README + V-drop; tỉa 6 ipynb + mlruns/db + Dockerfile 8000 + archive dashboard; giữ core API; lock 5 diff MAIA.
- Actual (`git diff HEAD --stat`): 17 files, 1018 deletions(-), 0 additions tracked. `git diff HEAD --name-only`: .env.example, README.md, 2 compose, 4 n8n-workflows, Dockerfile, 6 ipynb, mlflow.db, dashboard rename. `git diff HEAD -- backend/` = rỗng → core Java/llm-router/frontend untouched. Untracked: V15 migration + plans/ + tasks/ (evidence mới, đúng scope).

## Commands passed (evidence tươi 2026-09-14)
- `ls n8n-workflows` → No such file; `ls supply-chain-module/*.ipynb` → no matches; `ls supply-chain-module/Dockerfile` → No such file; `_archive/dashboard_app.py` present → PASS
- `grep -rn n8n docker/ .env.example README.md` (trừ AUDIT/PLAN) → CLEAN → PASS
- `python3 -m pytest supply-chain-module/api/tests/test_api.py -q` → 9 passed in 0.23s → PASS
- `yaml.safe_load(compose.yml + dev.yml)` → YAML_OK → PASS
- `cat V15__drop_n8n_analytics.sql` → 3x DROP TABLE IF EXISTS → PASS, naming V15 đúng (V13/V14 đã tồn tại)

## Issues (severity)
- CRITICAL: không có.
- MAJOR: không có (reviewer trước báo BLOCKED do thiếu diff — đã bù đủ evidence, core untouched xác nhận).
- MINOR-1: `application.yml:93` default `localhost:8000` lệch chuẩn 8020 (pre-existing, env `SUPPLY_CHAIN_API_URL` override ở render/dev) → task follow-up, không block.
- MINOR-2: `tasks/notes` từng ghi V13, đã sửa thành V15 → done.

## Residual risk / Rollback
- Risk thấp: prune-only deletions; migration chưa apply ở env này; working tree chưa commit.
- Rollback: `git stash -u` hoặc `git checkout -- . && git clean -fd`; V15 IF EXISTS an toàn V1-V11.
