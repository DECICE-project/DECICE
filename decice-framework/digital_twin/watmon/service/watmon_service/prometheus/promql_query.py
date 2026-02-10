from aiopromql import PrometheusAsync, make_label_string
from watmon_service.graph import NetworkxEdge, NetworkxNode, TypedGraph
from watmon_service.schema import NodeInVP
from watmon_service.prometheus.promql_schema import (
    PromVertexpool,
    PromDevice,
    PromNode,
    LinkLatencyMs,
    UniDirectionalVertexpoolMs,
    RawNodeLinkLatencyMs,
    UniDirectionalVertexMs,
)
from datetime import datetime
import json
from pydantic import BaseModel
from datetime import timezone

VERTEXPOOL_QUERY = """decice_device_info * on(vertexpool_id) group_left(vertexpool_labels) decice_vertexpool_labels
        * on(device_id) group_left(device_labels) decice_device_labels
        OR
        decice_node_info * on(vertexpool_id) group_left(vertexpool_labels) decice_vertexpool_labels"""


def _label_dict_to_label_list(label_dict: dict) -> list[str]:
    return_list = []
    for key, value in label_dict.items():
        return_list.append(key + ":" + value)
    return return_list


def _update_vertexpool(
    metric_dictionary: dict,
    last_updated: datetime,
    vertexpool: PromVertexpool | None = None,
) -> PromVertexpool:
    nodename = metric_dictionary.get("nodename")
    device_id = metric_dictionary.get("device_id")
    vertexpool_labels = []
    vertexpool_labels_string: str = metric_dictionary.get("vertexpool_labels")
    if vertexpool_labels_string:
        vertexpool_labels = json.loads(vertexpool_labels_string.replace("'", '"'))
        vertexpool_labels = _label_dict_to_label_list(vertexpool_labels)
    if nodename:
        node = PromNode(name=nodename, ip=metric_dictionary.get("node_ip"))
        if not vertexpool:
            return PromVertexpool(
                id=int(metric_dictionary.get("vertexpool_id")),
                nodes=[node],
                lastUpdated=last_updated,
                vertexpool_labels=vertexpool_labels,
            )
        else:
            vertexpool.nodes.append(node)
            vertexpool.lastUpdated = last_updated
            return vertexpool
    elif device_id:
        device_labels = []
        device_labels_string: str = metric_dictionary.get("device_labels")
        if device_labels_string:
            device_labels = json.loads(device_labels_string.replace("'", '"'))
            device_labels = _label_dict_to_label_list(device_labels)
        ip = metric_dictionary.get("device_ip")
        device = PromDevice(
            id=int(device_id),
            labels=device_labels,
            ip=ip,
            name=metric_dictionary.get("devicename"),
        )
        if not vertexpool:
            return PromVertexpool(
                id=int(metric_dictionary.get("vertexpool_id")),
                devices=[device],
                lastUpdated=last_updated,
                vertexpool_labels=vertexpool_labels,
            )
        else:
            vertexpool.devices.append(device)
            vertexpool.lastUpdated = last_updated
            return vertexpool


async def get_agent_pod_ips(label_key: str, label_value: str, prom: PrometheusAsync) -> list[str]:
    """Get the IPs of all pods with the specified label."""
    prom_lk = f"label_{label_key}"
    query_string = (
        f"kube_pod_ips * on(pod) group_left({prom_lk}) kube_pod_labels{make_label_string(**{prom_lk: label_value})}"
    )
    response_model = await prom.query(query_string)
    return_list = [
        metric.get("ip") for metric, ts_value in response_model.to_metric_map().items() if ts_value.latest().value == 1
    ]
    return return_list


async def get_nodes_and_their_ips(prom: PrometheusAsync) -> list[NodeInVP]:
    """Get Kubernetes nodes and their IPs from Prometheus."""
    query_string = "kube_node_info"
    response_model = await prom.query(query_string)
    return_list = [
        NodeInVP(nodename=metric.get("node"), ip=metric.get("internal_ip"))
        for metric in response_model.to_metric_map().keys()
    ]
    return return_list


async def get_vertexpools(prom: PrometheusAsync) -> list[PromVertexpool]:
    vertexpool_dict: dict[int, PromVertexpool] = {}
    resp = await prom.query(VERTEXPOOL_QUERY)
    resp_map = resp.to_metric_map()
    for metric, ts in resp_map.items():
        vertexpool_id: int = int(metric.get("vertexpool_id"))
        if vertexpool_id not in vertexpool_dict:
            vertexpool_dict[vertexpool_id] = _update_vertexpool(metric, ts.latest().timestamp)
        else:
            vertexpool_dict[vertexpool_id] = _update_vertexpool(
                metric, ts.latest().timestamp, vertexpool_dict[vertexpool_id]
            )
    return list(vertexpool_dict.values())


def get_vertexpool_links_string(interval: str = "5m") -> str:
    """Get promql query string that returns latencies between vertexpools"""
    base_query = get_edges_base_query_string(interval=interval)
    q = "avg by (target_vertexpool_id,self_vertexpool_id)(" + base_query + ")"
    return q


def get_edges_base_query_string(
    nodename: str | None = None,
    vertexpool_selector: str | None = None,
    interval: str = "5m",
) -> str:
    node_filter = ""
    vertexpool_id = ""
    if vertexpool_selector:
        vertexpool_id = "vertexpool_id='%s'" % (vertexpool_selector)
    if nodename:
        node_filter = ",nodename='%s'" % (nodename)
    q = (
        "("
        + "label_replace(avg_over_time(decice_ping_latency_ms{target_type='device'%s}[%s]), 'device_id', '$1', 'target_device_id', '(.*)')"
        % (node_filter, interval)
        + "* on(nodename) group_left(self_vertexpool_id)"
        + "label_replace(decice_node_info{%s},'self_vertexpool_id','$1','vertexpool_id','(.*)')" % (vertexpool_id)
        + "* on(device_id) group_left(target_vertexpool_id)"
        + "label_replace(decice_device_info{%s} , 'target_vertexpool_id' , '$1', 'vertexpool_id', '(.*)')"
        % (vertexpool_id)
        + ")"
        + "OR"
        + "("
        + "avg_over_time(decice_ping_latency_ms{target_type='node'%s}[%s])" % (node_filter, interval)
        + "* on(nodename) group_left(self_vertexpool_id)"
        + "label_replace(decice_node_info{%s},'self_vertexpool_id','$1','vertexpool_id','(.*)')" % (vertexpool_id)
        + "*on(target_name) group_left(target_vertexpool_id)"
        + "label_replace(label_replace(decice_node_info{%s},'target_vertexpool_id','$1','vertexpool_id','(.*)'),'target_name','$1','nodename','(.*)')"
        % (vertexpool_id)
        + ")"
    )
    return q


def _filter_dict_for_model(
    data: dict,
    model: BaseModel,
    additional_fields: set[str] | None = None,
    value: float | str | None = None,
) -> dict:
    model_fields = set(model.model_fields.keys())
    if additional_fields:
        model_fields.update(additional_fields)
    filtered_data = {key: value for key, value in data.items() if key in model_fields}
    if value:
        filtered_data["value"] = float(value)
    return filtered_data


async def get_vertexpool_links(
    prom: PrometheusAsync,
    unidirectional: bool = False,
    interval: str = "5m",
) -> list[LinkLatencyMs] | list[UniDirectionalVertexpoolMs]:
    "Returns directed Link latencies between Vertexpools"
    query = get_vertexpool_links_string(interval)
    resp = await prom.query(query)
    resp_metric = resp.to_metric_map()
    return_list: list[LinkLatencyMs] = []
    for metric, ts in resp_metric.items():
        link = LinkLatencyMs(**_filter_dict_for_model(metric.dict, LinkLatencyMs, value=ts.latest().value))
        link.lastUpdated = value = ts.latest().timestamp
        return_list.append(link)
    if unidirectional:
        unidirectional_links = []
        uni_link_dictionary: dict[tuple[str, str], float] = {}
        for link in return_list:
            link_tuple = tuple(sorted((link.self_vertexpool_id, link.target_vertexpool_id)))
            if link_tuple not in uni_link_dictionary:
                uni_link_dictionary[link_tuple] = link.value
            else:
                prev_value = uni_link_dictionary[link_tuple]
                uni_link_dictionary[link_tuple] = (prev_value + link.value) / 2
        for uni_link, value in uni_link_dictionary.items():
            a, b = uni_link[0], uni_link[1]
            unidirectional_links.append(
                UniDirectionalVertexpoolMs(
                    vertexpool_a=a,
                    vertexpool_b=b,
                    value=value,
                    lastUpdated=datetime.now(tz=timezone.utc),
                )
            )
        return unidirectional_links
    return return_list


async def get_node_to_x_latency(
    prom: PrometheusAsync,
    nodename: str | None = None,
    vertexpool_selector: str | None = None,
    interval: str | None = "5m",
    unidirectional: bool = False,
) -> list[RawNodeLinkLatencyMs] | list[UniDirectionalVertexMs]:
    """Returns nodes directed latencies(outwards) to other nodes and devices.

    If no nodename is specified returns all directed edges that represent latencies.

    unidirectional flag can be set to True to return unidirectional link avarages only.
    """
    query = get_edges_base_query_string(nodename=nodename, vertexpool_selector=vertexpool_selector, interval=interval)
    resp = await prom.query(query)
    resp_metric = resp.to_metric_map()
    return_list: list[RawNodeLinkLatencyMs] = []
    for metric, ts in resp_metric.items():
        link = RawNodeLinkLatencyMs(
            **_filter_dict_for_model(metric.dict, RawNodeLinkLatencyMs, value=ts.latest().value)
        )
        link.lastUpdated = ts.latest().timestamp
        return_list.append(link)

    if unidirectional:
        unidirectional_links = []
        uni_link_dictionary: dict[tuple[str, str], float] = {}
        vertex_a_device_id_dictionary: dict[tuple[str, str], int] = {}
        vertex_b_device_id_dictionary: dict[tuple[str, str], int] = {}
        for link in return_list:
            if not link.target_device_id and link.nodename == link.target_name:
                continue

            link_tuple = tuple(sorted((link.nodename, link.target_name)))
            if link.target_device_id:
                if link.nodename == link_tuple[0]:
                    vertex_b_device_id_dictionary[link_tuple] = int(link.target_device_id)
                else:
                    vertex_a_device_id_dictionary[link_tuple] = int(link.target_device_id)

            if link_tuple not in uni_link_dictionary:
                uni_link_dictionary[link_tuple] = link.value
            else:
                prev_value = uni_link_dictionary[link_tuple]
                uni_link_dictionary[link_tuple] = (prev_value + link.value) / 2

        for uni_link, value in uni_link_dictionary.items():
            a, b = uni_link[0], uni_link[1]
            a_device_id = None
            b_device_id = None
            if uni_link in vertex_a_device_id_dictionary:
                a_device_id = vertex_a_device_id_dictionary[uni_link]
            if uni_link in vertex_b_device_id_dictionary:
                b_device_id = vertex_b_device_id_dictionary[uni_link]

            unidirectional_links.append(
                UniDirectionalVertexMs(
                    vertex_a=a,
                    vertex_b=b,
                    lastUpdated=datetime.now(tz=timezone.utc),
                    value=value,
                    vertex_a_device_id=a_device_id,
                    vertex_b_device_id=b_device_id,
                )
            )
        return unidirectional_links
    return return_list


async def construct_typed_graph(
    interval: str,
    prom: PrometheusAsync,
) -> TypedGraph:
    tg = TypedGraph(directed=True)
    # Get nodes and devices from vertexpools
    resp = await prom.query(VERTEXPOOL_QUERY)
    nodes_q = resp.to_metric_map()
    for metric in nodes_q.keys():
        # vpid = metric.get("vertexpool_id")
        nodename = metric.get("nodename")
        if nodename is not None:
            nxnode = NetworkxNode(name=nodename, type="node")
            tg.add_node(nxnode)
        else:
            devname = metric.get("devicename")
            nxdevice = NetworkxNode(name=devname, type="device", device_id=metric.get("device_id"))
            tg.add_node(nxdevice)

    # Get edges from Prometheus
    resp = await prom.query(get_edges_base_query_string(interval=interval))
    edges_q = resp.to_metric_map()
    for metric, value in edges_q.items():
        latest_value = value.latest().value
        # source is always a type node
        src_node = (metric.get("nodename"), "node")
        # destination can be either a device or a node
        dest_type = metric.get("target_type")
        if dest_type == "node":
            dst_node = (metric.get("target_name"), "node")
        else:
            dst_node = (metric.get("target_name"), "device")
        tg.add_edge_from_key(
            src_key=src_node,
            dst_key=dst_node,
            edge=NetworkxEdge(label=metric.get("network_delay_ms"), weight=latest_value),
        )
    return tg
