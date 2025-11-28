import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from config.config import get_settings

API_KEY_HEADER_NAME = "X-Internal-Api-Key"
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


async def verify_internal_traffic(
    api_key_header: str = Security(api_key_header),
):
    """
    Verifies that the request comes from a trusted internal service
    by checking the shared secret.
    """
    settings = get_settings()

    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing internal authentication credentials",
        )

    # secrets.compare_digest prevents timing attacks
    if not secrets.compare_digest(api_key_header, settings.INTERNAL_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal authentication credentials",
        )

    return True
