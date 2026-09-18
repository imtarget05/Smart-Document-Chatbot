import os
import sys

# Ensure test environment mode so secret validators allow test tokens
os.environ.setdefault("APP_ENV", "test")
# Force in-memory fallback for graph-memory tests: never hit real Neon staging
# (.env points POSTGRES_HOST at Neon; without this, tests pollute shared DB
# and accumulate state across runs, e.g. get_stats 20 == 2).
os.environ["POSTGRES_HOST"] = "127.0.0.1"
os.environ["POSTGRES_PORT"] = "15432"

agent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(agent_dir, ".."))
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)
if root_dir not in sys.path:
    sys.path.insert(1, root_dir)

import inspect
import asyncio
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio")
    config.addinivalue_line("markers", "integration: marks tests requiring external services (Postgres/Qdrant/LLM)")
    config.addinivalue_line("markers", "slow: marks tests taking tens of seconds; excluded from fast CI")

@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        args = {arg: pyfuncitem.funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames if arg in pyfuncitem.funcargs}
        asyncio.run(pyfuncitem.obj(**args))
        return True


@pytest.fixture(autouse=True)
def _force_graph_memory_in_memory(monkeypatch):
    """Docstring intent is in-memory fallback — patch pool to None so no
    test ever touches real Neon, and each GraphMemory starts empty."""
    try:
        from memory.graph_memory import GraphMemory

        async def _no_pool(self):
            return None

        monkeypatch.setattr(GraphMemory, "_get_pool", _no_pool)
    except ImportError:
        pass
