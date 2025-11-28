# async tasks that export vertexpool metrics
from watmon_service.db.vertexpool import VertexpoolManager
from watmon_service.db.session import session_generate
from watmon_service.prometheus.metrics import (
    DECICE_DEVICE_INFO,
    DECICE_DEVICE_LABELS,
    DECICE_VERTEXPOOL_LABELS,
    DECICE_NODE_INFO,
)
import asyncio
import json


class MetricUpdater:
    def __init__(self) -> None:
        self.vertexpool_manager = VertexpoolManager(session_manager=session_generate)

    async def update_vertexpools(self):
        vertexpools = await self.vertexpool_manager.get_vertexpools()
        DECICE_VERTEXPOOL_LABELS.clear()
        for vertexpool in vertexpools:
            vertexpool_labels = {}
            for label in vertexpool.labels:
                vertexpool_labels[label.key] = label.value
            if vertexpool_labels:
                labels = json.dumps(vertexpool_labels)
            else:
                labels = ""

            DECICE_VERTEXPOOL_LABELS.labels(
                vertexpool_id=vertexpool.id, vertexpool_labels=labels
            ).set(1.0)

    async def update_devices(self):
        devices = await self.vertexpool_manager.get_devices()
        DECICE_DEVICE_LABELS.clear()
        DECICE_DEVICE_INFO.clear()
        for device in devices:
            DECICE_DEVICE_INFO.labels(
                device_id=device.device_id,
                devicename=device.devicename,
                device_ip=device.ip,
                vertexpool_id=device.vertexpool_id,
            ).set(1)

            device_labels = {}
            for label in device.labels:
                device_labels[label.key] = label.value
            if device_labels:
                labels = json.dumps(device_labels)
            else:
                labels = ""

            DECICE_DEVICE_LABELS.labels(
                device_id=device.device_id, device_labels=labels
            ).set(1)

    async def update_nodes(self):
        nodes = await self.vertexpool_manager.get_nodes()
        DECICE_NODE_INFO.clear()
        for node in nodes:
            DECICE_NODE_INFO.labels(
                nodename=node.nodename,
                node_ip=node.ip,
                vertexpool_id=node.vertexpool_id,
            ).set(1)

    async def update_metrics(self):
        await self.update_devices()
        await self.update_vertexpools()
        await self.update_nodes()

    async def run(self, update_interval_seconds: int = 3):
        while True:
            await self.update_metrics()
            await asyncio.sleep(update_interval_seconds)
