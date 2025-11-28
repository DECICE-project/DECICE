# file: app.py

from fastapi import FastAPI, HTTPException, status, Depends, Request
from typing import List, Optional
from uuid import UUID
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from datetime import datetime

# Import all necessary components from other layers
from schemas import (
    JobSubmissionSchema, 
    JobStatusSchema, 
    JobListSchema, 
    JobState, 
    ClusterType
)
from repository.unit_of_work import UnitOfWork
from services.scheduler_service import SchedulerService
from services.exceptions import JobNotFoundError
from clients.kubernetes_client import KubernetesClient
from clients.slurm_client import SlurmClient
from clients.prometheus_metrics_client import PrometheusMetricsClient, IntelligentSchedulerService

# --- Logging Configuration ---
# In a real app, this would be more sophisticated (e.g., loaded from a file)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="DECICE HPC Meta-Scheduler API (Production)",
    version="0.1.0",
    # The openapi spec is loaded via the override below
)

# --- OpenAPI Specification Override ---
import yaml
from pathlib import Path

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    spec_path = Path(__file__).parent / "openapi.yaml"
    try:
        with spec_path.open("r") as f:
            openapi_schema = yaml.safe_load(f)
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    except FileNotFoundError:
        # 如果找不到 openapi.yaml，使用默认的自动生成的 schema
        from fastapi.openapi.utils import get_openapi
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description="DECICE HPC Meta-Scheduler API",
            routes=app.routes,
        )
        app.openapi_schema = openapi_schema
        return app.openapi_schema

app.openapi = custom_openapi

# --- Dependency Injection Setup ---
# Here we define how to create instances of our clients.
# In a real app, these might have more complex initialization (e.g., loading config).
def get_kubernetes_client():
    return KubernetesClient()

def get_slurm_client():
    return SlurmClient()

def get_prometheus_client():
    return PrometheusMetricsClient()

def get_intelligent_scheduler():
    prometheus_client = get_prometheus_client()
    return IntelligentSchedulerService(prometheus_client)

# --- Security ---
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    # Placeholder for real JWT validation logic
    if credentials:
        # In production: decode and validate token, return 'sub' claim
        return "user-123-prod"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Bearer token is missing or invalid",
    )

# --- API Endpoints (Route Handlers) ---
# Each endpoint now uses the Unit of Work pattern to ensure transactional integrity.

@app.post(
    "/jobs",
    response_model=JobStatusSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a New Job",
    tags=["Jobs"],
)
async def submit_job(
    submission: JobSubmissionSchema,
    request: Request, # FastAPI can inject the request object
    current_user_id: str = Depends(get_current_user)
):
    """
    Integrates all layers to submit a job.
    1. Opens a Unit of Work to manage the transaction.
    2. Instantiates and injects dependencies into the service layer.
    3. Calls the service layer to execute business logic.
    4. Commits the transaction if successful.
    """
    logger.info(f"User '{current_user_id}' submitting job '{submission.name}'")
    try:
        with UnitOfWork() as uow:
            scheduler_service = SchedulerService(
                job_repository=uow.jobs,
                kubernetes_client=get_kubernetes_client(),
                slurm_client=get_slurm_client(),
                intelligent_scheduler=get_intelligent_scheduler()
            )
            
            # The service layer now handles the core logic with intelligent scheduling
            new_job_domain_model = await scheduler_service.submit_job(
                submission_data=submission.model_dump(),
                user_id=current_user_id
            )
            
            # The transaction is committed here if all above operations succeed
            uow.commit()

            # The response_model will automatically convert the domain model (if it's Pydantic-compatible)
            # or a dictionary representation into the final JSON response.
            return new_job_domain_model

    except Exception as e:
        logger.error(f"Failed to submit job for user '{current_user_id}': {e}", exc_info=True)
        # The Unit of Work's __exit__ method will automatically handle the rollback.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while submitting the job."
        )

@app.get(
    "/metrics/schedulers",
    summary="Get All Scheduler Metrics",
    tags=["Monitoring"],
)
async def get_scheduler_metrics(
    current_user_id: str = Depends(get_current_user)
):
    """
    Get real-time metrics for all schedulers (Volcano and HPC) from Prometheus
    """
    try:
        intelligent_scheduler = get_intelligent_scheduler()
        metrics = await intelligent_scheduler.get_cluster_status_summary()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get scheduler metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scheduler metrics"
        )

@app.get(
    "/metrics/recommendation",
    summary="Get Scheduling Recommendation",
    tags=["Monitoring"],
)
async def get_scheduling_recommendation(
    scheduler_target: str = "AUTO",
    current_user_id: str = Depends(get_current_user)
):
    """
    Get intelligent scheduling recommendation based on current cluster loads
    """
    try:
        intelligent_scheduler = get_intelligent_scheduler()
        job_data = {"schedulerTarget": scheduler_target}
        recommendation = await intelligent_scheduler.get_scheduling_recommendation(job_data)
        
        # Also get detailed metrics for context
        metrics = await intelligent_scheduler.prometheus_client.get_all_scheduler_metrics()
        
        # Get detailed decision factors for transparency
        volcano_metrics = metrics.get("volcano", {})
        hpc_metrics = metrics.get("hpc", {})
        
        # Calculate load scores using the same algorithm
        decision_factors = intelligent_scheduler._analyze_scheduling_factors(volcano_metrics, hpc_metrics)
        
        return {
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat(),
            "decision_factors": {
                "volcano_load_score": decision_factors.get("volcano_load_score", 0),
                "hpc_load_score": decision_factors.get("hpc_load_score", 0),
                "load_difference": decision_factors.get("load_difference", 0),
                "decision_reason": decision_factors.get("decision_reason", ""),
                "detailed_reasons": decision_factors.get("reasons", [])
            },
            "metrics_summary": {
                "volcano": {
                    "cluster_cpu_percent": volcano_metrics.get("cluster_cpu_percent", 0),
                    "cluster_memory_percent": volcano_metrics.get("cluster_memory_percent", 0),
                    "queue_jobs": volcano_metrics.get("queue_jobs", 0)
                },
                "hpc": {
                    "utilization_percent": hpc_metrics.get("utilization_percent", 0),
                    "capacity_score": hpc_metrics.get("capacity_score", 0),
                    "jobs_pending": hpc_metrics.get("jobs_pending", 0),
                    "nodes_available": hpc_metrics.get("nodes_available", 0),
                    "nodes_total": hpc_metrics.get("nodes_total", 0)
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get scheduling recommendation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get scheduling recommendation"
        )

@app.get(
    "/health",
    summary="Health Check",
    tags=["System"],
)
async def health_check():
    """
    Public health check endpoint (no authentication required)
    Used by Kubernetes probes and monitoring systems
    """
    return {
        "status": "healthy",
        "service": "decice-metascheduler",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }

@app.get(
    "/metrics/load-comparison",
    summary="Get Detailed Load Comparison",
    tags=["Monitoring"],
)
async def get_load_comparison(
    current_user_id: str = Depends(get_current_user)
):
    """
    Get detailed load comparison between Volcano and HPC clusters
    for debugging and analysis purposes
    """
    try:
        intelligent_scheduler = get_intelligent_scheduler()
        metrics = await intelligent_scheduler.prometheus_client.get_all_scheduler_metrics()
        
        volcano_metrics = metrics.get("volcano", {})
        hpc_metrics = metrics.get("hpc", {})
        
        # Calculate detailed analysis
        decision_factors = intelligent_scheduler._analyze_scheduling_factors(volcano_metrics, hpc_metrics)
        
        # Calculate individual load scores
        volcano_load_score = intelligent_scheduler._calculate_volcano_load_score(volcano_metrics)
        hpc_load_score = intelligent_scheduler._calculate_hpc_load_score(hpc_metrics)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "load_analysis": {
                "volcano_load_score": volcano_load_score,
                "hpc_load_score": hpc_load_score,
                "load_difference": abs(volcano_load_score - hpc_load_score),
                "recommended_scheduler": "HPC" if hpc_load_score < volcano_load_score and abs(volcano_load_score - hpc_load_score) > 15 else "VOLCANO",
                "decision_threshold": 15,
                "decision_logic": "Switch to less loaded scheduler only if difference > 15 points"
            },
            "detailed_breakdown": {
                "volcano": {
                    "raw_metrics": {
                        "cpu_percent": volcano_metrics.get("cluster_cpu_percent", 0),
                        "memory_percent": volcano_metrics.get("cluster_memory_percent", 0),
                        "queue_jobs": volcano_metrics.get("queue_jobs", 0)
                    },
                    "load_components": {
                        "cpu_load": min(volcano_metrics.get("cluster_cpu_percent", 0), 100.0) * 0.4,
                        "memory_load": min(volcano_metrics.get("cluster_memory_percent", 0), 100.0) * 0.4,
                        "queue_load": min(volcano_metrics.get("queue_jobs", 0) * 10, 100.0) * 0.2
                    }
                },
                "hpc": {
                    "raw_metrics": {
                        "utilization_percent": hpc_metrics.get("utilization_percent", 0),
                        "jobs_pending": hpc_metrics.get("jobs_pending", 0),
                        "nodes_available": hpc_metrics.get("nodes_available", 0),
                        "nodes_total": hpc_metrics.get("nodes_total", 0)
                    },
                    "load_components": {
                        "utilization_load": min(hpc_metrics.get("utilization_percent", 0), 100.0) * 0.5,
                        "queue_pressure": min(hpc_metrics.get("jobs_pending", 0) * 15, 100.0) * 0.3,
                        "node_availability_load": (1.0 - (hpc_metrics.get("nodes_available", 0) / max(hpc_metrics.get("nodes_total", 1), 1))) * 100.0 * 0.2
                    }
                }
            },
            "decision_factors": decision_factors
        }
    except Exception as e:
        logger.error(f"Failed to get load comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get load comparison"
        )

@app.get(
    "/jobs/{jobId}",
    response_model=JobStatusSchema,
    summary="Get Job Status",
    tags=["Jobs"],
)
def get_job_status(jobId: UUID, current_user_id: str = Depends(get_current_user)):
    """
    Integrates all layers to retrieve a single job's status.
    It uses the Unit of Work for session management and handles business exceptions.
    """
    try:
        with UnitOfWork() as uow:
            scheduler_service = SchedulerService(
                job_repository=uow.jobs,
                kubernetes_client=get_kubernetes_client(),
                slurm_client=get_slurm_client()
            )
            job = scheduler_service.get_job(job_id=jobId, user_id=current_user_id)
            return job
            
    except JobNotFoundError:
        # Translate the business exception into a specific HTTP error.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    except Exception as e:
        logger.error(f"Failed to retrieve job '{jobId}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )

@app.get(
    "/jobs",
    response_model=JobListSchema,
    summary="List My Jobs",
    tags=["Jobs"],
)
def list_my_jobs(
    status: Optional[JobState] = None,
    name: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user_id: str = Depends(get_current_user)
):
    """
    Integrates all layers to list jobs with filtering and pagination.
    """
    try:
        with UnitOfWork() as uow:
            scheduler_service = SchedulerService(
                job_repository=uow.jobs,
                kubernetes_client=get_kubernetes_client(),
                slurm_client=get_slurm_client()
            )
            jobs, total = scheduler_service.list_jobs(
                user_id=current_user_id,
                limit=limit,
                offset=offset,
                status=status,
                name=name
            )
            return {"total": total, "jobs": jobs}
            
    except Exception as e:
        logger.error(f"Failed to list jobs for user '{current_user_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )