from typing import List

from pydantic.type_adapter import TypeAdapter

from models.models import Node


def normalize(value, min_value, max_value):
    normalized_value = (
        (value - min_value) / (max_value - min_value) if max_value != min_value else 0
    )
    return normalized_value


def compute_score(node: Node) -> float:
    cpu_usage = node.metrics.util
    memory_usage = node.metrics.mem_util
    network_bandwidth = node.metrics.network_bandwidth_mbps

    normalized_cpu = normalize(cpu_usage, 0, 100)
    normalized_memory = normalize(memory_usage, 0, 100)
    normalized_network = normalize(network_bandwidth, 0, 1000)

    cpu_weight = 0.4
    memory_weight = 0.4
    network_weight = 0.2

    score = (
        1
        - (normalized_cpu * cpu_weight)
        + (normalized_memory * memory_weight)
        + (normalized_network * network_weight)
    )
    return score


extract_nodes = TypeAdapter(List[Node])
