from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


##########################
# Client Request From PSGC
##########################
class SlurmClientRequest(BaseModel):
    username: str
    work_dir: str
    slurm_file_content: str
    task_id: UUID


#######################################
# SLURM DATA CLASSES FOR JOB SUBMISSION
#######################################
class SlurmJobSpec(BaseModel):
    script: str
    name: Optional[str]
    current_working_directory: Optional[str]
    environment: Optional[list[str]] = []


class SlurmJobSubmitRequest(BaseModel):
    jobs: list[SlurmJobSpec]


class SlurmMeta(BaseModel):
    slurm: Optional[dict[str, Any]] = None
    plugin: Optional[dict[str, Any]] = None
    client: Optional[dict[str, Any]] = None
    command: Optional[list[str]] = None


class SlurmJobSubmitResponse(BaseModel):
    job_id: Optional[int] = None
    step_id: Optional[str] = None
    job_submit_user_msg: Optional[str] = None
    meta: Optional[SlurmMeta] = None
    warnings: Optional[list[dict[str, Any]]] = None
    errors: Optional[list[dict[str, Any]]] = None


####################################
# SLURM DATA CLASSES FOR GET REQUEST
####################################
class SlurmJob(BaseModel):
    job_id: int
    name: str
    user: str
    account: str
    exit_code: list[str]
    state: dict[str, Any]
    working_directory: str

    # transform exit_code
    @field_validator("exit_code", mode="before")
    def extract_exit_status(cls, v):
        if isinstance(v, dict) and "status" in v:
            return v["status"]
        return v

    # transform state
    @field_validator("state", mode="before")
    def extract_state(cls, v):
        if isinstance(v, dict):
            return {"current": v.get("current"), "reason": v.get("reason")}
        return v


class SlurmWarning(BaseModel):
    description: Optional[str] = None
    source: Optional[str] = None


class SlurmResponse(BaseModel):
    jobs: list[SlurmJob]
    meta: SlurmMeta
    errors: list
    warnings: list[dict[str, Any]]


#############################################################
# Slurm Job Status update Response coming from Epilog scripts
#############################################################
class SlurmEpilogResponse(BaseModel):
    job_id: str
    username: str
    job_name: str
    status: str
    exit_code: str
