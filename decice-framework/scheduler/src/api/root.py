import logging

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from core.schemas import ComponentStatus, HealthCheckResponse

logger = logging.getLogger(__name__)
root_router = APIRouter()


@root_router.get(
    "/", include_in_schema=False, status_code=status.HTTP_307_TEMPORARY_REDIRECT
)
async def home():
    """Redirects the root path to the API documentation."""
    return RedirectResponse(url="/docs/")


@root_router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Performs a health check of the application and its critical components.",
)
async def health_check(request: Request):
    """
    Provides the operational status of the AI Scheduler API.
    - **overall_status**: "healthy" if critical components are initialized, "degraded" or "unhealthy" otherwise.
    - **components**: Status of individual critical components.

    This endpoint can serve as both a liveness (is the app process running?)
    and a basic readiness probe (are critical components initialized?).
    For strict readiness, if overall_status is not 'healthy', a 503 might be raised.
    """
    component_statuses_models: dict[str, ComponentStatus] = {}
    all_components_ok = True

    # Check if startup itself was healthy
    if not getattr(request.app.state, "startup_healthy", False):
        all_components_ok = False
        component_statuses_models["application_startup"] = ComponentStatus(
            status="ERROR",
            details="Core component initialization failed during startup.",
        )
        logger.error("Health Check: Detected startup initialization failure.")
    else:
        component_statuses_models["application_startup"] = ComponentStatus(status="OK")

    # Check for settings
    if (
        hasattr(request.app.state, "settings")
        and request.app.state.settings is not None
    ):
        component_statuses_models["app_settings"] = ComponentStatus(status="OK")
    else:
        component_statuses_models["app_settings"] = ComponentStatus(
            status="ERROR", details="Not initialized"
        )
        all_components_ok = False
        logger.warning("Health Check: AppSettings not found in app.state.")

    # Check for Kairos
    if (
        hasattr(request.app.state, "kairos_instance")
        and request.app.state.kairos_instance is not None
    ):
        component_statuses_models["kairos_service"] = ComponentStatus(status="OK")
    else:
        component_statuses_models["kairos_service"] = ComponentStatus(
            status="ERROR", details="Not initialized"
        )
        all_components_ok = False
        logger.warning("Health Check: Kairos instance not found in app.state.")

    # Check for AIScheduler
    if (
        hasattr(request.app.state, "ai_scheduler_instance")
        and request.app.state.ai_scheduler_instance is not None
    ):
        component_statuses_models["ai_scheduler_service"] = ComponentStatus(status="OK")
    else:
        component_statuses_models["ai_scheduler_service"] = ComponentStatus(
            status="ERROR", details="Not initialized"
        )
        all_components_ok = False
        logger.warning("Health Check: AIScheduler instance not found in app.state.")

    # Check for FuzzyGate
    if (
        hasattr(request.app.state, "fuzzy_gate_instance")
        and request.app.state.fuzzy_gate_instance is not None
    ):
        component_statuses_models["fuzzy_gate_service"] = ComponentStatus(status="OK")
    else:
        component_statuses_models["fuzzy_gate_service"] = ComponentStatus(
            status="ERROR", details="Not initialized"
        )
        all_components_ok = False
        logger.warning("Health Check: FuzzyGate instance not found in app.state.")

    # Determine overall status
    if all_components_ok:
        overall_status = "healthy"
        message = "Application and all critical components are operational."
        return HealthCheckResponse(
            overall_status=overall_status,
            message=message,
            components=component_statuses_models,
        )
    else:
        overall_status = "degraded"
        message = "Application is running, but one or more critical components may not be initialized correctly or startup failed."

        # If raising an HTTPException for a readiness probe failure:
        component_statuses_dict = {
            k: v.model_dump(exclude_none=True)
            for k, v in component_statuses_models.items()
        }
        logger.error(
            f"Health Check returning 503: {overall_status}, Components: {component_statuses_dict}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "overall_status": overall_status,
                "message": message,
                "components": component_statuses_dict,
            },
        )
