from aiopromql import PrometheusSync
from watmon_service.graph import TypedGraph, NetworkxNode, NetworkxEdge
from watmon_service.prometheus.promql_query import (
    get_edges_base_query_string,
)

VERTEXPOOL_QUERY = """decice_device_info * on(vertexpool_id) group_left(vertexpool_labels) decice_vertexpool_labels
        * on(device_id) group_left(device_labels) decice_device_labels
        OR
        decice_node_info * on(vertexpool_id) group_left(vertexpool_labels) decice_vertexpool_labels"""


def construct_typed_graph() -> TypedGraph:
    prom = PrometheusSync(
        url="http://10.42.0.1:30090",
        timeout=10,
    )
    tg = TypedGraph(directed=True)

    # Get nodes and devices from vertexpools
    nodes_q = prom.query(VERTEXPOOL_QUERY).to_metric_map()
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
    edges_q = prom.query(get_edges_base_query_string()).to_metric_map()
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
    prom.close()
    return tg


se = construct_typed_graph().get_structural_equivalence()
print("Structurally equivalent nodes:")
for group in se:
    print(group)
