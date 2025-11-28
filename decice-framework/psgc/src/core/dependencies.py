import httpx
import redis.asyncio as redis
from fastapi import Request
from minio import Minio


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Retrieves the shared httpx.AsyncClient from the application state."""
    return request.app.state.http_client


def get_minio_client(request: Request) -> Minio:
    """Retrieves the shared minio_client from the application state."""
    return request.app.state.minio_client


def get_redis_client(request: Request) -> redis.Redis:
    return request.app.state.redis_client
