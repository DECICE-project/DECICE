# models.py
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class ContainerSpec(BaseModel):
    name: str
    image: str
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    req_cpu_mcpu: Optional[int] = None
    req_mem_mib: Optional[int] = None
    lim_cpu_mcpu: Optional[int] = None
    lim_mem_mib: Optional[int] = None

class InferenceRequest(BaseModel):
    schema_version: str = Field(default="v1")
    namespace: str
    workload_kind: str  # Deployment | Job | CronJob
    workload_name: str
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    containers: List[ContainerSpec]
    init_container_count: int = 0
    sidecar_count: int = 0
    volume_types: List[str] = []
    node_type: Optional[str] = None
    runtime_class: Optional[str] = None
    gpu_count: int = 0
    # Jobs-only hints (optional)
    parallelism: Optional[int] = None
    completions: Optional[int] = None

class InferenceResponse(BaseModel):
    schema_version: str = Field(default="v1")
    pred_avg_power_w: float
    pred_total_energy_j: Optional[float] = None
    components: Optional[Dict[str, float]] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None
