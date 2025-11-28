import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from auth.auth import verify_internal_traffic
from services.data_service import DataService, get_data_service

logger = logging.getLogger(__name__)
data_router = APIRouter(prefix="/data")


class GenerateDataRequest(BaseModel):
    """
    Configuration for generating synthetic scheduling scenarios.
    """

    num_files: int = Field(
        10,
        ge=1,
        le=10000,
        description="The number of unique JSON scenario files to generate.",
    )
    jobs_min: int = Field(
        5, ge=1, description="Minimum number of jobs (tasks) per scenario."
    )
    jobs_max: int = Field(
        20, ge=1, description="Maximum number of jobs (tasks) per scenario."
    )
    # If your DataService supports node ranges, add them here.
    # Currently keeping it simple to match the Service signature.


class DatasetSummary(BaseModel):
    name: str = Field(..., description="The unique name of the dataset folder.")
    file_count: int = Field(..., description="Number of JSON scenarios in the dataset.")
    path: str = Field(..., description="Absolute path or S3 key.")


class OperationResponse(BaseModel):
    """
    Generic response for data operations.
    """

    status: str
    dataset_name: str
    message: str | None = None
    details: dict[str, Any] | None = None


# Routes
@data_router.post(
    "/generate/{dataset_name}",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_traffic)],
    summary="Generate Synthetic Dataset",
)
async def generate_dataset(
    dataset_name: str,
    request: GenerateDataRequest,
    service: DataService = Depends(get_data_service),
):
    """
    **Triggers the generation of a new synthetic dataset.**

    The system will create a folder named `dataset_name` and populate it with
    randomized scheduling scenarios based on the parameters provided.

    - **dataset_name**: Unique identifier (folder name). Must not already exist.
    - **num_files**: Volume of data to generate.
    - **jobs_min/max**: Complexity of each scenario.
    """
    logger.info(
        f"API: Request to generate dataset '{dataset_name}' with {request.num_files} files."
    )

    try:
        # Call the service layer
        result = await service.create_synthetic_dataset(
            name=dataset_name,
            num_files=request.num_files,
            job_min=request.jobs_min,
            job_max=request.jobs_max,
        )

        # Handle Service-level errors (like file existence)
        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=result.get("message")
            )

        return OperationResponse(
            status="created",
            dataset_name=dataset_name,
            message=f"Successfully generated {result.get('files_generated')} scenarios.",
            details=result,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error generating dataset '{dataset_name}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the dataset.",
        )


@data_router.post(
    "/upload/{dataset_name}",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_traffic)],
    summary="Upload Custom Dataset",
)
async def upload_dataset(
    dataset_name: str,
    files: list[UploadFile] = File(
        ..., description="List of .json scenario files to upload."
    ),
    service: DataService = Depends(get_data_service),
):
    """
    **Uploads existing JSON scenario files to create a new dataset.**

    Use this if you have specific edge-cases or real-world data captures
    you want to use for training/testing.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided in the upload.",
        )

    logger.info(f"API: Uploading {len(files)} files to dataset '{dataset_name}'.")

    try:
        result = await service.upload_dataset(dataset_name, files)

        return OperationResponse(
            status="uploaded",
            dataset_name=dataset_name,
            message=f"Successfully uploaded {result.get('files_uploaded')} files.",
            details=result,
        )
    except Exception as e:
        logger.error(
            f"Unexpected error uploading to '{dataset_name}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing uploads.",
        )


@data_router.get(
    "/",
    response_model=list[DatasetSummary],
    dependencies=[Depends(verify_internal_traffic)],
    summary="List All Datasets",
)
async def list_datasets(service: DataService = Depends(get_data_service)):
    """
    **Returns a list of all available datasets.**

    Includes metadata like file counts and server paths. Useful for
    populating dropdowns in a UI when selecting data for training.
    """
    # The service returns a list of dicts, Pydantic will validate/serialize them
    return await service.list_datasets()


@data_router.delete(
    "/{dataset_name}",
    response_model=OperationResponse,
    dependencies=[Depends(verify_internal_traffic)],
    summary="Delete Dataset",
)
async def delete_dataset(
    dataset_name: str, service: DataService = Depends(get_data_service)
):
    """
    **Permanently deletes a dataset and its contents.**
    """
    logger.info(f"API: Request to delete dataset '{dataset_name}'.")

    result = await service.delete_dataset(dataset_name)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=result.get("message")
        )

    return OperationResponse(
        status="deleted",
        dataset_name=dataset_name,
        message="Dataset folder removed successfully.",
    )
