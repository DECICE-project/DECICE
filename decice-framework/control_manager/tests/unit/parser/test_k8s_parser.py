import json
from parser.k8s_parser import K8sParser

import pytest

from db.models import Deployment, GenericK8sResource, Job, Workflow


@pytest.fixture
def valid_job_yaml() -> bytes:
    return b"""
apiVersion: batch/v1
kind: Job
metadata:
  name: job1
spec:
  template:
    metadata: {}
    spec:
      containers:
      - name: main
        image: busybox
        command: ["echo"]
        args: ["hello"]
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
            nvidia.com/gpu: "2"
"""


@pytest.fixture
def job_missing_gpu_yaml() -> bytes:
    return b"""
apiVersion: batch/v1
kind: Job
metadata:
  name: job2
spec:
  template:
    metadata: {}
    spec:
      containers:
      - name: main
        image: busybox
        command: ["echo"]
        args: ["world"]
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
"""


@pytest.fixture
def job_invalid_gpu_yaml() -> bytes:
    return b"""
apiVersion: batch/v1
kind: Job
metadata:
  name: job-invalid-gpu
spec:
  template:
    metadata: {}
    spec:
      containers:
      - name: main
        image: busybox
        resources:
          requests:
            nvidia.com/gpu: "invalid"
"""


@pytest.fixture
def job_no_containers_yaml() -> bytes:
    return b"""
apiVersion: batch/v1
kind: Job
metadata:
  name: job-no-containers
spec:
  template:
    metadata: {}
    spec:
      containers: []
"""


@pytest.fixture
def valid_deployment_yaml() -> bytes:
    return b"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deploy1
spec:
  replicas: 2
  template:
    metadata: {}
    spec:
      containers:
      - name: app
        image: nginx:latest
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
"""


@pytest.fixture
def deployment_multiple_containers_yaml() -> bytes:
    return b"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deploy-multi
spec:
  replicas: 1
  template:
    metadata: {}
    spec:
      containers:
      - name: first
        image: busybox
      - name: second
        image: alpine
"""


@pytest.fixture
def valid_service_yaml() -> bytes:
    return b"""
apiVersion: v1
kind: Service
metadata:
  name: svc1
spec:
  ports:
    - port: 8080
      targetPort: 80
  selector:
    app: test
"""


@pytest.fixture
def valid_namespace_yaml() -> bytes:
    return b"""
apiVersion: v1
kind: Namespace
metadata:
  name: test-namespace
"""


@pytest.fixture
def multi_doc_yaml(
    valid_job_yaml, valid_deployment_yaml, valid_service_yaml, valid_namespace_yaml
) -> bytes:
    return b"---\n".join(
        [
            valid_namespace_yaml,
            valid_service_yaml,
            valid_deployment_yaml,
            valid_job_yaml,
        ]
    )


@pytest.fixture
def argo_workflow_yaml() -> bytes:
    return b"""
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: argo-test
spec: {}
"""


@pytest.fixture
def invalid_yaml() -> bytes:
    return b"this: is not\n  - valid: yaml"


class TestK8sParser:
    def test_parse_valid_job(self, valid_job_yaml):
        parser = K8sParser()
        workflow = parser.parse(valid_job_yaml, "job.yaml")

        assert isinstance(workflow, Workflow)
        job = workflow.tasks[0]
        assert isinstance(job, Job)
        assert job.name == "job1"
        assert job.image == "busybox"
        assert json.loads(job.command_str) == ["echo", "hello"]
        assert job.required_cpu == "100m"
        assert job.required_memory == "128Mi"
        assert job.required_gpu == 2

    def test_parse_job_missing_gpu(self, job_missing_gpu_yaml):
        parser = K8sParser()
        workflow = parser.parse(job_missing_gpu_yaml, "job.yaml")
        job = workflow.tasks[0]
        assert job.required_gpu is None
        assert job.required_cpu == "50m"
        assert job.required_memory == "64Mi"

    def test_parse_job_invalid_gpu_logs_warning(self, job_invalid_gpu_yaml, caplog):
        parser = K8sParser()
        workflow = parser.parse(job_invalid_gpu_yaml, "job.yaml")
        job = workflow.tasks[0]
        # GPU is invalid, should be None
        assert job.required_gpu is None
        assert "Could not parse GPU resource" in caplog.text

    def test_parse_job_no_containers_raises_error(self, job_no_containers_yaml):
        parser = K8sParser()
        with pytest.raises(
            ValueError, match="No valid resources found in the provided YAML."
        ):
            parser.parse(job_no_containers_yaml, "job.yaml")

    def test_parse_valid_deployment(self, valid_deployment_yaml):
        parser = K8sParser()
        workflow = parser.parse(valid_deployment_yaml, "deploy.yaml")
        dep = workflow.tasks[0]
        assert isinstance(dep, Deployment)
        assert dep.name == "deploy1"
        assert dep.image == "nginx:latest"
        assert dep.replicas == 2
        assert dep.required_cpu == "200m"
        assert dep.required_memory == "256Mi"

    def test_parse_deployment_multiple_containers(
        self, deployment_multiple_containers_yaml
    ):
        parser = K8sParser()
        workflow = parser.parse(deployment_multiple_containers_yaml, "deploy.yaml")
        dep = workflow.tasks[0]
        assert isinstance(dep, Deployment)
        # Only first container is parsed
        assert dep.image == "busybox"

    def test_parse_valid_service(self, valid_service_yaml):
        parser = K8sParser()
        workflow = parser.parse(valid_service_yaml, "svc.yaml")
        svc = workflow.tasks[0]
        assert isinstance(svc, GenericK8sResource)
        assert svc.name == "svc1"
        assert "apiVersion" in svc.command_str

    # --- [FIX] Updated test expectation: Ignore Namespace ---
    def test_parse_only_ignored_resource_raises_error(self, valid_namespace_yaml):
        """Test that parsing a file containing ONLY ignored resources raises ValueError."""
        parser = K8sParser()
        # Since Namespace is in IGNORED_TYPES, this creates 0 tasks -> ValueError
        with pytest.raises(ValueError, match="No valid resources found"):
            parser.parse(valid_namespace_yaml, "ns.yaml")

    # --------------------------------------------------------

    def test_parse_multi_document(self, multi_doc_yaml):
        parser = K8sParser()
        workflow = parser.parse(multi_doc_yaml, "multi.yaml")
        assert isinstance(workflow, Workflow)

        # --- [FIX] Expect 3 tasks, not 4 (Namespace ignored) ---
        assert len(workflow.tasks) == 3

        types = [type(t) for t in workflow.tasks]
        assert GenericK8sResource in types  # Service
        assert Job in types
        assert Deployment in types

        # Verify Namespace was filtered out
        task_names = [t.name for t in workflow.tasks]
        assert "test-namespace" not in task_names
        # -------------------------------------------------------

    def test_can_parse_rejects_argo_workflow(self, argo_workflow_yaml):
        # This method returns False because we updated can_parse to skip argoproj.io
        assert not K8sParser.can_parse("workflow.yaml", argo_workflow_yaml)

    def test_parse_invalid_yaml_raises_error(self, invalid_yaml):
        parser = K8sParser()
        with pytest.raises(ValueError, match="Invalid YAML format"):
            parser.parse(invalid_yaml, "bad.yaml")
