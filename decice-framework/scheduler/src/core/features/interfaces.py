from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from ..schemas import LatencyMatrix, Node, ScheduleRequest, Task, VertexPool


class IFeatureExtractor(ABC):
    """
    Abstract "contract" for all feature extractors.
    Base class only defines the 'name' attribute.
    """

    name: str = ""


class ITaskFeatureExtractor(IFeatureExtractor):
    """
    Interface for features calculated *per workflow task*.
    """

    @abstractmethod
    def extract(self, task: Task, context: ScheduleRequest) -> Any:
        """Extracts a feature for a single workflow task."""
        pass


class INodeFeatureExtractor(IFeatureExtractor):
    """
    Interface for features calculated *per node* from the ClusterState.
    """

    @abstractmethod
    def extract(self, node: Node, pool: VertexPool, context: ScheduleRequest) -> Any:
        """Extracts a feature for a single node."""
        pass


class IAggregateFeatureExtractor(IFeatureExtractor):
    """
    Interface for features calculated *per deployment* by aggregating
    the workflowtask_df and nodes_df.
    """

    @abstractmethod
    def calculate(
        self,
        jobs_df: pd.DataFrame,
        nodes_df: pd.DataFrame,
        latency_matrix: LatencyMatrix,
    ) -> float:
        """Calculates a single aggregate feature value."""
        pass
