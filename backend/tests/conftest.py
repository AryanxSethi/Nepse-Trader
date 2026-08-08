"""Pytest fixtures — makes the backend package importable and provides a lifespan-free test client.

These tests are deterministic and network-free: they cover pure helpers and
input-validation paths (HTTP 400/404) only. The network-dependent baseline
smoke lives in ``tests/smoke_baseline.py``.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import main  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    """TestClient WITHOUT lifespan — no DB init, no seeding, no background tasks."""
    return TestClient(main.app)