import functools
import logging

import httpx
from fastapi import HTTPException, status

from services.token_service import TokenConnectionError, TokenResponseError

logger = logging.getLogger(__name__)


def handle_errors(func):
    """
    Decorator to catch and map internal exceptions to proper HTTP errors.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)

        # Slurm-related HTTP errors (via httpx)
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"HTTP error from Slurm service: {e.response.text}",
            )

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not reach Slurm service: {str(e)}",
            )

        # Token service errors
        except TokenConnectionError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Token service unavailable: {str(e)}",
            )

        except TokenResponseError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token service returned invalid data: {str(e)}",
            )

        # Generic fallback
        except Exception as e:
            logger.exception(f"Unhandled error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}",
            )

    return wrapper
