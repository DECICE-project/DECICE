import logging
from collections import defaultdict
from typing import Tuple

import pandas as pd

from .features.interfaces import INodeFeatureExtractor, ITaskFeatureExtractor
from .features.registry import FeatureRegistry
from .schemas import LatencyMatrix, ScheduleRequest

logger = logging.getLogger(__name__)


class DataTransformer:
    """
    A unified "Facade" for transforming a ScheduleRequest.

    Refactored to use 'Task' terminology instead of 'Workload'.
    """

    def __init__(
        self,
        task_registry: FeatureRegistry,
        task_feature_names: list[str],
        node_registry: FeatureRegistry,
        node_feature_names: list[str],
    ):
        # Setup for Task Transformation
        self.task_feature_names = task_feature_names
        self.task_extractors: list[ITaskFeatureExtractor] = []

        for name in self.task_feature_names:
            try:
                extractor_cls = task_registry.get_extractor_class(name)
                instance = extractor_cls()
                if not isinstance(instance, ITaskFeatureExtractor):
                    raise TypeError(f"Extractor {name} is not ITaskFeatureExtractor")
                self.task_extractors.append(instance)
            except KeyError:
                raise ValueError(f"Task feature '{name}' not found in registry.")

        # Setup for Node Transformation
        self.node_feature_names = node_feature_names
        self.node_extractors: list[INodeFeatureExtractor] = []
        for name in self.node_feature_names:
            try:
                extractor_cls = node_registry.get_extractor_class(name)
                instance = extractor_cls()
                if not isinstance(instance, INodeFeatureExtractor):
                    raise TypeError(f"Extractor {name} is not INodeFeatureExtractor")
                self.node_extractors.append(instance)
            except KeyError:
                raise ValueError(f"Node feature '{name}' not found in registry.")

    def transform(
        self, request: ScheduleRequest
    ) -> Tuple[pd.DataFrame, pd.DataFrame, LatencyMatrix]:
        """
        Transforms a ScheduleRequest into the three core data structures
        for the AI scheduler: tasks, nodes, and latencies.
        """
        # Delegate to internal methods
        tasks_df = self._transform_tasks(request)
        nodes_df = self._transform_nodes(request)
        latency_matrix = self._transform_latency_matrix(request)

        return tasks_df, nodes_df, latency_matrix

    def _transform_tasks(self, request: ScheduleRequest) -> pd.DataFrame:
        """
        Processes the request.tasks list into a "Demand" DataFrame.
        """
        data: list[dict] = []

        # Iterate over the new 'tasks' field
        for task in request.tasks:
            feature_row = {}
            for extractor in self.task_extractors:
                # Extractors must now accept 'task' argument
                feature_row[extractor.name] = extractor.extract(task, context=request)
            data.append(feature_row)

        if not data:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=self.task_feature_names)

        return pd.DataFrame(data)[self.task_feature_names]

    def _transform_nodes(self, request: ScheduleRequest) -> pd.DataFrame:
        """
        Processes the request.cluster into a flat "Supply" DataFrame of Nodes.
        """
        data: list[dict] = []
        cluster = request.cluster

        for pool in cluster.vertexpools:
            for node in pool.nodes:
                feature_row = {}
                for extractor in self.node_extractors:
                    feature_row[extractor.name] = extractor.extract(
                        node, pool, context=request
                    )
                data.append(feature_row)

        if not data:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=self.node_feature_names)

        return pd.DataFrame(data)[self.node_feature_names]

    def _transform_latency_matrix(self, request: ScheduleRequest) -> LatencyMatrix:
        """
        Converts the list of Links into a nested dict latency matrix.
        """
        matrix = defaultdict(dict)
        for link in request.cluster.links:
            matrix[link.vertexpool_a_id][link.vertexpool_b_id] = link.network_delay_ms
        return dict(matrix)
