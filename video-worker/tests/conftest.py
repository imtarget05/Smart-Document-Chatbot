import sys
from pathlib import Path

# Make the ``video_worker`` package importable when pytest runs from the repo
# root (mirrors llm-router/tests/conftest.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))