from core.data_model import DeciceDigitalTwin, Pod, Node, Job, Link, Device
from copy import deepcopy


def get_all_pods(digital_twin_data: DeciceDigitalTwin) -> list[Pod]:
    pod_list = []
    jobs = digital_twin_data.jobs
    if jobs:
        for job in jobs:
            if job.pods:
                for pod in job.pods:
                    pod_list.append(pod)
    return pod_list


def get_all_nodes(digital_twin_data: DeciceDigitalTwin | None, include_vertexpool_id: bool) -> list[Node]:
    """
    Retrieve all nodes from the provided digital twin data.

    Args:
        digital_twin_data (DeciceDigitalTwin | None): The digital twin data containing vertexpools and nodes.
        include_vertexpool_id (bool): Whether to include the vertexpool ID in the node_info dictionary.

    Returns:
        list[Node]: A list of nodes, potentially including the vertexpool ID.
    """
    nodes = []
    if not digital_twin_data:
        return nodes
    for vertexpool in digital_twin_data.vertexpools or []:
        for node in vertexpool.nodes or []:
            # Create a copy of the node to avoid mutating the original
            node_copy = deepcopy(node)
            if include_vertexpool_id:
                node_copy.node_info = node_copy.node_info or {}
                node_copy.node_info["vertexpool_id"] = vertexpool.id
            nodes.append(node_copy)
    return nodes


def get_nodes_vp_tuple(
    digital_twin_data: DeciceDigitalTwin | None,
) -> list[tuple[Node, str]]:
    """
    Retrieve all nodes from the provided digital twin data.

    Returns:
        list[tuple[Node,str]]: A list of node,vertexpool_id tuple.
    """
    nodes = []
    if not digital_twin_data:
        return nodes
    for vertexpool in digital_twin_data.vertexpools or []:
        for node in vertexpool.nodes or []:
            nodes.append((node, vertexpool.id))
    return nodes


def get_devices_vp_tuple(digital_twin_data: DeciceDigitalTwin) -> list[tuple[Device, str]]:
    """
    Retrieve all nodes from the provided digital twin data.

    Returns:
        list[tuple[Device,str]]: A list of deivices including the vertexpool ID.
    """
    devices = []
    if not digital_twin_data:
        return devices
    for vertexpool in digital_twin_data.vertexpools or []:
        for device in vertexpool.devices or []:
            devices.append((device, vertexpool.id))
    return devices


def get_all_devices(digital_twin_data: DeciceDigitalTwin | None, include_vertexpool_id: bool) -> list[Device]:
    """
    Retrieve all nodes from the provided digital twin data.

    Args:
        digital_twin_data (DeciceDigitalTwin | None): The digital twin data containing vertexpools and nodes.
        include_vertexpool_id (bool): Whether to include the vertexpool ID in the node_info dictionary.

    Returns:
        list[Node]: A list of nodes, potentially including the vertexpool ID.
    """
    devices = []
    if not digital_twin_data:
        return devices
    for vertexpool in digital_twin_data.vertexpools or []:
        for device in vertexpool.devices or []:
            # Create a copy of the node to avoid mutating the original
            device_copy = deepcopy(device)
            if include_vertexpool_id:
                device_copy.device_info = device_copy.device_info or {}
                device_copy.device_info["vertexpool_id"] = vertexpool.id
            devices.append(device_copy)
    return devices


def get_pods(digital_twin: DeciceDigitalTwin, scheduled_filter: bool | None = None) -> list[Pod] | None:
    """Returns all pods of digital_twin , if self.digital_twin not initialized return None.

    Args:
        pending_filter (bool | None, optional):Filter pods based on pending bool. Defaults to None.

    """
    if digital_twin:
        all_pods: list[Pod] = get_all_pods(digital_twin)
        # filter
        if scheduled_filter is not None:
            filtered_pods: list[Pod] = []
            if scheduled_filter:  # scheduled == True:
                for pod in all_pods:
                    if (pod.scheduled is None) or (pod.scheduled is True):
                        filtered_pods.append(pod)
            else:  # scheduled == False
                for pod in all_pods:
                    if (pod.scheduled is None) or (pod.scheduled is False):
                        filtered_pods.append(pod)
            return filtered_pods
        # non-filter
        return all_pods

    else:
        return None


def get_all_jobs(digital_twin: DeciceDigitalTwin | None) -> list[Job]:
    return [] if not digital_twin or not digital_twin.jobs else digital_twin.jobs


def get_all_links(digital_twin: DeciceDigitalTwin | None) -> list[Link]:
    return [] if not digital_twin or not digital_twin.links else digital_twin.links
