from digital_twin.core.data_model import DeciceDigitalTwin, Node, Link, Device, Vertexpool, Metrics
from digital_twin.core.model_utils import get_all_links, get_devices_vp_tuple, get_nodes_vp_tuple
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from digital_twin.core.time_series_schema import TimeSeriesPointWrite, TimeSeriesPointRead, TimeRange
from typing import Any
from abc import ABC, abstractmethod
import time
from datetime import datetime
from datetime import timezone
from collections import defaultdict
import json


class TimeSeriesClient(ABC):
    """
    Abstract base class for interacting with influxdb.

    Implement read and write methods when extending
    """

    def __init__(self, url: str, org: str, token: str, bucket: str) -> None:
        self.bucket = bucket
        self.client = self._initialize_client(url, token, org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()

    def _initialize_client(self, url: str, token: str, org: str) -> InfluxDBClient:
        return InfluxDBClient(url=url, token=token, org=org)

    def parse_point(self, measurement: str, tags: dict, fields: dict, timestamp) -> Point:
        p = Point(measurement).time(timestamp)
        if tags:
            for key, valu in tags.items():
                p.tag(key, valu)
        if fields:
            for key, value in fields.items():
                p.field(key, value)
        return p

    def write_points(self, data: list[TimeSeriesPointWrite], bucket: str):
        points = []
        for tsp in data:
            points.append(self.parse_point(tsp.measurement, tsp.tags, tsp.fields, tsp.timetamp))
        self.write_api.write(bucket=bucket, org=self.client.org, record=points)

    def read_custom(self, tsr: TimeSeriesPointRead, group_by_time: bool = False) -> list | dict[datetime, dict]:
        query = f"""
        from(bucket: "{tsr.bucket}")
        |> range(start: {tsr.time_range.start.isoformat()}, stop: {tsr.time_range.stop.isoformat()})
        |> filter(fn: (r) => r._measurement == "{tsr.measurement}")
        """

        for key, val in tsr.tags.items():
            query += f'\n|> filter(fn: (r) => r["{key}"] == "{val}")'

        # query += '\n|> keep(columns: ["_time", "_field", "_value"])'
        if group_by_time:
            query += """
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """

        result = self.query_api.query(query)

        if group_by_time:
            grouped = {}
            for table in result:
                for record in table.records:
                    time = record.get_time()
                    fields = {
                        k: v
                        for k, v in record.values.items()
                        if k not in ["_start", "_stop", "result", "table", "_measurement", "_time"]
                    }
                    if time in grouped:
                        grouped[time].append(fields)
                    else:
                        grouped[time] = [fields]

            # Sort by time descending
            grouped_sorted = dict(sorted(grouped.items(), key=lambda x: x[0], reverse=True))

            return grouped_sorted
        else:
            return [{**record.values} for table in result for record in table.records]

    @abstractmethod
    def write(self, data):
        pass

    @abstractmethod
    def read(self) -> Any:
        pass


class DTCTimeSeries(TimeSeriesClient):
    def write(self, data: DeciceDigitalTwin) -> None:
        points = self.convert_dt_model_to_points(data)
        self.write_api.write(bucket=self.bucket, org=self.client.org, record=points)

    def read(self) -> list[str]:
        query = f"""from(bucket: "{self.bucket}") |> range(start: -20m)"""
        tables = self.query_api.query(query, org=self.client.org)
        json_list = []

        for table in tables:
            for record in table.records:
                json_list.append(record.values)

        return json_list

    def convert_dt_model_to_points(self, data: DeciceDigitalTwin) -> list[Point]:
        points = []
        if not data.lastUpdated:
            data.lastUpdated = int(time.time() * 1e9)
        timestamp = datetime.fromtimestamp(data.lastUpdated, tz=timezone.utc)
        node_points = self.get_node_points(get_nodes_vp_tuple(data), timestamp)
        device_points = self.get_device_points(get_devices_vp_tuple(data), timestamp)
        vertexpool_label_points = self.get_vertexpool_label_points(data, timestamp)
        link_points = self.get_link_points(get_all_links(data), timestamp)
        cluster_info_points = self.get_cluster_info_points(data.cluster_info, timestamp)
        points.extend(node_points + device_points + link_points + vertexpool_label_points + cluster_info_points)
        return points

    def get_vertexpool_label_points(self, data: DeciceDigitalTwin, timestamp) -> list[Point]:
        points = []
        if not data.vertexpools:
            return points

        for vp in data.vertexpools:
            points.append(
                Point("vertexpools")
                .tag("vertexpool_id", vp.id)
                .field("vertexpool_labels", json.dumps(vp.vertexpool_labels))
                .time(timestamp)
            )
        return points

    def get_node_points(self, nodes: list[tuple[Node, str]], timestamp: datetime) -> list[Point]:
        points = []
        for n in nodes:
            node = n[0]
            vp_id = n[1]
            node.metrics.model_config
            point = (
                Point("node").tag("name", node.name).field("id", node.id).field("system", node.system).time(timestamp)
            )
            if node.metrics:
                node_metrics = node.metrics.model_dump(exclude_unset=True)
                for key, value in node_metrics.items():
                    point.field(key, value)
            if node.node_info:
                point.field("node_info", json.dumps(node.node_info))
            node_vertexpool_id = vp_id
            if node_vertexpool_id is not None:
                point.tag("vertexpool_id", node_vertexpool_id)
            points.append(point)
        return points
    
    def get_cluster_info_points(self, cluster_info: dict, timestamp: datetime) -> list[Point]:
        points = []
        point = Point("cluster_info").time(timestamp)
        for key, value in cluster_info.items():
            if isinstance(value, (dict, list)):
                point.field(key, json.dumps(value))
            else:
                point.field(key, value)
        points.append(point)
        return points

    def get_device_points(self, devices: list[tuple[Device, str]], timestamp: datetime) -> list[Point]:
        points = []
        for d in devices:
            device = d[0]
            point = Point("device").tag("name", device.name).field("id", device.id).field("up", 1).time(timestamp)
            if device.device_info:
                point.field("device_info", json.dumps(device.device_info))
            if device.labels:
                point.field("labels", json.dumps(device.labels))
            device_vertexpool_id = d[1]
            if device_vertexpool_id is not None:
                point.tag("vertexpool_id", device_vertexpool_id)
            points.append(point)
        return points

    def get_link_points(self, links: list[Link], timestamp: datetime) -> list[Point]:
        points = []
        for link in links:
            point = (
                Point("link")
                .tag("vertexpool_a_id", link.vertexpool_a_id)
                .tag("vertexpool_b_id", link.vertexpool_b_id)
                .field("network_delay_ms", link.network_delay_ms)
                .time(timestamp)
            )
            points.append(point)
        return points

    def get_historical_snapshot(self, time_range: TimeRange) -> dict[datetime, DeciceDigitalTwin]:
        return_dict: dict[datetime, DeciceDigitalTwin] = defaultdict(DeciceDigitalTwin)
        vertexpools: dict[datetime, dict] = self.read_custom(
            TimeSeriesPointRead(time_range=time_range, measurement="vertexpools", bucket="cluster_snapshot"),
            group_by_time=True,
        )
        nodes: dict[datetime, dict] = self.read_custom(
            TimeSeriesPointRead(time_range=time_range, measurement="node", bucket="cluster_snapshot"),
            group_by_time=True,
        )
        devices: dict[datetime, dict] = self.read_custom(
            TimeSeriesPointRead(time_range=time_range, measurement="device", bucket="cluster_snapshot"),
            group_by_time=True,
        )
        links: dict[datetime, dict] = self.read_custom(
            TimeSeriesPointRead(time_range=time_range, measurement="link", bucket="cluster_snapshot"),
            group_by_time=True,
        )
        cluster_info: dict[datetime, dict] = self.read_custom(
            TimeSeriesPointRead(time_range=time_range, measurement="cluster_info", bucket="cluster_snapshot"),
            group_by_time=True,
        )
        for timestamp, vertexvalues in vertexpools.items():
            # init DT
            id_map: dict[str, Vertexpool] = defaultdict(Vertexpool)
            dt = return_dict[timestamp]
            dt.lastUpdated = timestamp.timestamp()

            # initialize vertexpools
            for vp_point in vertexvalues:
                vp = id_map[vp_point.get("vertexpool_id")]
                vp_labels = vp_point.get("vertexpool_labels")
                if vp_labels:
                    vp.vertexpool_labels = json.loads(vp_labels)
                vp.id = vp_point.get("vertexpool_id")
            # add nodes
            node_points: dict = nodes.get(timestamp, {})
            for np in node_points:
                node_args = {k: v for k, v in np.items() if k in Node.model_fields}
                node_info = node_args.get("node_info")
                node_vertexpool: str | None = np.get("vertexpool_id", None)
                if node_info:
                    node_args["node_info"] = json.loads(node_info)
                node_metric_args = {k: v for k, v in np.items() if k in Metrics.model_fields}
                node_metrics = Metrics(**node_metric_args)
                node = Node(**node_args, metrics=node_metrics)
                id_map[node_vertexpool].nodes.append(node)
            # add devices
            device_points: dict = devices.get(timestamp, {})
            for dev in device_points:
                device_args = {k: v for k, v in dev.items() if k in Device.model_fields}
                device_info = device_args.get("device_info")
                device_labels = device_args.get("labels")
                device_vertexpool: str | None = dev.get("vertexpool_id", None)
                if device_info:
                    device_args["device_info"] = json.loads(device_info)
                if device_labels:
                    device_args["labels"] = json.loads(device_labels)
                device = Device(**device_args)
                id_map[device_vertexpool].devices.append(device)

            # finalize vertexpools
            for _, vp in id_map.items():
                dt.vertexpools.append(vp)
            # add links
            link_points: dict[dict] = links.get(timestamp, {})
            for lnk in link_points:
                link_args = {k: v for k, v in lnk.items() if k in Link.model_fields}
                link = Link(**link_args)
                dt.links.append(link)

            # add cluster info
            cluster_info_points: dict[dict] = cluster_info.get(timestamp, {})
            if cluster_info_points:
                cluster_info_dict = {}
                for key,value in cluster_info_points[0].items():
                    # value can be a number or nested json string
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            continue
                    cluster_info_dict[key] = value
                dt.cluster_info = cluster_info_dict

        return return_dict
