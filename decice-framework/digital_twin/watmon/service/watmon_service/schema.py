from pydantic import BaseModel
from typing import Optional


class NodeInVP(BaseModel):
    nodename: str
    ip: str | None = None


class Node(NodeInVP):
    vertexpool_id: Optional[int] = None


class Label(BaseModel):
    label_key: str
    label_value: str


class DevicePatch(BaseModel):
    name: str | None = None
    labels: list[Label] | None = None
    ip: str | None = None


class NodePatch(BaseModel):
    ip: str | None = None


class DeviceInVp(BaseModel):
    id: int
    name: str
    labels: list[str] | None = None
    ip: str | None = None


class Device(DeviceInVp):
    vertexpool_id: Optional[int] = None


class DevicePost(DevicePatch):
    id: int | None = None
    name: str
    ip: str
    labels: list[Label] | None = None
    vertexpool_id: Optional[int] = None


class MoveVertex(BaseModel):
    vertex_id: str
    new_vertexpool_id: int


class VertexPool(BaseModel):
    vertexpool_id: int
    devices: list[DeviceInVp]
    nodes: list[NodeInVP]
    labels: list[str]


class VertexpoolsPost(BaseModel):
    vertexpools: list[VertexPool]
