from fastapi import APIRouter, status, Depends, HTTPException, Query
from datetime import datetime, timedelta
import json

from core.controller import DTCController, get_dtc_controller
from core.data_model import Node, Link, Job, DeciceDigitalTwin
from core.model_utils import get_all_nodes, get_all_links, get_all_jobs
from core.time_series_schema import TimeSeriesPointWrite, TimeSeriesPointRead, TimeRange
from config.config import service_settings, ServiceSettings
from influxdb_client.rest import ApiException

from api.v1 import *

router = APIRouter()


@router.post("/model_core", status_code=status.HTTP_201_CREATED)
async def write_cluster_data(data: DeciceDigitalTwin, controller: DTCController = Depends(get_dtc_controller)):
    dict = data.model_dump()
    print(dict)
    controller.update_digital_twin(data)
    return status.HTTP_201_CREATED

@router.get("/model_core", status_code=status.HTTP_200_OK)
async def get_data(controller: DTCController = Depends(get_dtc_controller)) -> DeciceDigitalTwin | None:
    return controller.digital_twin

@router.get("/settings/", status_code=status.HTTP_200_OK)
async def get_settings() -> ServiceSettings:
    """Get the current digital twin settings."""
    return service_settings


@router.get("/nodes/", status_code=status.HTTP_200_OK)
async def get_nodes(
    include_vertexpool_id: bool = False, controller: DTCController = Depends(get_dtc_controller)
) -> list[Node]:
    """Get all nodes with optional vertexpool_id info included."""
    return get_all_nodes(digital_twin_data=controller.digital_twin, include_vertexpool_id=include_vertexpool_id)


@router.get("/links/", status_code=status.HTTP_200_OK)
async def get_links(controller: DTCController = Depends(get_dtc_controller)) -> list[Link]:
    """Get all links"""
    return get_all_links(digital_twin=controller.digital_twin)


@router.get("/jobs/", status_code=status.HTTP_200_OK)
async def get_jobs(controller: DTCController = Depends(get_dtc_controller)) -> list[Job]:
    """Get all jobs"""
    return get_all_jobs(digital_twin=controller.digital_twin)


@router.post("/timeseries/write_record/", status_code=status.HTTP_201_CREATED)
async def write_to_influxdb(
    tsp: list[TimeSeriesPointWrite], bucket: str, controller: DTCController = Depends(get_dtc_controller)
):
    """Write custom timeseries point to InfluxDB"""
    try:
        controller.time_series_client.write_points(tsp, bucket)
    except ApiException as e:
        try:
            body = json.loads(e.body)
        except json.JSONDecodeError:
            body = {"error": e.body}
        body["message"] = f"Error writing to InfluxDB: {body.get('message', 'Unknown error')}"
        raise HTTPException(status_code=e.status, detail=body)
    return 201


@router.post("/timeseries/read_record/", status_code=status.HTTP_200_OK)
async def read_from_influxdb(
    tsr: TimeSeriesPointRead, controller: DTCController = Depends(get_dtc_controller)
) -> list[dict]:
    """Write custom timeseries point to InfluxDB"""
    try:
        resp = controller.time_series_client.read_custom(tsr)
    except ApiException as e:
        try:
            body = json.loads(e.body)
        except json.JSONDecodeError:
            body = {"error": e.body}
        body["message"] = f"Error writing to InfluxDB: {body.get('message', 'Unknown error')}"
        raise HTTPException(status_code=e.status, detail=body)
    return resp


def convert_datetime_keys_to_str(d: dict[datetime, DeciceDigitalTwin]) -> dict[str, DeciceDigitalTwin]:
    return {date.isoformat(): model for date, model in d.items()}


@router.get("/past_snapshots/")
async def past_snapshots(
    start: datetime | str = Query(
        "-30m",
        description="Start time as ISO8601 datetime or relative time string (e.g. '-30m' for 30 minutes ago)",
        example="-30m",
    ),
    stop: datetime | str | None = Query(
        None,
        description="Stop time as ISO8601 datetime or relative time string (e.g. '-10m', defaults to now if omitted)",
        examples=[None, "-10m"],
    ),
    controller: DTCController = Depends(get_dtc_controller),
) -> dict[str, DeciceDigitalTwin]:
    "Returns past snapshots of DigitalTwin sorted by time"
    tr = TimeRange(start=start, stop=stop)
    ret: dict[datetime, DeciceDigitalTwin] = controller.time_series_client.get_historical_snapshot(time_range=tr)
    return convert_datetime_keys_to_str(ret)


@router.get("/past_snapshots/{snapshot_date}")
async def get_a_snapshot(
    snapshot_date: datetime, controller: DTCController = Depends(get_dtc_controller)
) -> DeciceDigitalTwin:
    """
    Return a single snapshot for the given timestamp by querying a tiny time range
    """
    # Create a tiny time range hack to satisfy Flux range requirement
    start = snapshot_date
    print(start)
    stop = snapshot_date + timedelta(microseconds=1)
    tr = TimeRange(start=start, stop=stop)
    snapshots: dict[datetime, DeciceDigitalTwin] = controller.time_series_client.get_historical_snapshot(time_range=tr)

    if start in snapshots:
        return snapshots[start]
    else:
        raise HTTPException(status_code=404, detail="Snapshot not found")
