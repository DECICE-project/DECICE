from prometheus_client import Counter, Gauge

# Define a Counter metric
GET_NODES_REQUEST_COUNT = Counter("get_nodes_request_count", "Total number GET /nodes/ of requests")

DECICE_DEVICE_INFO_LABELS = ["device_id", "devicename", "device_ip", "vertexpool_id"]
DECICE_DEVICE_LABELS_LABELS = ["device_id", "device_labels"]
DECICE_DEVICE_INFO = Gauge("decice_device_info", "Devices info", DECICE_DEVICE_INFO_LABELS)
DECICE_DEVICE_LABELS = Gauge("decice_device_labels", "Labels for the devices", DECICE_DEVICE_LABELS_LABELS)

DECICE_NODE_INFO_LABELS = ["nodename", "node_ip", "vertexpool_id"]
DECICE_NODE_INFO = Gauge("decice_node_info", "Node, vertexpool relationships", DECICE_NODE_INFO_LABELS)

DECICE_VERTEXPOOL_LABELS_LABELS = ["vertexpool_id", "vertexpool_labels"]
DECICE_VERTEXPOOL_LABELS = Gauge("decice_vertexpool_labels", "Vertexpool labels", DECICE_VERTEXPOOL_LABELS_LABELS)
