from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class MeasuremtnStrategy(str, Enum):
    ROUND_ROBIN = "round-robin"


class NodeInVP(BaseModel):
    nodename: str
    ip: str | None = None


class Node(NodeInVP):
    vertexpool_id: Optional[int] = None


class Label(BaseModel):
    label_key: str
    label_value: str


class DeviceInVp(BaseModel):
    id: int
    name: str
    labels: list[str] | None = None
    ip: str | None = None


class Device(DeviceInVp):
    vertexpool_id: Optional[int] = None


class MoveVertex(BaseModel):
    vertex_id: str
    new_vertexpool_id: int


class VertexPool(BaseModel):
    vertexpool_id: int
    devices: list[DeviceInVp]
    nodes: list[NodeInVP]
    labels: list[str]


class ExporterSettings(BaseModel):
    measure_self_pool: bool | None = True
    self_pool_measurement_interval_seconds: float | None = 30
    vertexpool_measurement_interval_seconds: float | None = 5
    measurement_stratagy: MeasuremtnStrategy | None = MeasuremtnStrategy.ROUND_ROBIN


class VertexpoolsPost(BaseModel):
    vertexpools: list[VertexPool]
    settings: ExporterSettings | None = ExporterSettings()


### Current ping schema of promql query
class PingMetrics(BaseModel):
    __name__: str
    endpoint: str
    instance: str
    job: str
    namespace: str
    nodename: str  # used in Link
    pod: str
    service: str
    self_vertex_id: str  # used in Link
    targetIP: str
    target_vertex_id: str  # used in Link
    target_type: str  # used in Link
    targetname: str  # used in Link
    ping_value: float  # used in Link
    timestamp: datetime  # used in Link
