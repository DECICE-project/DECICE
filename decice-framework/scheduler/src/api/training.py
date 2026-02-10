import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from auth.auth import verify_internal_traffic
from core.schemas import TrainingRunRequest
from services.model_service import ModelService, get_model_service
from services.training_service import TrainingService, get_training_service

logger = logging.getLogger(__name__)
training_router = APIRouter(prefix="/training")


@training_router.post(
    "/start",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_traffic)],
)
async def start_training(
    request: TrainingRunRequest,
    training_service: TrainingService = Depends(get_training_service),
    model_service: ModelService = Depends(get_model_service),
):
    """
    Start a training run.
    """
    # Validate Model Definition
    model_config = model_service.get_scheduler_definition(request.scheduler_name)
    if not model_config:
        raise HTTPException(
            status_code=404,
            detail=f"Scheduler definition '{request.scheduler_name}' not found.",
        )

    # Submit Job (Service now validates Dataset internally)
    try:
        return await training_service.start_training_job(
            request, model_config.model_dump()
        )
    except ValueError as e:
        # Catch the "Dataset not found" error from the service
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start training: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error starting training job."
        )


# @training_router.post("/data/upload/{dataset_name}")
# async def upload_training_data(
#     dataset_name: str,
#     files: list[UploadFile] = File(...),
#     data_service: DataService = Depends(get_data_service),
# ):
#     """Upload custom JSON scenarios to create a named dataset."""
#     return await data_service.upload_dataset(dataset_name, files)


# @training_router.get(
#     "/jobs/{job_id}",
#     response_model=TrainingJobStatus,
#     dependencies=[Depends(verify_internal_traffic)],
# )
# async def get_job_status(
#     job_id: str, training_service: TrainingService = Depends(get_training_service)
# ):
#     job = training_service.get_job_status(job_id)
#     if not job:
#         raise HTTPException(status_code=404, detail="Training job not found")
#     return job


# @training_router.get(
#     "/jobs",
#     response_model=list[TrainingJobStatus],
#     dependencies=[Depends(verify_internal_traffic)],
# )
# async def list_jobs(training_service: TrainingService = Depends(get_training_service)):
#     return training_service.list_jobs()


# ================================
# ================================
# class GenerateDataRequest(BaseModel):
#     """Parameters for synthetic data generation."""

#     num_files: int = Field(
#         10, ge=1, le=1000, description="Number of scenario files to generate."
#     )
#     jobs_min: int = Field(5, ge=1, description="Minimum number of jobs per scenario.")
#     jobs_max: int = Field(20, ge=1, description="Maximum number of jobs per scenario.")
#     # You could add node ranges here if you update the Service to accept them
#     # nodes_min: int = 10
#     # nodes_max: int = 50


# class DatasetSummary(BaseModel):
#     name: str
#     file_count: int
#     path: str


# @training_router.post(
#     "/generate/{dataset_name}",
#     status_code=status.HTTP_201_CREATED,
#     dependencies=[Depends(verify_internal_traffic)],
#     summary="Generate a synthetic dataset",
# )
# async def generate_dataset(
#     dataset_name: str,
#     request: GenerateDataRequest,
#     service: DataService = Depends(get_data_service),
# ):
#     """
#     Triggers the generation of synthetic scheduling scenarios.

#     - **dataset_name**: Unique name for the folder (e.g., 'train_small_v1').
#     - **num_files**: How many JSON scenarios to create.
#     """
#     try:
#         result = await service.create_synthetic_dataset(
#             name=dataset_name,
#             num_files=request.num_files,
#             job_min=request.jobs_min,
#             job_max=request.jobs_max,
#         )

#         if result.get("status") == "error":
#             raise HTTPException(
#                 status_code=status.HTTP_409_CONFLICT, detail=result.get("message")
#             )

#         return result

#     except Exception as e:
#         logger.error(f"Failed to generate dataset: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal error during data generation.",
#         )


# @training_router.post(
#     "/upload/{dataset_name}",
#     status_code=status.HTTP_201_CREATED,
#     dependencies=[Depends(verify_internal_traffic)],
#     summary="Upload custom training data",
# )
# async def upload_dataset(
#     dataset_name: str,
#     files: list[UploadFile] = File(..., description="List of JSON scenario files"),
#     service: DataService = Depends(get_data_service),
# ):
#     """
#     Upload your own JSON scenario files to create a dataset.
#     """
#     if not files:
#         raise HTTPException(status_code=400, detail="No files provided")

#     return await service.upload_dataset(dataset_name, files)


# @training_router.get(
#     "/",
#     response_model=list[DatasetSummary],
#     dependencies=[Depends(verify_internal_traffic)],
#     summary="List all available datasets",
# )
# async def list_datasets(service: DataService = Depends(get_data_service)):
#     return service.list_datasets()


# @training_router.delete(
#     "/{dataset_name}",
#     dependencies=[Depends(verify_internal_traffic)],
#     summary="Delete a dataset",
# )
# async def delete_dataset(
#     dataset_name: str, service: DataService = Depends(get_data_service)
# ):
#     result = service.delete_dataset(dataset_name)
#     if result["status"] == "error":
#         raise HTTPException(status_code=404, detail=result["message"])
#     return result
