import logging

from fastapi import APIRouter, Depends, status

from clients.psgc_client import PSGCClient, get_psgc_client
from schemas.jobs import SlurmEpilogResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/job_event", status_code=status.HTTP_201_CREATED)
async def get_job_status_from_slurm(
    job_info: SlurmEpilogResponse, psgc_client: PSGCClient = Depends(get_psgc_client)
):
    """
    Receives completion info from Slurm EpilogScript and forwards it to PSGC.
    """
    logger.info(
        f"Received Slurm Epilog event for job {job_info.job_id} ({job_info.job_name})"
    )

    # The payload we send to PSGC matches 'SlurmWebhookPayload' in the PSGC code
    payload = {
        "job_id": job_info.job_id,  # Slurm ID (e.g. "101")
        "job_name": job_info.job_name,  # PSGC Task Name (e.g. "psgc-task-{uuid}")
        "job_state": job_info.status,  # e.g. "COMPLETED"
        "exit_code": int(job_info.exit_code) if job_info.exit_code.isdigit() else None,
        "cluster": "slurm-cluster",  # Optional identifier
    }

    # Forward to PSGC
    await psgc_client.send_task_status_update(payload)

    return {"status": "processed"}
