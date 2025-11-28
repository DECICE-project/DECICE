from fastapi import HTTPException

from watmon_service.db.vertexpool import VertexpoolManager
from watmon_service.db.models import DeviceDB, VertexpoolDB
from watmon_service.schema import NodeInVP, VertexPool, DeviceInVp, Device


def convert_device_response_list(
    device_list: list[DeviceDB], include_vertexpool_id: bool = True
) -> list[DeviceInVp] | list[Device]:
    devices = []
    for dev in device_list:
        dev_labels = []
        for label in dev.labels:
            dev_labels.append(label.key + ":" + label.value)
        if not dev_labels:
            dev_labels = None
        if include_vertexpool_id:
            devices.append(
                Device(
                    id=dev.device_id,
                    name=dev.devicename,
                    ip=dev.ip,
                    labels=dev_labels,
                    vertexpool_id=dev.vertexpool_id,
                )
            )
        else:
            devices.append(
                DeviceInVp(
                    id=dev.device_id, name=dev.devicename, ip=dev.ip, labels=dev_labels
                )
            )
    return devices


def convert_device_response(device: DeviceDB) -> Device:
    dev_labels = []
    for label in device.labels:
        dev_labels.append(label.key + ":" + label.value)
    return Device(
        id=device.device_id,
        name=device.devicename,
        labels=dev_labels,
        ip=device.ip,
        vertexpool_id=device.vertexpool_id,
    )


def convert_vertexpool_response(vp: VertexpoolDB) -> VertexPool:
    nodes = [NodeInVP(nodename=node.nodename, ip=node.ip) for node in vp.nodes]
    devices = convert_device_response_list(vp.devices, include_vertexpool_id=False)
    labels = []
    for label in vp.labels:
        labels.append(label.key + ":" + label.value)
    return VertexPool(vertexpool_id=vp.id, devices=devices, nodes=nodes, labels=labels)


async def convert_vertexpool_response_list(
    manager: VertexpoolManager,
) -> list[VertexPool]:
    vertexpools: list[VertexPool] = []
    try:
        for vp in await manager.get_vertexpools():
            vp_response = convert_vertexpool_response(vp)
            vertexpools.append(vp_response)
        return vertexpools
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
