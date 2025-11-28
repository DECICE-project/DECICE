from fastapi import APIRouter, status, Depends, HTTPException, Query
from datetime import datetime, timedelta
import json

from digital_twin.core.controller import DTCController, get_dtc_controller
from digital_twin.core.data_model import Node, Link, Job, DeciceDigitalTwin, DeciceDigitalTwinV1
from digital_twin.core.model_utils import get_all_nodes, get_all_links, get_all_jobs
from digital_twin.core.time_series_schema import TimeSeriesPointWrite, TimeSeriesPointRead, TimeRange
from digital_twin.config.config import service_settings, ServiceSettings
from influxdb_client.rest import ApiException

router = APIRouter()


@router.post("/model_core/", status_code=status.HTTP_201_CREATED)
async def write_cluster_data(data: DeciceDigitalTwinV1 | DeciceDigitalTwin, controller: DTCController = Depends(get_dtc_controller)):
    dict = data.model_dump()
    # if isinstance(data, DeciceDigitalTwinV1): cast it to DeciceDigitalTwin
    if isinstance(data, DeciceDigitalTwinV1):
        data_converted = DeciceDigitalTwin(
            lastUpdated=data.lastUpdated,
            vertexpools=data.vertexpools,
            links=data.links,
            jobs=data.jobs,
        )
        data = data_converted
    print(dict)
    controller.update_digital_twin(data)
    return status.HTTP_201_CREATED

@router.get("/model_core/", status_code=status.HTTP_200_OK)
async def get_data(controller: DTCController = Depends(get_dtc_controller)) -> DeciceDigitalTwinV1 | None:
    # cast DeciceDigitalTwin to DeciceDigitalTwinV1
    if isinstance(controller.digital_twin, DeciceDigitalTwin):
        data_converted = DeciceDigitalTwinV1(
            lastUpdated=controller.digital_twin.lastUpdated,
            vertexpools=controller.digital_twin.vertexpools,
            links=controller.digital_twin.links,
            jobs=controller.digital_twin.jobs,
        )
        return data_converted
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
) -> dict[str, DeciceDigitalTwinV1]:
    "Returns past snapshots of DigitalTwin sorted by time"
    tr = TimeRange(start=start, stop=stop)
    ret: dict[datetime, DeciceDigitalTwin] = controller.time_series_client.get_historical_snapshot(time_range=tr)
    # Cast DeciceDigitalTwin to DeciceDigitalTwinV1
    ret_v1: dict[datetime, DeciceDigitalTwinV1] = {}
    for date, model in ret.items():
        data_converted = DeciceDigitalTwinV1(
            lastUpdated=model.lastUpdated,
            vertexpools=model.vertexpools,
            links=model.links,
            jobs=model.jobs,
        )
        ret_v1[date] = data_converted
    return convert_datetime_keys_to_str(ret_v1)


@router.get("/past_snapshots/{snapshot_date}")
async def get_a_snapshot(
    snapshot_date: datetime, controller: DTCController = Depends(get_dtc_controller)
) -> DeciceDigitalTwinV1:
    """
    Return a single snapshot for the given timestamp by querying a tiny time range
    """
    # Create a tiny time range hack to satisfy Flux range requirement
    start = snapshot_date
    print(start)
    stop = snapshot_date + timedelta(microseconds=1)
    tr = TimeRange(start=start, stop=stop)
    snapshots: dict[datetime, DeciceDigitalTwin] = controller.time_series_client.get_historical_snapshot(time_range=tr)
    # Cast DeciceDigitalTwin to DeciceDigitalTwinV1
    ret_v1: dict[datetime, DeciceDigitalTwinV1] = {}
    for date, model in snapshots.items():
        data_converted = DeciceDigitalTwinV1(
            lastUpdated=model.lastUpdated,
            vertexpools=model.vertexpools,
            links=model.links,
            jobs=model.jobs,
        )
        ret_v1[date] = data_converted

    if start in ret_v1:
        return ret_v1[start]
    else:
        raise HTTPException(status_code=404, detail="Snapshot not found")
