# a fastapi router
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from aiopromql import PrometheusAsync
from typing import AsyncGenerator

from watmon_service.prometheus.promql_schema import (
    UniDirectionalVertexpoolMs,
    UniDirectionalVertexMs,
)
from watmon_service.schema import VertexPool, Node, Device
from watmon_service.settings import read_settings, Settings
from watmon_service.common import convert_vertexpool_response_list
from watmon_service.db.vertexpool import VertexpoolManager, get_vertexpool_manager
from watmon_service.prometheus.promql_query import (
    get_vertexpools,
    get_vertexpool_links,
    get_node_to_x_latency,
)
from watmon_service.prometheus.promql_schema import PromVertexpool

settings: Settings = read_settings()
router = APIRouter(prefix="/metric_api", tags=["Prometheus Link Metrics"])


async def prometheus_connection() -> AsyncGenerator[PrometheusAsync, None]:
    client = PrometheusAsync(settings.prometheus_url, 4)
    try:
        yield client
    finally:
        await client.aclose()


class ExpandedVertices(BaseModel):
    vertexpools: list[VertexPool]
    selected_vertexpool: VertexPool | None = None


class ExpandedGraph(BaseModel):
    links: list[UniDirectionalVertexpoolMs]
    expanded_vertices: ExpandedVertices


@router.get("/vertexpools")
async def get_all_vertexpools_metrics(
    prometheus_connection: PrometheusAsync = Depends(prometheus_connection),
) -> list[PromVertexpool]:
    return await get_vertexpools(prometheus_connection)


@router.get("/vertexpool_links")
async def get_unidirectional_vertexpool_links(
    prometheus_connection: PrometheusAsync = Depends(prometheus_connection),
    interval: str = settings.promql.network_delay_range_selector,
) -> list[UniDirectionalVertexpoolMs]:
    return await get_vertexpool_links(prometheus_connection, True, interval)


@router.get("/raw_edges")
async def get_raw_edges(
    nodename: str | None = None,
    vertexpool_id: str | None = None,
    interval: str = settings.promql.network_delay_range_selector,
    prometheus_connection: PrometheusAsync = Depends(prometheus_connection),
) -> list[UniDirectionalVertexMs]:
    return await get_node_to_x_latency(
        prometheus_connection, nodename, vertexpool_id, interval, True
    )


@router.get("/expanded_vertexpools")
async def get_expanded_vertexpools_view(
    vertexpool_id: str | None = None,
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
) -> ExpandedVertices:
    vertexpools = await convert_vertexpool_response_list(manager)
    return_vertexpool = []
    current_vertexpool: PromVertexpool | None = None
    nodes: list[Node] = []
    devices: list[Device] = []
    if vertexpool_id:
        # create a new vertexpool list where vertexpool_id is not in the list
        for vp in vertexpools:
            if str(vp.vertexpool_id) != vertexpool_id:
                return_vertexpool.append(vp)
            else:
                # nodes = vp.nodes
                # devices = vp.devices
                current_vertexpool = vp
    else:
        return_vertexpool = vertexpools
    return ExpandedVertices(
        vertexpools=return_vertexpool,
        selected_nodes=nodes,
        selected_devices=devices,
        selected_vertexpool=current_vertexpool,
    )


@router.get("/expanded_graph/")
async def get_expanded_vertexpool_graph(
    vertexpool_id: str | None = None,
    interval: str = settings.promql.network_delay_range_selector,
    prometheus_connection: PrometheusAsync = Depends(prometheus_connection),
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
) -> ExpandedGraph:
    links = await get_vertexpool_links(prometheus_connection, True, interval=interval)
    expanded_view = await get_expanded_vertexpools_view(vertexpool_id, manager=manager)
    raw_to_vertexpool_link_inner: list[UniDirectionalVertexpoolMs] = []
    raw_to_vertexpool_link_outer: list[UniDirectionalVertexpoolMs] = []
    remaining_links: list[UniDirectionalVertexpoolMs] = []
    if vertexpool_id:
        inner_links = await get_raw_edges(
            vertexpool_id=vertexpool_id, prometheus_connection=prometheus_connection
        )

        # find and remove the link with given vertexpool_id
        node_device_name_list: list[str] = []
        if (
            expanded_view.selected_vertexpool
            and expanded_view.selected_vertexpool.nodes is not None
        ):
            for node in expanded_view.selected_vertexpool.nodes:
                # check if node has attribute name
                if hasattr(node, "nodename"):
                    node_device_name_list.append(node.nodename)
        if (
            expanded_view.selected_vertexpool
            and expanded_view.selected_vertexpool.devices is not None
        ):
            for device in expanded_view.selected_vertexpool.devices:
                if hasattr(device, "name"):
                    node_device_name_list.append(device.name)

        for link in links:
            # link.vertexpool_a or link.vertexpool_b should be equal to vertexpool_id
            if link.vertexpool_a == vertexpool_id:
                if link.vertexpool_b != vertexpool_id:
                    for node_device in node_device_name_list:
                        converted_link = UniDirectionalVertexpoolMs(
                            vertexpool_a=node_device,
                            vertexpool_b=link.vertexpool_b,
                            value=link.value,
                            lastUpdated=link.lastUpdated,
                        )
                        raw_to_vertexpool_link_outer.append(converted_link)
                        # remove the link from vp_links
            elif link.vertexpool_b == vertexpool_id:
                for node_device in node_device_name_list:
                    converted_link = UniDirectionalVertexpoolMs(
                        vertexpool_a=link.vertexpool_a,
                        vertexpool_b=node_device,
                        value=link.value,
                        lastUpdated=link.lastUpdated,
                    )
                    raw_to_vertexpool_link_outer.append(converted_link)
            else:
                remaining_links.append(link)

        for link in inner_links:
            raw_to_vertexpool_link_inner.append(
                UniDirectionalVertexpoolMs(
                    vertexpool_a=link.vertex_a,
                    vertexpool_b=link.vertex_b,
                    value=link.value,
                    lastUpdated=link.lastUpdated,
                )
            )
        links = (
            raw_to_vertexpool_link_outer
            + remaining_links
            + raw_to_vertexpool_link_inner
        )

    return ExpandedGraph(
        links=links,
        expanded_vertices=expanded_view,
    )
