from fastapi import APIRouter, Depends, status

from auth.auth import verify_internal_traffic
from schemas.jobs import (SlurmClientRequest, SlurmEpilogResponse,
                          SlurmJobSubmitResponse, SlurmResponse)
from services.slurm_service import SlurmService, get_slurm_service
from services.token_service import TokenService, get_token_service
from utils.handle_errors import handle_errors

router = APIRouter()


@router.post(
    "/submit",
    response_model=SlurmJobSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_traffic)],
)
@handle_errors
async def submit_job(
    request: SlurmClientRequest,
    slurm_service: SlurmService = Depends(get_slurm_service),
    token_service: TokenService = Depends(get_token_service),
):
    token = token_service.request_token(request.username)

    slurm_response = await slurm_service.submit_job(
        username=request.username,
        token=token,
        script_content=request.slurm_file_content,
        job_name=str(request.task_id),
        work_dir=request.work_dir,
    )

    return slurm_response


@router.post("/job_event", status_code=status.HTTP_201_CREATED)
async def get_job_status_from_slurm(job_info: SlurmEpilogResponse):
    print("Job status information from Slurm Epilog script received:", job_info)


@router.get("/{job_id}", response_model=SlurmResponse, status_code=status.HTTP_200_OK)
@handle_errors
async def get_job_info(
    job_id: int,
    slurm_service: SlurmService = Depends(get_slurm_service),
    token_service: TokenService = Depends(get_token_service),
):
    token = token_service.request_token("slurm")
    return await slurm_service.get_slurm_job_info(job_id, token)
