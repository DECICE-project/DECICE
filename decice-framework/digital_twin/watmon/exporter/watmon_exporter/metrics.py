from prometheus_client import Counter, Gauge

POST_VERTEXPOOLS_REQUEST_COUNT = Counter(
    "decice_post_vertexpools_request_count",
    "Total number Vertexpools POSTs",
    ["nodename"],
)

PING_ATTEMPS_COUNT = Counter(
    "decice_ping_attempts_total",
    "Total number of ping attempts made by the node",
    ["nodename"],
)
PING_SUCCESS_COUNT = Counter(
    "decice_ping_success_total",
    "Total number of successful ping attempts by the node",
    ["nodename"],
)
PING_FAIL_COUNT = Counter(
    "decice_ping_failed_total",
    "Total number of failed ping attempts by the node",
    ["nodename"],
)
PING_LATENCY = Gauge(
    "decice_ping_latency_ms",
    "Ping latency in milliseconds",
    ["nodename", "target_type", "target_name", "target_device_id"],
)
