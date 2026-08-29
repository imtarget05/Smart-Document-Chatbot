"""MLflow model loader — load registered models from the supply_chain experiment.

Models expected in registry (register_models.py đã tạo):
  - prophet_forecasting   (Prophet, alias 'challenger')
  - supplier_risk         (LogisticRegression, alias 'challenger')
  - anomaly_detection     (IsolationForest, alias 'challenger')
  - eoq_inventory         (DummyRegressor, alias 'challenger')

MLFLOW_TRACKING_URI env → SQLite db ở mlops/mlflow.db (local) hoặc
http://127.0.0.1:5000 (MLflow server).
"""

from __future__ import annotations

import os
import time as _time
from typing import Any

import mlflow
import mlflow.pyfunc  # noqa: F401
try:
    import mlflow.sklearn  # noqa: F401
except ImportError:
    pass
try:
    import mlflow.prophet  # noqa: F401
except ImportError:
    pass
from mlflow.tracking import MlflowClient

_TRACKING_URI = os.environ.get(
    "MLFLOW_TRACKING_URI",
    "sqlite:///" + os.path.join(os.path.dirname(__file__), "..", "mlops", "mlflow.db"),
)
_REGISTRY_CACHE: dict[str, Any] = {}
_REGISTRY_CACHE_TS: dict[str, float] = {}
_CACHE_TTL_SEC = 600  # 10 phút


def _ensure_client() -> MlflowClient:
    mlflow.set_tracking_uri(_TRACKING_URI)
    return MlflowClient()


def _cache_key(name: str) -> str:
    return name


def load_registered_model(name: str, alias: str = "challenger") -> Any:
    """Load a registered model by name + alias, với cache 10 phút."""
    key = _cache_key(name)
    now = _time.time()
    cached = _REGISTRY_CACHE.get(key)
    if cached is not None and now - _REGISTRY_CACHE_TS.get(key, 0) < _CACHE_TTL_SEC:
        return cached

    client = _ensure_client()
    model_uri = f"models:/{name}@{alias}"
    try:
        if name in ("supplier_risk", "anomaly_detection"):
            model = mlflow.sklearn.load_model(model_uri)  # type: ignore[attr-defined]
        elif name == "prophet_forecasting":
            model = mlflow.prophet.load_model(model_uri)  # type: ignore[attr-defined]
        else:
            model = mlflow.pyfunc.load_model(model_uri)  # type: ignore[attr-defined]
    except Exception as exc:
        raise RuntimeError(
            f"Không load được model {name}@{alias}: {exc}"
        ) from exc

    _REGISTRY_CACHE[key] = model
    _REGISTRY_CACHE_TS[key] = now
    return model


def model_available(name: str, alias: str = "challenger") -> bool:
    """Check nếu model đã register trong MLflow."""
    client = _ensure_client()
    try:
        client.get_model_version_by_alias(name, alias)
        return True
    except Exception:
        return False
