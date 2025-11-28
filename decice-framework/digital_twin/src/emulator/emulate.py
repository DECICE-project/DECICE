import yaml
import random
import requests
from pydantic import ValidationError
from datetime import datetime
from datetime import UTC
import argparse
import time

# Import the schema definitions
from digital_twin.emulator.schema import GraphSchema, VertexPoolEmu, LinkEmu
from digital_twin.core.data_model import Vertexpool, Node, Metrics, Device, Link, DeciceDigitalTwin


# Utility functions
def generate_util(mean: float, stdev: float) -> float:
    return max(0.0, min(100.0, random.gauss(mean, stdev)))


def calculate_power(util: float, cpu_cores: float, pf: float) -> float:
    base_power = 20.0
    return round(base_power + (util / 100.0) * cpu_cores * 15.0 * pf, 2)


def calculate_mem_util(util: float) -> float:
    jitter = random.uniform(-10, 10)
    mem_util = max(0.0, min(100.0, util * 0.7 + jitter))
    return round(mem_util, 2)


# Conversion function from VertexPoolEmu to Vertexpool
def convert_vertexpool(vp_emu: VertexPoolEmu) -> Vertexpool:
    new_nodes = []
    for node in vp_emu.nodes:
        util = generate_util(node.metrics.util.mean, node.metrics.util.stdev)
        power = calculate_power(util, node.metrics.cpu_cores, node.metrics.power_factor)
        mem_util = calculate_mem_util(
            util,
        )

        new_nodes.append(
            Node(
                name=node.name,
                id=node.name,
                node_info=node.node_info if node.node_info else None,
                metrics=Metrics(
                    util=round(util, 2),
                    power_watts=power,
                    cpu_cores=node.metrics.cpu_cores,
                    mem_total=node.metrics.mem_total,
                    network_bandwidth_mbps=node.metrics.network_bandwidth_mbps,
                    mem_util=mem_util,
                    total_disk_gb=node.metrics.total_disk_gb,
                    free_disk_gb=node.metrics.free_disk_gb,
                ),
            )
        )

    new_devices = [
        Device(
            id=device.id,
            name=device.name,
            labels=device.labels,
            device_info=device.device_info if device.device_info else None,
        )
        for device in vp_emu.devices
    ]

    return Vertexpool(
        id=vp_emu.id,
        vertexpool_labels=vp_emu.vertexpool_labels,
        nodes=new_nodes,
        devices=new_devices,
    )


def convert_link(link_emu: LinkEmu) -> Link:
    mean = link_emu.network_delay_ms.mean
    stdev = link_emu.network_delay_ms.stdev
    delay: float = max(0.5, random.gauss(mean, stdev))
    return Link(
        vertexpool_a_id=link_emu.vertexpool_a_id, vertexpool_b_id=link_emu.vertexpool_b_id, network_delay_ms=delay
    )


def emulate(path) -> DeciceDigitalTwin:
    graph = load_and_validate_yaml(path)
    lastUpdated = datetime.now(tz=UTC).timestamp()
    emulated_vertexpools = [convert_vertexpool(vp) for vp in graph.vertexpools]
    emulated_links = [convert_link(lnk) for lnk in graph.links]
    dt = DeciceDigitalTwin(lastUpdated=lastUpdated, vertexpools=emulated_vertexpools, links=emulated_links, jobs=[])
    return dt


def load_and_validate_yaml(yaml_path: str) -> GraphSchema:
    try:
        # Load YAML file
        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)

        # Validate against GraphSchema
        graph = GraphSchema(**data)
        print("✅ YAML file is valid.")
        return graph

    except FileNotFoundError:
        print(f"❌ File not found: {yaml_path}")
    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error:\n{e}")
    except ValidationError as ve:
        print(f"❌ Validation error:\n{ve}")
    return None


def update_dt(url: str, dt: DeciceDigitalTwin) -> bool:
    res = requests.post(url=url + "/api/model_core/", json=dt.model_dump())
    if res.status_code == 201:
        return True
    else:
        return False


def save_dt_as_json(url: str, path: str = "last_emulate_result.json"):
    res = requests.get(f"{url}/api/model_core")
    dt = DeciceDigitalTwin(**res.json())
    with open(path, "w") as f:
        f.write(dt.model_dump_json(indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Emulate and update digital twin from YAML.")
    # Required positional argument
    parser.add_argument("yaml_path", help="Path to the emulation YAML file")
    # Optional arguments
    parser.add_argument(
        "--dt_url", default="http://127.0.0.1:8010", help="Digital Twin URL (default: http://127.0.0.1:8010)"
    )
    parser.add_argument("--freq", type=int, default=30, help="Update interval frequency in seconds (default: 30)")

    args = parser.parse_args()
    digital_twin_url = args.dt_url
    update_interval = args.freq
    yaml_path = args.yaml_path

    try:
        while True:
            print("----------")
            digital_twin = emulate(yaml_path)
            print("----------")
            print(digital_twin)
            updated = update_dt(digital_twin_url, digital_twin)
            print("----------")
            if updated:
                print("Updated DT")
                save_dt_as_json(digital_twin_url)
            else:
                print("Couldnt update DT")
            time.sleep(update_interval)
            print("\n\n")
    except KeyboardInterrupt:
        print("\nExiting on user interrupt.")
