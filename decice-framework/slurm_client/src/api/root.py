import logging
from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/", include_in_schema=False, status_code=status.HTTP_307_TEMPORARY_REDIRECT
)
async def home():
    """Redirects the root path to the API documentation."""
    return RedirectResponse(url="/docs/")


@router.get(
    "/health",
    summary="Performs a deep health check of the service and its dependencies",
    tags=["health"],
)
async def health_check():
    return status.HTTP_200_OK
