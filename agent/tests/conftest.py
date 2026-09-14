import os
import sys

# Ensure test environment mode so secret validators allow test tokens
os.environ.setdefault("APP_ENV", "test")

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

@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        args = {arg: pyfuncitem.funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames if arg in pyfuncitem.funcargs}
        asyncio.run(pyfuncitem.obj(**args))
        return True
