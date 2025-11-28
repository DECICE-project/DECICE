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


# TODO: Populate id fields for Node with UID instead of nodename
class NodeService:
    def __init__(self, prometheus_url: str) -> None:
        self.url = normalize_url(prometheus_url)
        self._node_dict: dict[str, Node] = {}
        self.node_info_query = (
            {}
        )  # Dictionary to hold node_info queries and mapping to node_info keys
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
        # self.add_node_info_query(anomaly_score := "decice_node_anomaly_score", "anomaly_score")

    def apply_node_info_queries(self):
        """Applies node info queries from config to the service."""
        node_info_queries = get_node_info_queries()
        for query_config in node_info_queries:
            self._add_node_info_query(query_config.promql, query_config.field_name)

    def add_node_metric_query(self, query_list: list[str], attr: str):
        """Adds PromQL queries to node_metric_query_to_attr. PromQL query results should have the label nodename.

        Args:
            query_list (list[str]): PromQL queries to be fetched from Prometheus.
            attr (str): Correspoinding attribute name in Node.Metrics
        """
        for query in query_list:
            if query not in self.node_metric_query_to_attr:
                self.node_metric_query_to_attr[query] = attr

    def _add_node_info_query(self, query: str, dict_key: str):
        """Adds PromQL query to node_info_query. PromQL query results should have the label nodename.

        Args:
            query (str): PromQL query to be fetched from Prometheus.
            dict_key (str): Corresponding key in Node.node_info dictionary.
        """
        if query not in self.node_info_query:
            self.node_info_query[query] = dict_key

    def _upsert_node(
        self,
        nodename: str,
        attr_name: str | None = None,
        value: float | None = None,
        node_info_dict_key: str | None = None,
    ):
        "Given the nodename updates the node, if it doesnt exist creates the node"
        if nodename not in self._node_dict:
            self._node_dict[nodename] = Node(
                name=nodename, metrics=Metrics(), id=nodename
            )
        # if this is additional node_info, we need to update the node_info dictionary
        if attr_name == "node_info" and value is not None:
            # get the dictionary from attr_name
            node: Node = self._node_dict.get(nodename)
            if not node.node_info:
                node.node_info = {}
            if node_info_dict_key:
                node.node_info[node_info_dict_key] = value
        # else if this is a base metric, we update the metrics directly
        elif attr_name and value:
            node: Node = self._node_dict.get(nodename)
            setattr(node.metrics, attr_name, value)

    async def pull_metrics(self):
        """Fetches metrics all at once via a network calls to Prometheus and updates self._node_dict

        All metrics should have "nodename" label
        """
        async with PrometheusAsync(self.url, timeout=10) as client:
            queries = list(self.node_metric_query_to_attr.keys()) + list(
                self.node_info_query.keys()
            )
            tasks = [client.query(q) for q in queries]
            responses = await asyncio.gather(*tasks)
            for query, resp in zip(queries, responses):
                node_info_key = None
                if query in self.node_info_query:
                    node_info_key = self.node_info_query[query]
                    att = "node_info"
                else:
                    att = self.node_metric_query_to_attr[query]
                metric_map = resp.to_metric_map()
                for labels, timeseries in metric_map.items():
                    labels_dict = labels.dict
                    nodename = labels_dict.get("nodename")
                    # nodename = labels.get("nodename").lower()

                    if not nodename:
                        continue

                    nodename = nodename.lower()
                    value = timeseries.latest().value
                    if node_info_key:  # for node_info values
                        self._upsert_node(
                            nodename, att, value, node_info_dict_key=node_info_key
                        )
                    else:  # for base metrics
                        self._upsert_node(nodename, att, value)

    def get_node(self, nodename: str) -> Node:
        """Returns pydantic object for given nodename"""
        return self._node_dict[nodename]

    def pop_node(self, nodename: str) -> Node:
        """Returns the pydantic object for the given nodename and removes it from the dictionary."""
        return self._node_dict.pop(nodename)


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
                        self._nodes._upsert_node(nodename.lower())
                    list_values.append(metric_dict)

    def finalize_vertexpools(self) -> list[Vertexpool]:
        """Returns populated Vertexpools"""
        vertexpool_dict: dict[str, Vertexpool] = {}
        # process vertexpool and its labels
        for vp in self._vertexpools_labels:
            vp_id = vp.get("vertexpool_id")
            vertexpool = Vertexpool(
                id=vp_id,
                nodes=[],
                devices=[],
            )
            vertexpool_label_string = vp.get("vertexpool_labels")
            if vertexpool_label_string:
                vertexpool.vertexpool_labels = json.loads(vertexpool_label_string)
            else:
                vertexpool.vertexpool_labels = None
            vertexpool_dict[vp_id] = vertexpool

        # insert nodes
        for node_metric in self._node_mappings:
            nodename = node_metric.get("nodename")
            vertexpool_id = node_metric.get("vertexpool_id")
            try:
                node = self._nodes.pop_node(nodename)
            except KeyError:
                continue
            vertexpool_dict[vertexpool_id].nodes.append(node)

        # populate devices
        for dev in self._devices_metrics:
            dev_id = dev.get("device_id")
            dev_name = dev.get("devicename")
            dev_labels_string = dev.get("device_labels")
            if dev_labels_string:
                device_labels = json.loads(dev_labels_string)
            else:
                device_labels = None
            device_vp_id = dev.get("vertexpool_id")

            device = Device(id=dev_id, name=dev_name, labels=device_labels)
            vertexpool_dict[device_vp_id].devices.append(device)

        # Handle remaining nodes that were not associated with any vertexpool
        if self._nodes._node_dict:
            unassigned_vertices = vertexpool_dict.get(None)
            if not unassigned_vertices:
                unassigned_vertices = Vertexpool(id=None, nodes=[], devices=[])
                vertexpool_dict[None] = unassigned_vertices

        for node in self._nodes._node_dict.values():
            unassigned_vertices.nodes.append(node)

        return vertexpool_dict.values()


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
            vertexpool_id_source: str = labels_dict.get("self_vertexpool_id")
            vertexpool_id_dest: str = labels_dict.get("target_vertexpool_id")
            # vertexpool_id_source: str = labels.get("self_vertexpool_id")
            # vertexpool_id_dest: str = labels.get("target_vertexpool_id")

            # Ensure both required labels were found before proceeding
            if not vertexpool_id_source or not vertexpool_id_dest:
                continue

            latency: float = timeseries.latest().value
            links.append(
                Link(
                    vertexpool_a_id=vertexpool_id_source,
                    vertexpool_b_id=vertexpool_id_dest,
                    network_delay_ms=latency,
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
        """Applies cluster info queries from config to the service."""
        cluster_info_queries = get_cluster_info_queries()
        for query_config in cluster_info_queries:
            if (
                query_config.promql,
                query_config.field_name,
                query_config.label_key,
            ) not in self.cluster_info_query:
                self.cluster_info_query[
                    (
                        query_config.promql,
                        query_config.field_name,
                        query_config.label_key,
                    )
                ] = {}

    async def fetch_cluster_info(self):
        """Fetches cluster info metrics all at once via a network calls to Prometheus and updates self.cluster_info_query"""
        async with PrometheusAsync(self.url, timeout=10) as client:
            queries = [key[0] for key in self.cluster_info_query.keys()]
            tasks = [client.query(q) for q in queries]
            responses = await asyncio.gather(*tasks)
            for (query, field_name, label_key), resp in zip(
                self.cluster_info_query.keys(), responses
            ):
                metric_map = resp.to_metric_map()
                self.cluster_info_query[(query, field_name, label_key)].clear()
                self.cluster_info_query[(query, field_name, label_key)].update(
                    metric_map
                )

    def process(self) -> dict:
        cluster_info: dict = {}
        for (
            query,
            field_name,
            label_key,
        ), metric_map in self.cluster_info_query.items():
            if label_key is None:
                # Direct mapping to field_name
                for labels, timeseries in metric_map.items():
                    value: float = timeseries.latest().value
                    cluster_info[field_name] = value
            else:
                # Mapping by label values
                field_dict: dict = {}
                for labels, timeseries in metric_map.items():
                    labels_dict = labels.dict
                    label_value = labels_dict.get(label_key)
                    if not label_value:
                        continue
                    value: float = timeseries.latest().value
                    field_dict[label_value] = value
                cluster_info[field_name] = field_dict
        return cluster_info
