# file: tests/unit/test_clients.py

import pytest
from unittest.mock import patch, MagicMock

from clients.kubernetes_client import KubernetesClient
from clients.slurm_client import SlurmClient


class TestKubernetesClient:
    """Unit tests for KubernetesClient."""
    
    def test_create_manager_pod_returns_pod_name(self):
        """Test that create_manager_pod returns a properly formatted pod name."""
        client = KubernetesClient()
        
        pod_name = client.create_manager_pod(
            job_name="test-job",
            image="test-image:latest",
            command=["python", "script.py"],
            job_details={"schedulerTarget": "VOLCANO"}
        )
        
        assert pod_name == "test-job-manager-pod"
        assert isinstance(pod_name, str)
    
    def test_create_manager_pod_with_special_characters(self):
        """Test pod name generation with special characters in job name."""
        client = KubernetesClient()
        
        pod_name = client.create_manager_pod(
            job_name="test_job-123",
            image="test-image:latest", 
            command=["python", "script.py"],
            job_details={}
        )
        
        assert pod_name == "test_job-123-manager-pod"


class TestSlurmClient:
    """Unit tests for SlurmClient."""
    
    def test_submit_job_via_interlink_returns_job_id(self):
        """Test that submit_job_via_interlink returns a job ID."""
        client = SlurmClient()
        
        job_id = client.submit_job_via_interlink(
            job_name="test-slurm-job",
            image="slurm-image:latest",
            command=["sbatch", "script.sh"],
            job_details={"schedulerTarget": "INTERLINK_SLURM"}
        )
        
        assert job_id == "slurm-job-12345"
        assert isinstance(job_id, str)
    
    def test_submit_job_with_different_parameters(self):
        """Test job submission with various parameters."""
        client = SlurmClient()
        
        job_id = client.submit_job_via_interlink(
            job_name="complex-job",
            image="complex-image:v2",
            command=["mpirun", "-n", "4", "app"],
            job_details={
                "schedulerTarget": "INTERLINK_SLURM",
                "resources": {"cpu": "4", "memory": "8Gi"}
            }
        )
        
        assert job_id is not None
        assert len(job_id) > 0
