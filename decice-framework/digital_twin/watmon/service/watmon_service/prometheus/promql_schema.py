from pydantic import BaseModel
from datetime import datetime


class UniDirectionalVertexpoolMs(BaseModel):
    vertexpool_a: str
    vertexpool_b: str
    value: float
    lastUpdated: datetime | None = None


class UniDirectionalVertexMs(BaseModel):
    vertex_a: str
    vertex_b: str
    vertex_a_device_id: int | None = None
    vertex_b_device_id: int | None = None
    value: float
    lastUpdated: datetime | None = None


class PromNode(BaseModel):
    name: str | None = None
    ip: str | None = None


class PromDevice(BaseModel):
    id: int
    name: str | None = None
    labels: list[str] = []
    ip: str | None = None


class PromVertexpool(BaseModel):
    id: int
    nodes: list[PromNode] = []
    vertexpool_labels: list[str] = []
    devices: list[PromDevice] = []
    lastUpdated: datetime | None = None


class LinkLatencyMs(BaseModel):
    self_vertexpool_id: str
    target_vertexpool_id: str
    value: float
    lastUpdated: datetime | None = None


class RawNodeLinkLatencyMs(LinkLatencyMs):
    nodename: str
    target_device_id: str | None = None
    target_name: str
    target_type: str
