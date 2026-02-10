from config.config import ClusterInfoQueryConfig, NodeInfoQueryConfig, get_settings

# Node queries
NODES = "node_uname_info"

CPU_CORES = "label_replace(node:node_num_cpu:sum , 'nodename' , '$1' , 'node' , '(.*)')"

TOTAL_MEMORY = "floor(node_memory_MemTotal_bytes/(1024*1024)*on(pod)group_left(nodename)(node_uname_info))"

CPU_USAGE = "100-(avg by(pod)(irate(node_cpu_seconds_total{mode='idle'}[10m])*100)*on(pod)group_left(nodename)(node_uname_info))"

MEMORY_USAGE = "( (1 - (avg_over_time(node_memory_Cached_bytes[5m])/1000^2+avg_over_time(node_memory_Buffers_bytes[5m])/1000^2+avg_over_time(node_memory_MemFree_bytes[5m])/1000^2) / (avg_over_time(node_memory_MemTotal_bytes[5m])/1000^2) ) * 100 ) *on (pod) group_left(nodename) node_uname_info"

BANDWIDTH = "sum by(pod)(rate(node_network_receive_bytes_total[5m])) * 8 / 1024 / 1024 * on(pod)group_left(nodename)(node_uname_info)"

TOTAL_DISK_GB = "node_filesystem_size_bytes{mountpoint='/'} / 1000^3 * on(pod) group_left(nodename) node_uname_info"

FREE_DISK_GB = "node_filesystem_avail_bytes{mountpoint='/'} / 1000^3 * on(pod) group_left(nodename) node_uname_info"


# Vertexpool queries

VP_LABELS = "decice_vertexpool_labels"

VP_NODE_INFO = "decice_node_info"

VP_DEVICE_INFO = "decice_device_info * on (device_id) group_left (device_labels) decice_device_labels"


def get_edges_base_query_string(
    nodename: str | None = None,
    vertexpool_selector: str | None = None,
    interval: str = "5m",
) -> str:
    """Get promql query string that returns latencies between nodes and devices"""
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
        + "label_replace(decice_node_info{%s},'self_vertexpool_id','$1','vertexpool_id','(.*)')"
        % (vertexpool_id)
        + "* on(device_id) group_left(target_vertexpool_id)"
        + "label_replace(decice_device_info{%s} , 'target_vertexpool_id' , '$1', 'vertexpool_id', '(.*)')"
        % (vertexpool_id)
        + ")"
        + "OR"
        + "("
        + "avg_over_time(decice_ping_latency_ms{target_type='node'%s}[%s])"
        % (node_filter, interval)
        + "* on(nodename) group_left(self_vertexpool_id)"
        + "label_replace(decice_node_info{%s},'self_vertexpool_id','$1','vertexpool_id','(.*)')"
        % (vertexpool_id)
        + "*on(target_name) group_left(target_vertexpool_id)"
        + "label_replace(label_replace(decice_node_info{%s},'target_vertexpool_id','$1','vertexpool_id','(.*)'),'target_name','$1','nodename','(.*)')"
        % (vertexpool_id)
        + ")"
    )
    return q


def get_vertexpool_links_string(interval: str = "5m") -> str:
    """Get promql query string that returns latencies between vertexpools"""
    base_query = get_edges_base_query_string(interval=interval)
    q = "avg by (target_vertexpool_id,self_vertexpool_id)(" + base_query + ")"
    return q


def get_power_consumption_queries() -> list[str]:
    """
    Safely retrieves the power consumption queries from settings at runtime,
    not at import time.
    """
    settings = get_settings()
    return settings.POWER_CONSUMPTION_PROMQL_QUERIES or []


def get_cluster_info_queries() -> list[ClusterInfoQueryConfig]:
    """
    Safely retrieves the cluster info queries from settings at runtime,
    not at import time.
    """
    settings = get_settings()
    return settings.CLUSTER_INFO_QUERIES or []


def get_node_info_queries() -> list[NodeInfoQueryConfig]:
    """
    Safely retrieves the node info queries from settings at runtime,
    not at import time.
    """
    settings = get_settings()
    return settings.NODE_INFO_QUERIES or []
