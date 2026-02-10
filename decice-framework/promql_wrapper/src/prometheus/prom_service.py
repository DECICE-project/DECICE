import asyncio
import json
from urllib.parse import urlparse, urlunparse

from aiopromql import PrometheusAsync
from aiopromql.models.core import MetricLabelSet, TimeSeries

from models.models import Device, Link, Metrics, Node, Vertexpool

from .promql_queries import (BANDWIDTH, CPU_CORES, CPU_USAGE, FREE_DISK_GB,
                             MEMORY_USAGE, TOTAL_DISK_GB, TOTAL_MEMORY,
                             VP_DEVICE_INFO, VP_LABELS, VP_NODE_INFO,
                             get_cluster_info_queries, get_node_info_queries,
                             get_power_consumption_queries,
                             get_vertexpool_links_string)


def normalize_url(url: str, default_scheme="http") -> str:
    if "://" not in url:
        url = f"{default_scheme}://{url}"
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must use http or https scheme")
    return urlunparse(parsed)


class NodeService:
    def __init__(self, prometheus_url: str) -> None:
        self.url = normalize_url(prometheus_url)
        self._node_dict: dict[str, Node] = {}
        self.node_info_query = {}
        
        self.node_metric_query_to_attr = {
            BANDWIDTH: "network_bandwidth_mbps",
            CPU_CORES: "cpu_cores",
            CPU_USAGE: "util",
            FREE_DISK_GB: "free_disk_gb",
            MEMORY_USAGE: "mem_util",
            TOTAL_DISK_GB: "total_disk_gb",
            TOTAL_MEMORY: "mem_total",
        }
        
        power_watts_list = get_power_consumption_queries()
        self.add_node_metric_query(power_watts_list, "power_watts")
        self.apply_node_info_queries()

    def apply_node_info_queries(self):
        """Applies node info queries from config to the service."""
        node_info_queries = get_node_info_queries()
        for query_config in node_info_queries:
            self._add_node_info_query(query_config.promql, query_config.field_name)

    def add_node_metric_query(self, query_list: list[str], attr: str):
        for query in query_list:
            if query not in self.node_metric_query_to_attr:
                self.node_metric_query_to_attr[query] = attr

    def _add_node_info_query(self, query: str, dict_key: str):
        if query not in self.node_info_query:
            self.node_info_query[query] = dict_key

    def _upsert_node(
        self,
        nodename: str,
        attr_name: str | None = None,
        value: float | None = None,
        node_info_dict_key: str | None = None,
    ):
        nodename = nodename.lower()
        if nodename not in self._node_dict:
            self._node_dict[nodename] = Node(
                name=nodename, metrics=Metrics(), id=nodename
            )
            
        if attr_name == "node_info" and value is not None:
            node = self._node_dict[nodename]
            if node.node_info is None:
                node.node_info = {}
            if node_info_dict_key:
                node.node_info[node_info_dict_key] = value
                
        elif attr_name and value is not None:
            node = self._node_dict[nodename]
            # Clamp utilization metrics to valid ranges [0, 100]
            if attr_name in ["util", "mem_util"]:
                value = max(0.0, min(100.0, float(value)))
            
            setattr(node.metrics, attr_name, value)

    async def pull_metrics(self):
        """Fetches metrics all at once via network calls and updates _node_dict."""
        async with PrometheusAsync(self.url, timeout=10) as client:
            queries = list(self.node_metric_query_to_attr.keys()) + list(
                self.node_info_query.keys()
            )
            tasks = [client.query(q) for q in queries]
            responses = await asyncio.gather(*tasks)
            
            for query, resp in zip(queries, responses):
                node_info_key = self.node_info_query.get(query)
                att = "node_info" if node_info_key else self.node_metric_query_to_attr.get(query)
                
                metric_map = resp.to_metric_map()
                for labels, timeseries in metric_map.items():
                    labels_dict = labels.dict
                    nodename = labels_dict.get("nodename")

                    if not nodename:
                        continue

                    value = timeseries.latest().value
                    self._upsert_node(
                        nodename, att, value, node_info_dict_key=node_info_key
                    )

    def get_node(self, nodename: str) -> Node:
        return self._node_dict[nodename.lower()]

    def pop_node(self, nodename: str) -> Node:
        return self._node_dict.pop(nodename.lower())


class VertexPoolService:
    def __init__(self, prometheus_url: str, nodes: NodeService) -> None:
        self.url = normalize_url(prometheus_url)
        self._nodes = nodes
        self._devices_metrics: list[dict] = []
        self._vertexpools_labels: list[dict] = []
        self._node_mappings: list[dict] = []
        self.query_to_list_mapping = {
            VP_NODE_INFO: self._node_mappings,
            VP_DEVICE_INFO: self._devices_metrics,
            VP_LABELS: self._vertexpools_labels,
        }

    async def fetch_metrics(self):
        async with PrometheusAsync(self.url, timeout=10) as client:
            queries = list(self.query_to_list_mapping.keys())
            tasks = [client.query(q) for q in queries]
            responses = await asyncio.gather(*tasks)

            for query, resp in zip(queries, responses):
                list_values = self.query_to_list_mapping[query]
                metric_map = resp.to_metric_map()

                for labels, _ in metric_map.items():
                    metric_dict = labels.dict
                    nodename = metric_dict.get("nodename")
                    if nodename:
                        self._nodes._upsert_node(nodename)
                    list_values.append(metric_dict)

    def finalize_vertexpools(self) -> list[Vertexpool]:
        """Returns populated Vertexpools."""
        vertexpool_dict: dict[str, Vertexpool] = {}
        
        # Initialize vertexpools from discovered labels
        for vp in self._vertexpools_labels:
            vp_id = vp.get("vertexpool_id")
            if not vp_id:
                continue
                
            vertexpool = Vertexpool(
                id=vp_id,
                nodes=[],
                devices=[],
            )
            labels_raw = vp.get("vertexpool_labels")
            if labels_raw:
                try:
                    vertexpool.vertexpool_labels = json.loads(labels_raw)
                except json.JSONDecodeError:
                    vertexpool.vertexpool_labels = None
            
            vertexpool_dict[vp_id] = vertexpool

        # Assign nodes to their respective vertexpools
        for node_metric in self._node_mappings:
            nodename = node_metric.get("nodename")
            vp_id = node_metric.get("vertexpool_id")
            
            if not nodename or not vp_id:
                continue

            try:
                # Node Service keys are lowercase, pop_node handles this
                node = self._nodes.pop_node(nodename)
                if vp_id in vertexpool_dict:
                    vertexpool_dict[vp_id].nodes.append(node)
                else:
                    vertexpool_dict[vp_id] = Vertexpool(id=vp_id, nodes=[node], devices=[])
            except KeyError:
                continue

        # Populate devices
        for dev in self._devices_metrics:
            dev_id = dev.get("device_id")
            dev_vp_id = dev.get("vertexpool_id")
            if not dev_id or not dev_vp_id:
                continue

            labels_raw = dev.get("device_labels")
            device_labels = json.loads(labels_raw) if labels_raw else None

            device = Device(id=dev_id, name=dev.get("devicename"), labels=device_labels)
            if dev_vp_id in vertexpool_dict:
                vertexpool_dict[dev_vp_id].devices.append(device)

        # Handle orphaned nodes
        if self._nodes._node_dict:
            unassigned = vertexpool_dict.get(None)
            if not unassigned:
                unassigned = Vertexpool(id="unassigned", nodes=[], devices=[])
                vertexpool_dict["unassigned"] = unassigned

            for node in list(self._nodes._node_dict.values()):
                unassigned.nodes.append(node)

        return list(vertexpool_dict.values())


class LinkService:
    def __init__(self, prometheus_url="", link_interval_label="5m") -> None:
        self.url = normalize_url(prometheus_url)
        self.query_to_metrics_dict: dict[str, dict[MetricLabelSet, TimeSeries]] = {}
        self._link_metric: dict[MetricLabelSet, TimeSeries] = {}
        self.link_query = None
        self.update_link_interval_label(link_interval_label)

    def update_link_interval_label(self, new_interval) -> str:
        query = get_vertexpool_links_string(interval=new_interval)
        self.query_to_metrics_dict[query] = self._link_metric
        if self.link_query:
            del self.query_to_metrics_dict[self.link_query]
        self.link_query = query

    async def fetch_metrics(self):
        async with PrometheusAsync(self.url, timeout=10) as client:
            queries = list(self.query_to_metrics_dict.keys())
            tasks = [client.query(q) for q in queries]
            responses = await asyncio.gather(*tasks)

            for query, resp in zip(queries, responses):
                self.query_to_metrics_dict[query].clear()
                self.query_to_metrics_dict[query].update(resp.to_metric_map())

    def process(self) -> list[Link]:
        links = []
        for labels, timeseries in self._link_metric.items():
            labels_dict = labels.dict
            v_a = labels_dict.get("self_vertexpool_id")
            v_b = labels_dict.get("target_vertexpool_id")

            if not v_a or not v_b:
                continue

            links.append(
                Link(
                    vertexpool_a_id=v_a,
                    vertexpool_b_id=v_b,
                    network_delay_ms=timeseries.latest().value,
                )
            )
        return links


class CLusterInfoService:
    def __init__(self, prometheus_url: str) -> None:
        self.url = normalize_url(prometheus_url)
        self.cluster_info_query: dict[
            tuple[str, str, str | None], dict[MetricLabelSet, TimeSeries]
        ] = {}
        self._apply_cluster_info_queries()

    def _apply_cluster_info_queries(self):
        cluster_info_queries = get_cluster_info_queries()
        for q in cluster_info_queries:
            key = (q.promql, q.field_name, q.label_key)
            if key not in self.cluster_info_query:
                self.cluster_info_query[key] = {}

    async def fetch_cluster_info(self):
        async with PrometheusAsync(self.url, timeout=10) as client:
            queries = [key[0] for key in self.cluster_info_query.keys()]
            tasks = [client.query(q) for q in queries]
            responses = await asyncio.gather(*tasks)
            for (q, field_name, label_key), resp in zip(
                self.cluster_info_query.keys(), responses
            ):
                self.cluster_info_query[(q, field_name, label_key)].clear()
                self.cluster_info_query[(q, field_name, label_key)].update(
                    resp.to_metric_map()
                )

    def process(self) -> dict:
        cluster_info: dict = {}
        for (q, field_name, label_key), metric_map in self.cluster_info_query.items():
            if label_key is None:
                for _, ts in metric_map.items():
                    cluster_info[field_name] = ts.latest().value
            else:
                field_dict: dict = {}
                for labels, ts in metric_map.items():
                    l_dict = labels.dict
                    val = l_dict.get(label_key)
                    if val:
                        field_dict[val] = ts.latest().value
                cluster_info[field_name] = field_dict
        return cluster_info
