from unittest.mock import MagicMock, patch

import httpx
import pytest

from clients.promql_wrapper.client import PromQLWrapperClient, get_promql_wrapper_client


def test_get_promql_wrapper_client_success():
    """
    GIVEN valid application settings with a configured base URL
    WHEN get_promql_wrapper_client is called
    THEN it should return a PromQLWrapperClient instance configured with that URL.
    """
    mock_settings = MagicMock()
    mock_settings.PROMQL_WRAPPER_BASE_URL = "http://mock-promql:8050"

    mock_http_client = MagicMock(spec=httpx.AsyncClient)

    with patch(
        "clients.promql_wrapper.client.get_settings", return_value=mock_settings
    ):
        client_instance = get_promql_wrapper_client(client=mock_http_client)

    assert isinstance(client_instance, PromQLWrapperClient)
    assert client_instance.base_url == "http://mock-promql:8050"
    assert client_instance.client is mock_http_client


def test_get_promql_wrapper_client_raises_value_error_if_not_configured():
    """
    GIVEN application settings where the base URL is missing (None)
    WHEN get_promql_wrapper_client is called
    THEN it should raise a ValueError.
    """
    mock_settings = MagicMock()
    mock_settings.PROMQL_WRAPPER_BASE_URL = None

    mock_http_client = MagicMock(spec=httpx.AsyncClient)

    with patch(
        "clients.promql_wrapper.client.get_settings", return_value=mock_settings
    ):
        with pytest.raises(
            ValueError, match="PromQL Wrapper Base URL .* is not configured"
        ):
            get_promql_wrapper_client(client=mock_http_client)
