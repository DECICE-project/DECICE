from parser.argo_parser import ArgoYAMLParser

import pytest

from db.models import Workflow


@pytest.fixture
def valid_argo_workflow_yaml() -> bytes:
    """Provides a valid Argo Workflow with a simple A -> B dependency."""
    return b"""
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: argo-test-
  annotations:
    dev.decice.com/storage-request: "10Gi"
spec:
  entrypoint: main-dag
  templates:
  - name: task-a-template
    container:
      image: alpine:3.7
      command: [echo, "Hello from A"]
      resources:
        requests:
          cpu: "100m"
  - name: task-b-template
    container:
      image: alpine:3.7
      command: [echo, "Hello from B"]
  - name: main-dag
    dag:
      tasks:
      - name: task-a
        template: task-a-template
      - name: task-b
        template: task-b-template
        dependencies: [task-a]
"""


@pytest.fixture
def argo_workflow_with_loop_yaml() -> bytes:
    """Provides an Argo Workflow with a `withItems` fan-out task."""
    return b"""
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: argo-loop-test-
  annotations:
    dev.decice.com/storage-request: "20Gi"
spec:
  entrypoint: main-dag
  templates:
  - name: fan-out-task
    container:
      image: debian:9.5
  - name: fan-in-task
    container:
      image: alpine:3.7
      command: [echo, "Done"]
  - name: main-dag
    dag:
      tasks:
      - name: generate-items
        template: fan-out-task
        withItems:
          - { message: "hello" }
          - { message: "world" }
      - name: consume-items
        template: fan-in-task
        dependencies: [generate-items]
"""


@pytest.fixture
def yaml_missing_top_level_annotation() -> bytes:
    """Provides an Argo Workflow missing the required top-level annotation."""
    return b"""
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: argo-bad-
spec:
  entrypoint: main-dag
  templates:
  - name: some-template
    container:
      image: alpine:3.7
  - name: main-dag
    dag:
      tasks:
      - name: some-task
        template: some-template
"""


class TestArgoYAMLParser:
    """Test suite for the ArgoYAMLParser."""

    def test_parse_valid_workflow_and_dependencies(
        self, valid_argo_workflow_yaml: bytes
    ):
        """
        GIVEN a valid Argo Workflow with an A -> B dependency
        WHEN the parser's parse method is called
        THEN it should create a Workflow with two tasks where task B depends on task A.
        """
        parser = ArgoYAMLParser()

        workflow = parser.parse(
            file_content_bytes=valid_argo_workflow_yaml, filename="argo.yaml"
        )

        assert isinstance(workflow, Workflow)
        assert workflow.name.startswith("argo-test-")
        assert len(workflow.tasks) == 2

        tasks_by_name = {task.name: task for task in workflow.tasks}
        assert "task-a" in tasks_by_name
        assert "task-b" in tasks_by_name

        task_a = tasks_by_name["task-a"]
        task_b = tasks_by_name["task-b"]

        assert task_a.image == "alpine:3.7"
        assert task_a.required_cpu == "100m"
        assert len(task_a.dependencies) == 0

        assert task_b.image == "alpine:3.7"
        assert len(task_b.dependencies) == 1
        assert task_a in task_b.dependencies

    def test_parse_with_items_loop(self, argo_workflow_with_loop_yaml: bytes):
        """
        GIVEN an Argo Workflow with a `withItems` task that creates two items
        WHEN the parser's parse method is called
        THEN it should create two tasks for the looped task, and a third task that depends on both.
        """
        parser = ArgoYAMLParser()

        workflow = parser.parse(
            file_content_bytes=argo_workflow_with_loop_yaml, filename="argo.yaml"
        )

        assert isinstance(workflow, Workflow)
        assert len(workflow.tasks) == 3

        tasks_by_name = {task.name: task for task in workflow.tasks}

        assert "generate-items-0" in tasks_by_name
        assert "generate-items-1" in tasks_by_name
        assert "consume-items" in tasks_by_name

        looped_task_0 = tasks_by_name["generate-items-0"]
        looped_task_1 = tasks_by_name["generate-items-1"]
        consumer_task = tasks_by_name["consume-items"]

        assert len(consumer_task.dependencies) == 2
        assert looped_task_0 in consumer_task.dependencies
        assert looped_task_1 in consumer_task.dependencies

    def test_parse_raises_error_on_missing_annotation(
        self, yaml_missing_top_level_annotation: bytes
    ):
        """
        GIVEN an Argo Workflow YAML missing the required top-level annotation
        WHEN the parse method is called
        THEN a ValueError should be raised.
        """
        parser = ArgoYAMLParser()

        with pytest.raises(
            ValueError,
            match="A 'dev.decice.com/storage-request' annotation is required",
        ):
            parser.parse(
                file_content_bytes=yaml_missing_top_level_annotation,
                filename="argo.yaml",
            )

    def test_parse_raises_error_on_missing_entrypoint(self):
        """
        GIVEN an Argo Workflow YAML missing the `spec.entrypoint` field
        WHEN the parse method is called
        THEN a ValueError should be raised.
        """
        yaml_content = b"""
          apiVersion: argoproj.io/v1alpha1
          kind: Workflow
          metadata:
            annotations:
              dev.decice.com/storage-request: "1Gi"
          spec:
            templates: [] # No entrypoint defined
          """
        parser = ArgoYAMLParser()

        with pytest.raises(ValueError, match="Argo Workflow must have an 'entrypoint'"):
            parser.parse(file_content_bytes=yaml_content, filename="argo.yaml")
