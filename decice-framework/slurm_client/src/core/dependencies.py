import httpx
from fastapi import Request


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Retrieves the shared httpx.AsyncClient from the application state."""
    return request.app.state.http_client
