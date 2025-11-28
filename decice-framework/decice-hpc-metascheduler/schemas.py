# file: schemas.py

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


# --- Enumerations ---

class ClusterType(str, Enum):
    VOLCANO = "VOLCANO"
    INTERLINK_SLURM = "INTERLINK_SLURM"
    AUTO = "AUTO"  # Intelligent scheduling based on cluster load


class JobState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


# --- Pydantic Models (Schemas) ---

class JobSubmissionSchema(BaseModel):
    """
    Defines the essential properties of a job for submission.
    Corresponds to the JobSubmissionSchema in the OpenAPI specification.
    """
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., json_schema_extra={"example": "my-first-simulation"})
    image: str = Field(..., json_schema_extra={"example": "my-registry/my-app:1.0"})
    schedulerTarget: ClusterType


class JobStatusSchema(BaseModel):
    """
    Represents the current status and details of a job.
    Corresponds to the JobStatusSchema in the OpenAPI specification.
    """
    model_config = ConfigDict(extra="forbid")
    
    jobId: UUID
    name: str
    status: JobState
    targetCluster: ClusterType
    creationTimestamp: datetime
    # This internal field is used for ownership checks and excluded from API responses.
    userId: str = Field(exclude=True)


class JobListSchema(BaseModel):
    """
    A paginated list of jobs.
    Corresponds to the JobListSchema in the OpenAPI specification.
    """
    model_config = ConfigDict(extra="forbid")
    
    total: int
    jobs: List[JobStatusSchema]

class PlacementSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cluster: Optional[ClusterType] = Field(None, description="...")