from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth.auth import verify_internal_traffic
from services.evaluation_service import EvaluationService, get_evaluation_service

evaluation_router = APIRouter(prefix="/evaluation")


class EvaluationRequest(BaseModel):
    scheduler_name: str
    dataset_name: str


class EvaluationResponse(BaseModel):
    id: str
    status: str
    optimality_rate: float | None = None
    avg_regret: float | None = None


@evaluation_router.post(
    "/start",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_traffic)],
)
async def start_evaluation(
    req: EvaluationRequest, service: EvaluationService = Depends(get_evaluation_service)
):
    try:
        job = await service.start_evaluation(req.scheduler_name, req.dataset_name)
        return {"job_id": job.id, "status": "submitted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@evaluation_router.get("/", dependencies=[Depends(verify_internal_traffic)])
async def list_evaluations(
    service: EvaluationService = Depends(get_evaluation_service),
):
    return await service.list_jobs()


@evaluation_router.get("/{job_id}", dependencies=[Depends(verify_internal_traffic)])
async def get_evaluation(
    job_id: str, service: EvaluationService = Depends(get_evaluation_service)
):
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
