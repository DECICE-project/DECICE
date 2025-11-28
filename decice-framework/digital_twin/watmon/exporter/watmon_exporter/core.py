from pydantic import BaseModel
from datetime import datetime
from watmon_exporter.schema import VertexPool, ExporterSettings, VertexpoolsPost
from watmon_exporter.metrics import (
    PING_ATTEMPS_COUNT,
    PING_LATENCY,
    PING_SUCCESS_COUNT,
    PING_FAIL_COUNT,
)
from asyncio import create_task, sleep, get_running_loop
from concurrent.futures import ThreadPoolExecutor
from pythonping import ping
from functools import partial


class PingAttempt(BaseModel):
    nodename: str  # used in Link
    self_vertex_id: int  # used in Link
    target_ip: str
    target_vertex_id: int  # used in Link
    target_type: str | None = None  # used in Link
    target_name: str  # used in Link
    target_device_id: int | str


class PingResult(PingAttempt):
    ping_success: bool
    ping_value_ms: float  # used in Link
    timestamp: datetime = datetime.utcnow()  # used in Link


class Exporter:
    def __init__(self, nodename) -> None:
        # nodes current vertexpool and nodename
        self.nodename = nodename
        self.vertexpool_id = None

        self.settings: ExporterSettings = None
        self.vertexpools: list[VertexPool] = None
        self.current_device_ids: set[int] = (
            set()
        )  # at every update cycle also repopulate
        self.current_nodenames: set[str] = (
            set()
        )  # at every update cycle also repopulate
        self.current_vertexpool_ids: set[int] = (
            set()
        )  # at every update cycle also repopulate

        self.ip_to_ping_attemp_dict: dict[
            str, PingAttempt
        ] = {}  # maps ip addresses to PingAttempt
        self.next_target: dict[int, dict] = {}  # maps vertexpool_id to target_ip list

        self.last_self_vertexpool_attempt = datetime.now()
        self.last_vertexpool_attempt = datetime.now()
        self._run = False

        # last_device_labels_example = {
        #     1: ["venit-imac", "device", "dome_intersection", 1]
        # }
        # last_target_node_example = {"ws2": ["venit-imac", "node", "ws2", ""]}
        # when target node/device is no longer in the self.current_devices , remove the metric then delete the key
        self.last_device_labels: dict[int, list] = {}
        self.last_node_labels: dict[str, list] = {}

    def _get_all_ips_in_vertexpool(self, vertexpool: VertexPool) -> list[str]:
        all_ips = []
        for node in vertexpool.nodes:
            if node.ip:
                all_ips.append(node.ip)
        for device in vertexpool.devices:
            if device.ip:
                all_ips.append(device.ip)
        return all_ips

    def update_vertexpools(self, vertexpools_post: VertexpoolsPost):
        self.settings = vertexpools_post.settings
        self.vertexpools = vertexpools_post.vertexpools
        self._update_self_vertexpool_id()
        self._update_ping_targets()
        self._deleted_orphaned_entities()
        if not self._run:
            self._run = True
            create_task(self._start())

    def _update_self_vertexpool_id(self):
        for vp in self.vertexpools:
            for node in vp.nodes:
                if node.nodename == self.nodename:
                    self.vertexpool_id = vp.vertexpool_id
                    return
        print(f"Could not find nodename:{self.nodename} in vertexpools")

    def _update_ping_targets(
        self,
    ):
        """updates ip_to_ping_attemp_dict , next_target dictionaries and current id/nodename sets"""
        fresh_vertexpool_ids: set[int] = set()
        fresh_device_ids: set[int] = set()
        fresh_nodenames: set[str] = set()
        for vp in self.vertexpools:
            fresh_vertexpool_ids.add(vp.vertexpool_id)
            for device in vp.devices:
                fresh_device_ids.add(device.id)
                self.ip_to_ping_attemp_dict[device.ip] = PingAttempt(
                    nodename=self.nodename,
                    self_vertex_id=self.vertexpool_id,
                    target_ip=device.ip,
                    target_vertex_id=vp.vertexpool_id,
                    target_type="device",
                    target_name=device.name,
                    target_device_id=device.id,
                )
            for node in vp.nodes:
                fresh_nodenames.add(node.nodename)
                self.ip_to_ping_attemp_dict[node.ip] = PingAttempt(
                    nodename=self.nodename,
                    self_vertex_id=self.vertexpool_id,
                    target_ip=node.ip,
                    target_vertex_id=vp.vertexpool_id,
                    target_type="node",
                    target_name=node.nodename,
                    target_device_id="",
                )
            self._update_next_target_dict(vp)
        self.current_vertexpool_ids = fresh_vertexpool_ids
        self.current_device_ids = fresh_device_ids
        self.current_nodenames = fresh_nodenames

    def _deleted_orphaned_entities(self):
        "deletes no longer valid metric labels and dictionary keys"
        # delete orphaned vertexpools from
        orphaned_vertexpool_ids = set()
        for key, val in self.next_target.items():
            if key not in self.current_vertexpool_ids:
                orphaned_vertexpool_ids.add(key)  # vertexpool_id is no longer valid
        for key in orphaned_vertexpool_ids:
            del self.next_target[key]  # deleted orphaned vertexpool_id targets

        # delete orphaned metrics (node or device no longer exists in any vertexpool)
        orphaned_device_ids = set()
        for dev_id, labels in self.last_device_labels.items():
            if dev_id not in self.current_device_ids:
                PING_LATENCY.remove(*labels)  # wipe the metric from endpoint
                orphaned_device_ids.add(dev_id)
        for key in orphaned_device_ids:
            del self.last_device_labels[key]

        orphaned_nodenames = set()
        for nodename, labels in self.last_node_labels.items():
            if nodename not in self.current_nodenames:
                PING_LATENCY.remove(*labels)  # wipe the metric from endpoint
                orphaned_nodenames.add(nodename)
        for key in orphaned_nodenames:
            del self.last_node_labels[key]

    def _update_next_target_dict(self, vertexpool: VertexPool):
        if vertexpool.vertexpool_id in self.next_target:
            if set(self.next_target[vertexpool.vertexpool_id]["target_ips"]) == set(
                self._get_all_ips_in_vertexpool(vertexpool)
            ):
                print(
                    f"Targets in vertexpool {vertexpool.vertexpool_id} are not updated"
                )
                return

        self.next_target[vertexpool.vertexpool_id] = {
            "target_ips": self._get_all_ips_in_vertexpool(vertexpool),
            "next_target_index": 0,
        }
        print(f"Updated vertexpool {vertexpool.vertexpool_id}'s targets")

    async def is_time_self_vertexpool_measurement(self):
        if (
            datetime.now() - self.last_self_vertexpool_attempt
        ).total_seconds() > self.settings.self_pool_measurement_interval_seconds:
            self.last_self_vertexpool_attempt = datetime.now()
            await self.round_robin_ping_create_tasks(other_vetexpools=False)
            return True
        return False

    async def is_time_vertexpool_measurement(self):
        if (
            datetime.now() - self.last_vertexpool_attempt
        ).total_seconds() > self.settings.vertexpool_measurement_interval_seconds:
            self.last_vertexpool_attempt = datetime.now()
            await self.round_robin_ping_create_tasks(other_vetexpools=True)
            return True
        return False

    async def round_robin_ping_create_tasks(self, other_vetexpools):
        for vertexpool_id, target_dict in self.next_target.items():
            if other_vetexpools and (vertexpool_id == self.vertexpool_id):
                continue
            if not other_vetexpools and (vertexpool_id != self.vertexpool_id):
                continue
            try:
                if target_dict.get("target_ips"):
                    target_dict["next_target_index"] += 1
                    target_ip = target_dict["target_ips"][
                        target_dict["next_target_index"]
                    ]
            except IndexError:
                target_dict["next_target_index"] = 0
                target_ip = target_dict["target_ips"][target_dict["next_target_index"]]
            create_task(self.ping_and_export(target_ip))

    async def ping_and_export(
        self,
        ip: str,
    ) -> PingResult:
        print(f"Firing up a ping request to {ip}")
        ping_attemp = self.ip_to_ping_attemp_dict.get(ip)

        loop = get_running_loop()
        with ThreadPoolExecutor() as pool:
            ping_func = partial(self._ping, ping_attemp.target_ip)
            success, ping_ms = await loop.run_in_executor(pool, ping_func)
        ping_result = PingResult(
            **ping_attemp.model_dump(), ping_success=success, ping_value_ms=ping_ms
        )
        PING_ATTEMPS_COUNT.labels(self.nodename).inc()
        labels_dict = self._model_to_prom_labels(ping_result)
        label_values = self._labels_dict_to_ordered_label_values(labels_dict)
        if ping_result.target_type == "node":
            self.last_node_labels[ping_result.target_name] = label_values
        elif ping_result.target_type == "device":
            self.last_device_labels[ping_result.target_device_id] = label_values
        if success:
            print(
                f"SUCCESS: from {ping_result.target_type} {ping_result.target_name} : {ping_result.ping_value_ms} ms"
            )
            PING_SUCCESS_COUNT.labels(self.nodename).inc()
            PING_LATENCY.labels(**labels_dict).set(ping_result.ping_value_ms)
        else:  # TODO: Alert unreachable
            print(f"ERROR: {ping_result.nodename} cant ping {ping_result.target_name}.")
            try:
                PING_LATENCY.remove(*label_values)
                print(f"Removed ping metric for with labels {label_values}")
            except KeyError as ke:
                print(f"KeyError: {ke} - Metric already removed or never existed.")
            PING_FAIL_COUNT.labels(self.nodename).inc()

    def _model_to_prom_labels(self, ping_result: PingResult) -> dict:
        return {
            "nodename": ping_result.nodename,
            "target_type": ping_result.target_type,
            "target_name": ping_result.target_name,
            "target_device_id": ping_result.target_device_id,
        }

    def _labels_dict_to_ordered_label_values(self, labels_dict: dict) -> list:
        return [
            labels_dict.get("nodename"),
            labels_dict.get("target_type"),
            labels_dict.get("target_name"),
            labels_dict.get("target_device_id"),
        ]

    def _ping(self, target_ip):
        try:
            ping_ = ping(target_ip)
            if ping_.success():
                ping_ms = ping_.rtt_avg * 1000
                success = True
            else:
                ping_ms = -1
                success = False
        except RuntimeError as re:
            print(re)
            ping_ms = -1
            success = False
        return success, ping_ms

    async def _start(self):
        while self._run:
            await self.is_time_self_vertexpool_measurement()
            await self.is_time_vertexpool_measurement()
            await sleep(1)
