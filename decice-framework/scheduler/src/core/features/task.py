from typing import Any

from ..schemas import ScheduleRequest, Task
from . import task_feature_registry
from .interfaces import ITaskFeatureExtractor


@task_feature_registry.register()
class TaskIdExtractor(ITaskFeatureExtractor):
    name = "task_id"

    def extract(self, task: Task, context: ScheduleRequest) -> Any:
        return str(task.id)


@task_feature_registry.register()
class TaskRequiredCpuExtractor(ITaskFeatureExtractor):
    name = "required_cpu"

    def extract(self, task: Task, context: ScheduleRequest) -> Any:
        return task.requirements.required_cpu


@task_feature_registry.register()
class TaskRequiredMemoryExtractor(ITaskFeatureExtractor):
    name = "required_memory"

    def extract(self, task: Task, context: ScheduleRequest) -> Any:
        return task.requirements.required_memory


@task_feature_registry.register()
class TaskGpuIsRequiredExtractor(ITaskFeatureExtractor):
    name = "gpu_is_required"

    def extract(self, task: Task, context: ScheduleRequest) -> Any:
        return 1 if task.requirements.required_gpu is not None else 0
