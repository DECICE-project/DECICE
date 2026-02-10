import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth.auth import verify_internal_traffic
from config.config import get_settings
from core.ai_scheduler import AIScheduler
from core.schemas import SchedulerDefinition
from dependencies import get_ai_scheduler  # <--- IMPORT THIS
from services.model_service import ModelService, get_model_service

logger = logging.getLogger(__name__)
models_router = APIRouter(prefix="/models")


class SwapRequest(BaseModel):
    scheduler_name: str


@models_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_traffic)],
)
async def create_scheduler_definition(
    definition: SchedulerDefinition, service: ModelService = Depends(get_model_service)
):
    """Define a new Scheduler architecture/configuration."""
    try:
        return service.create_scheduler_definition(definition)
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@models_router.get(
    "/",
    response_model=List[str],
    dependencies=[Depends(verify_internal_traffic)],
)
async def list_models(service: ModelService = Depends(get_model_service)):
    return service.list_models()


@models_router.post("/swap", status_code=status.HTTP_200_OK)
async def swap_model(
    request: SwapRequest,
    # This dependency injects the Singleton running in the Main Process
    scheduler: AIScheduler = Depends(get_ai_scheduler),
):
    """
    Trigger a Hot-Swap of the live inference engine to a specific model version.
    """
    settings = get_settings()

    # Construct the physical path based on config
    target_model_path = settings.MODELS_BASE_DIR / request.scheduler_name

    if not target_model_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Scheduler '{request.scheduler_name}' not found at {target_model_path}",
        )

    # Tell the Singleton to reload
    success = scheduler.hot_swap_model(
        new_model_name=request.scheduler_name, new_model_base_path=target_model_path
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Hot-swap failed. Check logs for Tensorflow loading errors.",
        )

    return {
        "status": "swapped",
        "current_version": request.scheduler_name,
        "message": "Inference engine updated successfully.",
    }


@models_router.get("/current")
async def get_active_model(scheduler: AIScheduler = Depends(get_ai_scheduler)):
    """Return the ID of the currently loaded model."""
    return {"current_model": scheduler.current_model_name}


@models_router.get(
    "/{name}",
    response_model=SchedulerDefinition,
    dependencies=[Depends(verify_internal_traffic)],
)
async def get_model_details(
    name: str, service: ModelService = Depends(get_model_service)
):
    model = service.get_scheduler_definition(name)
    if not model:
        raise HTTPException(status_code=404, detail="Model definition not found")
    return model
