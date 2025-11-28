from typing import List, Dict
from pydantic import BaseModel


class UtilStats(BaseModel):
    mean: float
    stdev: float


class MetricsEmu(BaseModel):
    util: UtilStats
    cpu_cores: float
    mem_total: float
    total_disk_gb: float
    free_disk_gb: float
    network_bandwidth_mbps: float
    power_factor: float = 1.0


class NodeEmu(BaseModel):
    name: str
    metrics: MetricsEmu
    node_info: Dict[str, str] | None = None


class DeviceEmu(BaseModel):
    id: str
    name: str
    labels: Dict[str, str]
    device_info: Dict[str, str] | None = None


class VertexPoolEmu(BaseModel):
    id: str
    vertexpool_labels: Dict[str, str]
    nodes: List[NodeEmu]
    devices: List[DeviceEmu]


class NetworkDelay(BaseModel):
    mean: float
    stdev: float


class LinkEmu(BaseModel):
    vertexpool_a_id: str
    vertexpool_b_id: str
    network_delay_ms: NetworkDelay


class GraphSchema(BaseModel):
    vertexpools: List[VertexPoolEmu]
    links: List[LinkEmu]
