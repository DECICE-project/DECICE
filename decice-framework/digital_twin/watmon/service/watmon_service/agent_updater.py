from datetime import datetime
import asyncio
from watmon_service.settings import Settings
import concurrent.futures
from functools import partial
from watmon_service.prometheus.promql_query import get_agent_pod_ips
from watmon_service.db.vertexpool import VertexpoolManager
from watmon_service.db.session import session_generate
from watmon_service.schema import VertexpoolsPost
from watmon_service.common import convert_vertexpool_response_list
from httpx import AsyncClient, Response
from requests import ConnectionError
from kubernetes.client import CoreV1Api, V1PodList, V1Pod

from aiopromql import PrometheusAsync


def _get_pods_with_label(
    k8s_v1: CoreV1Api, label_key: str, label_value: str, namespace: str
) -> list[str]:
    """Asyncronous Namespaced running pods with label"""
    pods: V1PodList = k8s_v1.list_namespaced_pod(
        namespace=namespace,
        label_selector=f"{label_key}={label_value}",
    )
    if not isinstance(pods, V1PodList):
        return []
    pod_list: list[V1Pod] = pods.items
    if not pod_list:
        return []

    agents = [
        pod.status.pod_ip
        for pod in pod_list
        if pod.status.phase == "Running" and pod.status.pod_ip is not None
    ]
    return agents


class AgentUpdater:
    """Responsible for updating Watmon-Network-Exporter Agents with Vertexpools."""

    def __init__(
        self,
        settings: Settings,
        k8s_v1: CoreV1Api,
        max_inform_interval_seconds: float = 60.0,
        min_inform_inertval_seconds: float = 10.0,
    ) -> None:
        self.settings = settings
        self.prom = PrometheusAsync(url=self.settings.prometheus_url, timeout=4)
        self.vertexpool_manager = VertexpoolManager(session_manager=session_generate)
        self.vertexpool_manager.async_trigger_callables.append(self.trigger)
        self.last_informed: datetime = datetime.now()
        self.max_inform_interval_seconds: float = max_inform_interval_seconds
        self.min_inform_inertval_seconds: float = min_inform_inertval_seconds
        self._run = True
        self.agents_ips: list[str] = []
        self.k8s_v1 = k8s_v1

    async def run_agent_list_updates(self, update_interval: float = 10):
        """Read Prometheus or Kubernetes for network exporter agents."""
        while self._run:
            try:
                if self.k8s_v1:
                    await self._update_agents_from_k8s()
                else:
                    await self._update_agents_from_prom()
            except ConnectionError as ce:
                print(f"CONNECTION ERROR: {ce}")
            except Exception as e:
                print(f"ERROR: {e}")
            await asyncio.sleep(update_interval)

    async def _update_agents_from_prom(self):
        """Read prometheus for network exporter agents pod ips"""
        self.agents_ips = await get_agent_pod_ips(
            self.settings.network_exporter_label_key,
            self.settings.network_exporter_label_value,
            self.prom,
        )

    async def _update_agents_from_k8s(self):
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pod_func = partial(
                _get_pods_with_label,
                self.k8s_v1,
                self.settings.network_exporter_label_key,
                self.settings.network_exporter_label_value,
                self.settings.namespace,
            )
            self.agents_ips = await loop.run_in_executor(pool, pod_func)

    async def _check_trigger_due_to_timeout(self):
        current_time = datetime.now()
        if (
            current_time - self.last_informed
        ).total_seconds() > self.max_inform_interval_seconds:
            print("Agent Trigger due to timeout!")
            await self.trigger()

    def _is_trigger_too_soon_to_update(self):
        current_time = datetime.now()
        if (
            current_time - self.last_informed
        ).total_seconds() < self.min_inform_inertval_seconds:
            print("Trigger too soon to update")
            return True
        else:
            return False

    async def trigger(self, log_msg: str | None = None):
        """Time for a inform_agents(), alse refreshes last_informed"""
        if self._is_trigger_too_soon_to_update():
            return
        if log_msg:
            print(f"trigger due to {log_msg}")
        self.last_informed = datetime.now()
        # Call inform_agents here (implementation not provided)
        await self.inform_agents()

    async def inform_agents(self):
        vertexpools = await self._gather_database_data()
        print(f"will inform {len(self.agents_ips)} pods with")
        print(f"{vertexpools}")
        data = VertexpoolsPost(vertexpools=vertexpools).model_dump_json()
        protocol = "http://"
        port = f":{self.settings.exporter_port}"
        endpoint = f"{self.settings.exporter_vertexpools_endpoint}"
        for ip in self.agents_ips:
            agent_url = protocol + ip + port + endpoint
            _ = asyncio.create_task(self._post_to_agent(data, agent_url))

    async def _post_to_agent(self, data: dict, url: str) -> Response:
        async with AsyncClient() as client:
            print(f"POSTing to: {url}")
            try:
                response = await client.post(url, data=data)
                if response.is_error:
                    print(
                        f"POST ERROR on url: {url}, Status Code: {response.status_code} "
                    )
                    return None
                else:
                    print(f"Post succesfull on {url}")
                    return response
            except Exception as e:
                print(f"Unexpected error while POSTing to {url}: {e}")

    async def _gather_database_data(self):
        vertexpools = await convert_vertexpool_response_list(self.vertexpool_manager)
        vertexpool_count = len(vertexpools)
        node_count = 0
        device_count = 0
        for vp in vertexpools:
            node_count += len(vp.nodes)
            device_count += len(vp.devices)
        print(
            f"will inform agents.Vertexpool count: {vertexpool_count}, {device_count} devices and {node_count} nodes exists."
        )
        return vertexpools

    async def run(self, run_interval: float = 1):
        asyncio.create_task(self.run_agent_list_updates())
        while self._run:
            await self._check_trigger_due_to_timeout()
            await asyncio.sleep(run_interval)
