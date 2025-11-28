# async tasks that periodically checks prometheus for current nodes and node ips
# task will delete and add nodes using watmon_service.db.vertexpool.VertexpoolManager
from requests import ConnectionError
import asyncio
import concurrent.futures
from kubernetes.client import CoreV1Api, V1NodeList, V1Node
from aiopromql import PrometheusAsync

from watmon_service.settings import read_settings, Settings
from watmon_service.db.vertexpool import VertexpoolManager
from watmon_service.db.session import session_generate
from watmon_service.schema import NodeInVP
from watmon_service.prometheus.promql_query import get_nodes_and_their_ips


class NodeSniffer:
    """Respobsible for sniffing Kubernetes nodes and updating the WATMON database."""

    def __init__(self, settings: Settings, v1: CoreV1Api | None) -> None:
        self.vertexpool_manager = VertexpoolManager(session_manager=session_generate)
        self.v1 = v1
        self.use_kube_config = False
        if self.v1:
            self.use_kube_config = True
        self.prom = PrometheusAsync(settings.prometheus_url, 4.0)
        self._run: bool = True

    def _find_node_in_list_node_info(
        self, nodename: str, list_node_info: list[NodeInVP]
    ) -> NodeInVP | None:
        for node_info in list_node_info:
            if nodename == node_info.nodename:
                return node_info

    async def _load_kubernetes_nodes(self) -> list[NodeInVP]:
        # load kubernetes nodes in asyncio loop
        loop = asyncio.get_running_loop()
        returnlist: list[NodeInVP] = []
        with concurrent.futures.ThreadPoolExecutor() as pool:
            nodes: V1NodeList = await loop.run_in_executor(pool, self.v1.list_node)
            for node in nodes.items:
                node: V1Node
                internal_ip_address = None
                for it in node.status.addresses:
                    if it.type == "InternalIP":
                        internal_ip_address = it.address
                        break
                item = NodeInVP(nodename=node.metadata.name)
                if internal_ip_address:
                    item.ip = internal_ip_address
                returnlist.append(item)
            return returnlist

    async def sync_node_memory(self):
        """Reads the nodes from prometheus then, updates the nodes in database and in memory."""
        try:
            if not self.use_kube_config:
                self.in_cluster_nodes = await get_nodes_and_their_ips(self.prom)
            else:
                self.in_cluster_nodes = await self._load_kubernetes_nodes()
            nodes_from_database = await self.vertexpool_manager.get_nodes()

            # update and delete nodes in database
            for node in nodes_from_database:
                # if this is a stale node, delete it
                if node.nodename not in [n.nodename for n in self.in_cluster_nodes]:
                    await self.vertexpool_manager.delete_node(node.nodename)
                    continue
                # if database nodes ip not the same in cluster , update it
                node_from_cluster = self._find_node_in_list_node_info(
                    node.nodename, self.in_cluster_nodes
                )
                if node_from_cluster and node_from_cluster.ip != node.ip:
                    await self.vertexpool_manager.patch_node(
                        nodename=node.nodename, ip=node_from_cluster.ip
                    )

            # for nodes in cluster but not in database, add them
            for node in self.in_cluster_nodes:
                if node.nodename not in [n.nodename for n in nodes_from_database]:
                    await self.vertexpool_manager.add_node(
                        nodename=node.nodename, ip=node.ip
                    )
        except ConnectionError as ce:
            print(f"PROMETHEUS CONNECTION ERROR: {ce}")

    async def run(self, update_interval_seconds=15):
        while self._run:
            await self.sync_node_memory()
            await asyncio.sleep(update_interval_seconds)

    async def stop(self):
        await self.vertexpool_manager.close()

    def debug_start(self):
        asyncio.run(self.sync_node_memory())


if __name__ == "__main__":
    settings: Settings = read_settings()
    ns = NodeSniffer(settings)
    ns.debug_start()
