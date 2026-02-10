import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiopromql.models.core import MetricLabelSet, TimeSeries

from clients.digital_twin import DigitalTwinClient
from models.models import DeciceDigitalTwin
from services.snapshot_service import SnapshotService


@pytest.fixture
def mock_dt_client() -> AsyncMock:
    """Provides a mock DigitalTwinClient."""
    return AsyncMock(spec=DigitalTwinClient)


@pytest.fixture
def mock_prometheus_client() -> AsyncMock:
    """
    Provides a mock for the aiopromql.PrometheusAsync context manager.
    """
    mock_query_response = MagicMock()

    metric_labels = MagicMock(spec=[MetricLabelSet, "__iter__"])

    metric_labels.dict = {
        "__name__": "node_cpu_seconds_total",
        "nodename": "test-node-01",
    }
    metric_labels.__iter__.return_value = iter(metric_labels.dict.items())

    metric_timeseries = MagicMock(spec=TimeSeries)
    metric_timeseries.latest.return_value = MagicMock(value=42.0)

    mock_query_response.to_metric_map.return_value = {metric_labels: metric_timeseries}

    client = AsyncMock()
    client.query = AsyncMock(return_value=mock_query_response)

    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = client
    return mock_context_manager


@pytest.mark.asyncio
class TestSnapshotService:
    async def test_create_and_post_snapshot_happy_path(
        self, mock_dt_client: AsyncMock, mock_prometheus_client: AsyncMock, monkeypatch
    ):
        """
        GIVEN successful responses from all downstream services
        WHEN create_and_post_snapshot is called
        THEN it should fetch, transform, and post the data correctly.
        """
        monkeypatch.setattr(
            "prometheus.prom_service.PrometheusAsync",
            lambda *args, **kwargs: mock_prometheus_client,
        )
        service = SnapshotService(dt_client=mock_dt_client)

        await service.create_and_post_snapshot()

        mock_dt_client.post_model_core.assert_awaited_once()

        call_args = mock_dt_client.post_model_core.call_args[0]
        posted_data: DeciceDigitalTwin = call_args[0]

        assert isinstance(posted_data, DeciceDigitalTwin)

        found_node = False
        for vp in posted_data.vertexpools:
            for node in vp.nodes:
                if node.name == "test-node-01":
                    found_node = True
                    break
        assert found_node, (
            "The test node from the mock Prometheus was not found in the final snapshot"
        )

    async def test_snapshot_propagates_prometheus_exception(
        self, mock_dt_client: AsyncMock, mock_prometheus_client: AsyncMock, monkeypatch
    ):
        """
        GIVEN a Prometheus client that raises an exception during the query
        WHEN create_and_post_snapshot is called
        THEN it should propagate the exception and NOT call the DigitalTwinClient.
        """
        mock_prometheus_client.__aenter__.return_value.query.side_effect = Exception(
            "Prometheus connection failed"
        )

        monkeypatch.setattr(
            "prometheus.prom_service.PrometheusAsync",
            lambda *args, **kwargs: mock_prometheus_client,
        )

        service = SnapshotService(dt_client=mock_dt_client)

        with pytest.raises(Exception, match="Prometheus connection failed"):
            await service.create_and_post_snapshot()

        mock_dt_client.post_model_core.assert_not_awaited()

    async def test_snapshot_propagates_digital_twin_exception(
        self, mock_dt_client: AsyncMock, mock_prometheus_client: AsyncMock, monkeypatch
    ):
        """
        GIVEN a DigitalTwinClient that raises an HTTPException
        WHEN create_and_post_snapshot is called
        THEN it should correctly propagate the HTTPException.
        """
        from fastapi import HTTPException

        mock_dt_client.post_model_core.side_effect = HTTPException(
            status_code=503, detail="DT Service Unavailable"
        )

        monkeypatch.setattr(
            "prometheus.prom_service.PrometheusAsync",
            lambda *args, **kwargs: mock_prometheus_client,
        )

        service = SnapshotService(dt_client=mock_dt_client)

        with pytest.raises(HTTPException) as exc_info:
            await service.create_and_post_snapshot()

        assert exc_info.value.status_code == 503
        assert "DT Service Unavailable" in exc_info.value.detail
