from aiopromql import PrometheusAsync
from watmon_service.schema import (
    Node,
    Device,
    VertexPool,
    Label,
    NodePatch,
    DevicePost,
    DevicePatch,
)
from watmon_service.db.vertexpool import VertexpoolManager, get_vertexpool_manager
from contextlib import asynccontextmanager
from watmon_service.db.session import init_db
from fastapi import HTTPException, FastAPI, Depends, Body
from typing import Annotated
from prometheus_client import make_asgi_app
from watmon_service.prometheus.metrics import GET_NODES_REQUEST_COUNT
from watmon_service.settings import read_settings, Settings
from watmon_service.node_collector import NodeSniffer
from watmon_service.prometheus.exporter import MetricUpdater
from watmon_service.agent_updater import AgentUpdater
from watmon_service.common import (
    convert_device_response,
    convert_vertexpool_response,
    convert_device_response_list,
    convert_vertexpool_response_list,
)
from watmon_service.prometheus.api import router as prom_router
from watmon_service.prometheus.api import prometheus_connection
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from kubernetes import client, config
from watmon_service.prometheus.promql_query import construct_typed_graph

settings: Settings = read_settings()


async def _update_nodes(ns: NodeSniffer):
    await ns.sync_node_memory()
    await ns.stop()


@asynccontextmanager
async def lifespan(_: FastAPI):
    use_kube_config = False
    cfg = client.Configuration()
    try:
        config.load_incluster_config(client_configuration=cfg)
        use_kube_config = True
    except config.ConfigException:
        print("Unable to use incluster config. Will check for kube-config file.)")
        try:
            config.load_kube_config(client_configuration=cfg)
            use_kube_config = True
        except config.config_exception.ConfigException:
            print("Unable to use kube-config file. Will use Prometheus instead.")
    if use_kube_config:
        k8s_client = client.ApiClient(configuration=cfg)
        v1_api = client.CoreV1Api(api_client=k8s_client)
    else:
        v1_api = None

    agent_updater = AgentUpdater(settings, v1_api)
    node_sniffer = NodeSniffer(settings, v1_api)
    metric_updater = MetricUpdater()
    app.state.agent_updater = agent_updater
    app.state.node_sniffer = node_sniffer
    app.state.metric_updater = metric_updater
    #
    await init_db()
    await _update_nodes(node_sniffer)
    asyncio.create_task(metric_updater.run())
    asyncio.create_task(node_sniffer.run())
    asyncio.create_task(agent_updater.run())
    yield


app = FastAPI(
    docs_url="/", lifespan=lifespan, title="WATMON-Service API", version="0.2.3"
)
metrics_app = make_asgi_app()
app.mount("/metrics/", metrics_app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(prom_router)


@app.get("/settings", response_model=Settings)
async def get_settings():
    return settings


@app.get("/update_nodes/", status_code=204)
async def update_nodes():
    """Reads the nodes from prometheus then, updates the nodes in API"""
    await _update_nodes(app.state.node_sniffer)


@app.get("/update_metrics/", status_code=204)
async def update_metrics():
    """Updates metrics endpoint"""
    await app.state.metric_updater.update_metrics()


@app.post("/nodes/", status_code=201)
async def add_node(
    node: Node, manager: VertexpoolManager = Depends(get_vertexpool_manager)
):
    try:
        node = await manager.add_node(
            nodename=node.nodename, vertexpool_id=node.vertexpool_id, ip=node.ip
        )
        return Node(
            nodename=node.nodename, vertexpool_id=node.vertexpool_id, ip=node.ip
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/devices/", status_code=201)
async def add_device(
    device: DevicePost, manager: VertexpoolManager = Depends(get_vertexpool_manager)
):
    try:
        device_in_db = await manager.add_device(device)
        return convert_device_response(device_in_db)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/nodes/{nodename}/move", status_code=201)
async def move_node(
    nodename: str,
    new_vertexpool_id: int | None = None,
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
):
    try:
        await manager.move_node_to_vertexpool(
            nodename=nodename, new_vertexpool_id=new_vertexpool_id
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/nodes/{nodename}", status_code=200)
async def patch_node(
    nodename: str,
    node: NodePatch,
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
):
    try:
        node_db = await manager.patch_node(nodename=nodename, ip=node.ip)
        if node_db:
            return Node(
                nodename=nodename, vertexpool_id=node_db.vertexpool_id, ip=node_db.ip
            )
        else:
            raise HTTPException(500, detail="Something went terribly wrong")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/devices/{device_id}/", status_code=200)
async def patch_device(
    device_id: int,
    device: DevicePatch,
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
):
    try:
        dev = await manager.patch_device(
            device_id, name=device.name, labels=device.labels, ip=device.ip
        )
        if dev:
            return convert_device_response(dev)
        else:
            raise HTTPException(500, detail="Something went terribly wrong")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/devices/{device_id}/add_label", status_code=200)
async def add_device_label(
    device_id: int,
    label: Label,
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
):
    try:
        dev = await manager.add_device_label(
            device_id, label.label_key, label.label_value
        )
        if dev:
            return convert_device_response(dev)
        else:
            raise HTTPException(500, detail="Something went terribly wrong")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/devices/{device_id}/move", status_code=201)
async def move_device(
    device_id: int,
    new_vertexpool_id: int | None = None,
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
):
    """Moves a device to vertexpool.
    If new_vertexpool_id is None, it will be moved to a new vertexpool with auto-incremented ID.
    """
    try:
        await manager.move_device_to_vertexpool(
            device_id=device_id, new_vertexpool_id=new_vertexpool_id
        )
        return
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/nodes/{nodename}", status_code=204)
async def delete_node(
    nodename: str, manager: VertexpoolManager = Depends(get_vertexpool_manager)
):
    try:
        await manager.delete_node(nodename=nodename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/nodes/",
)
async def get_nodes_list(
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
) -> list[Node]:
    GET_NODES_REQUEST_COUNT.inc()
    try:
        return [
            Node(nodename=node.nodename, vertexpool_id=node.vertexpool_id, ip=node.ip)
            for node in await manager.get_nodes()
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/devices/{device_id}", status_code=204)
async def delete_device(
    device_id: int, manager: VertexpoolManager = Depends(get_vertexpool_manager)
):
    try:
        await manager.delete_device(device_id=device_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/devices/",
)
async def get_devices_list(
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
) -> list[Device]:
    try:
        return convert_device_response_list(await manager.get_devices())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/vertexpools/")
async def get_vertexpools(
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
) -> list[VertexPool]:
    return await convert_vertexpool_response_list(manager=manager)


@app.put("/vertexpool/{vertexpool_id}/")
async def edit_vertexpool_labels(
    vertexpool_id: int,
    labels: Annotated[list[Label] | None, Body()],
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
):
    try:
        vertexpool = await manager.patch_vertexpool_labels(vertexpool_id, labels)
        if vertexpool:
            return convert_vertexpool_response(vertexpool)
        else:
            raise HTTPException(status_code=500, detail="something went wrong")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/vertexpool/{vertexpool_id}/add_label", status_code=200)
async def add_vertexpool_label(
    vertexpool_id: int,
    label: Label,
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
):
    try:
        vertexpool = await manager.add_vertexpool_label(
            vertexpool_id, label.label_key, label.label_value
        )
        if vertexpool:
            return convert_vertexpool_response(vertexpool)
        else:
            raise HTTPException(500, detail="Something went terribly wrong")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/vertexpool/group_vertices", status_code=200)
async def group_vertices(
    interval: str = settings.promql.network_delay_range_selector,
    prometheus_connection: PrometheusAsync = Depends(prometheus_connection),
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
) -> None:
    """
    Groups all vertices to VertexPools automatically via structral equivalence.
    """
    tg = await construct_typed_graph(interval, prometheus_connection)
    groups = tg.get_structural_equivalence()
    vpid_to_group: dict[str, list[str]] = {}
    for group in groups:
        new_vertexpool_id = None
        for vertice in group:
            if vertice.type == "node":
                if new_vertexpool_id is None:
                    await manager.move_node_to_vertexpool(nodename=vertice.name)
                    # check the new vertexpool ID of the node from DB
                    node = await manager.get_node(nodename=vertice.name)
                    new_vertexpool_id = node.vertexpool_id
                else:
                    await manager.move_node_to_vertexpool(
                        nodename=vertice.name, new_vertexpool_id=new_vertexpool_id
                    )

            elif vertice.type == "device":
                if new_vertexpool_id is None:
                    await manager.move_device_to_vertexpool(
                        device_id=int(vertice.device_id)
                    )
                    # check the new vertexpool ID of the device from DB
                    device = await manager.get_device(device_id=int(vertice.device_id))
                    new_vertexpool_id = device.vertexpool_id
                else:
                    await manager.move_device_to_vertexpool(
                        device_id=int(vertice.device_id),
                        new_vertexpool_id=new_vertexpool_id,
                    )
        vpid_to_group[new_vertexpool_id] = group

    return {"message": "Vertices grouped successfully", "groups": vpid_to_group}


@app.get("/vertexpool/reset_vertexpools", status_code=200)
async def reset_vertexpools(
    manager: VertexpoolManager = Depends(get_vertexpool_manager),
):
    """
    Put all vertices to sperate vertexpools.
    """
    try:
        for node in await manager.get_nodes():
            await manager.move_node_to_vertexpool(nodename=node.nodename)
        for device in await manager.get_devices():
            await manager.move_device_to_vertexpool(device_id=device.device_id)
        return {"message": "Vertexpools reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = read_settings().api_port
    uvicorn.run(app, host="0.0.0.0", port=port)
