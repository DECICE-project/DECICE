from uuid import UUID

import pytest

# Import the classes to test from the new 'task' module
from core.features.task import (TaskGpuIsRequiredExtractor, TaskIdExtractor,
                                TaskRequiredCpuExtractor,
                                TaskRequiredMemoryExtractor)
# Import fixtures
from core.schemas import HardwareRequirements, ScheduleRequest, Task

# --- Test Cases ---


def test_task_id_extractor(sample_workload, sample_schedule_request):
    """
    Test extracting the task ID as a string.
    Note: 'sample_workload' fixture returns a Task object now.
    """
    extractor = TaskIdExtractor()
    assert extractor.name == "task_id"
    result = extractor.extract(sample_workload, sample_schedule_request)
    assert isinstance(result, str)
    assert result == str(sample_workload.id)


def test_task_required_cpu_extractor(sample_workload, sample_schedule_request):
    """Test extracting required CPU."""
    extractor = TaskRequiredCpuExtractor()
    assert extractor.name == "required_cpu"
    result = extractor.extract(sample_workload, sample_schedule_request)
    assert result == sample_workload.requirements.required_cpu
    assert result == 2  # Based on fixture


def test_task_required_memory_extractor(sample_workload, sample_schedule_request):
    """Test extracting required memory."""
    extractor = TaskRequiredMemoryExtractor()
    assert extractor.name == "required_memory"
    result = extractor.extract(sample_workload, sample_schedule_request)
    assert result == sample_workload.requirements.required_memory
    assert result == 4096  # Based on fixture


def test_task_gpu_is_required_extractor(sample_schedule_request):
    """Test extracting GPU requirement flag."""
    extractor = TaskGpuIsRequiredExtractor()
    assert extractor.name == "gpu_is_required"

    # Test case 1: No GPU required (from sample_workload fixture in conftest)
    task_no_gpu = sample_schedule_request.tasks[0]
    result_no_gpu = extractor.extract(task_no_gpu, sample_schedule_request)
    assert result_no_gpu == 0

    # Test case 2: GPU required (second task in sample_schedule_request fixture)
    task_with_gpu = sample_schedule_request.tasks[1]
    result_with_gpu = extractor.extract(task_with_gpu, sample_schedule_request)
    assert result_with_gpu == 1

    # Test case 3: GPU field explicitly None
    req_none_gpu = HardwareRequirements(
        required_cpu=1, required_memory=1024, required_gpu=None
    )
    task_none_gpu = Task(
        id=UUID("11111111-1111-1111-1111-111111111111"), requirements=req_none_gpu
    )
    result_none_gpu = extractor.extract(task_none_gpu, sample_schedule_request)
    assert result_none_gpu == 0
