import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException, UploadFile

from clients.psgc.client import PsgcClient


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Provides a mock httpx.AsyncClient with an awaitable 'post' method."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.post = AsyncMock()
    return client


@pytest.fixture
def psgc_client(mock_http_client: MagicMock) -> PsgcClient:
    """Provides an instance of PsgcClient initialized with a mock client."""
    return PsgcClient(base_url="http://mock-psgc:8040", client=mock_http_client)


@pytest.mark.asyncio
class TestPsgcClient:
    """Test suite for the PsgcClient."""

    async def test_delegate_workflow_success(
        self,
        psgc_client: PsgcClient,
        mock_http_client: MagicMock,
    ):
        """
        GIVEN a workflow payload
        WHEN delegate_workflow is called
        THEN it should make a correctly structured JSON POST request.
        """
        workflow_payload = {"id": "wf1", "name": "test-workflow"}
        storage_filename = "data.zip"
        expected_response = {"status": "success", "id": "wf1"}

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value=expected_response)
        mock_http_client.post.return_value = mock_response

        result = await psgc_client.delegate_workflow(
            workflow_payload=workflow_payload,
            filename=storage_filename,
        )

        assert result == expected_response
        mock_http_client.post.assert_awaited_once()

        call_kwargs = mock_http_client.post.call_args.kwargs

        assert call_kwargs["url"] == "http://mock-psgc:8040/workflows"

        expected_payload = workflow_payload.copy()
        expected_payload["filename"] = storage_filename
        assert call_kwargs["json"] == expected_payload

    async def test_delegate_workflow_handles_request_error(
        self,
        psgc_client: PsgcClient,
        mock_http_client: MagicMock,
    ):
        request_error = httpx.RequestError("DNS lookup failed", request=None)
        mock_http_client.post.side_effect = request_error

        with pytest.raises(HTTPException) as exc_info:
            await psgc_client.delegate_workflow({}, "file.zip")

        assert exc_info.value.status_code == 503
        assert "Network error connecting to PSGC" in exc_info.value.detail

    async def test_delegate_workflow_handles_http_status_error(
        self,
        psgc_client: PsgcClient,
        mock_http_client: MagicMock,
    ):
        mock_error_response = httpx.Response(
            status_code=422, text="Validation Error", request=None
        )
        status_error = httpx.HTTPStatusError(
            message="Unprocessable Entity", request=None, response=mock_error_response
        )
        mock_http_client.post.side_effect = status_error

        with pytest.raises(HTTPException) as exc_info:
            await psgc_client.delegate_workflow({}, "file.zip")

        assert exc_info.value.status_code == 422
        assert (
            "PSGC request failed with status 422: Validation Error"
            in exc_info.value.detail
        )
