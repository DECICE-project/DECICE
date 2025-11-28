from typing import Generator

import pytest
from fastapi.testclient import TestClient

from api import app
from config.config import get_settings


@pytest.fixture(scope="function", autouse=True)
def mock_env(monkeypatch):
    """
    This fixture automatically runs for every test. It's responsible for
    setting all necessary environment variables, ensuring that any code
    that calls get_settings() will receive a valid, predictable configuration.
    """
    # Monkeypatch environment
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DT_SERVICE_HOST", "mock-digital-twin")
    monkeypatch.setenv("DT_SERVICE_PORT", "8010")
    monkeypatch.setenv("PROMETHEUS_HOST", "mock-prometheus")
    monkeypatch.setenv("PROMETHEUS_PORT", "9090")
    monkeypatch.setenv("AUTO_UPDATE_DT_ENABLED", "false")
    monkeypatch.setenv("POWER_CONSUMPTION_PROMQL_QUERIES", "[]")
    monkeypatch.setenv("INTERNAL_API_KEY", "XuTThABy4NY__123456")

    # Clear the settings cache to force it to reload from the patched environment
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture(scope="function")
def test_client() -> Generator[TestClient, None, None]:
    """
    Provides a FastAPI TestClient. The environment is now handled automatically
    by the `mock_env` fixture.
    """
    with TestClient(app) as client:
        yield client
