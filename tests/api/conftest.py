"""Shared fixtures for API route tests: an isolated app + TestClient per test."""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from datadoom.api import create_app
from datadoom.config import Config

warnings.filterwarnings("ignore", category=DeprecationWarning)


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        home=tmp_path,
        db_url=f"sqlite:///{(tmp_path / 'datadoom.db').as_posix()}",
        artifacts_dir=tmp_path / "artifacts",
    )


@pytest.fixture
def client(config: Config) -> Iterator[TestClient]:
    # The context manager triggers lifespan (binds the event-loop for WS fan-out).
    with TestClient(create_app(config)) as c:
        yield c


@pytest.fixture
def sample_spec() -> dict:
    return {
        "datadoom_version": "1",
        "name": "fraud-demo",
        "rows": 400,
        "features": {
            "age": {"type": "numeric", "dist": "normal", "params": {"mean": 40, "std": 10}},
            "amount": {"type": "numeric", "dist": "normal", "params": {"mean": 100, "std": 30}},
            "channel": {"type": "categorical", "categories": ["web", "store", "phone"]},
            "is_fraud": {"type": "boolean", "rate": 0.1},
        },
    }
