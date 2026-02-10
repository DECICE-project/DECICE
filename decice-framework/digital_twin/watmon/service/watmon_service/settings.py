from pydantic import BaseModel
import yaml

SETTINGS_PATH = "settings.yaml"
SETTING_PROMETHEUS_URL = "prometheus_url"
SETTING_NETWORK_EXPORTER_LABEL = "network_exporter_label"
SETTINGS_API_PORT = "api_port"
SETTINGS_EXPORTER_PORT = "exporter_port"
SETTINGS_EXPORTER_VERTEXPOOLS_ENDPOINT = "exporter_vertexpools_endpoint"


class PromQLSettings(BaseModel):
    network_delay_range_selector: str = "5m"  # default value, optional


class Settings(BaseModel):
    prometheus_url: str
    network_exporter_label_key: str
    network_exporter_label_value: str
    api_port: int
    exporter_port: int
    exporter_vertexpools_endpoint: str
    namespace: str = "monitoring"
    promql: PromQLSettings = PromQLSettings()


def read_settings(settings_path=SETTINGS_PATH) -> Settings:
    with open(settings_path, "r") as file:
        yaml_data: dict = yaml.safe_load(file)
        prometheus = yaml_data.get(SETTING_PROMETHEUS_URL)
        key, value = yaml_data.get(SETTING_NETWORK_EXPORTER_LABEL).split("=")
        api_port = int(yaml_data.get(SETTINGS_API_PORT))
        exporter_port = int(yaml_data.get(SETTINGS_EXPORTER_PORT))
        exporter_vertexpools_endpoint = yaml_data.get(SETTINGS_EXPORTER_VERTEXPOOLS_ENDPOINT)

        promql_data: dict | None = yaml_data.get("promql")
        promql_settings = PromQLSettings(**(promql_data or {}))
        return Settings(
            prometheus_url=prometheus,
            network_exporter_label_key=key,
            network_exporter_label_value=value,
            api_port=api_port,
            exporter_port=exporter_port,
            exporter_vertexpools_endpoint=exporter_vertexpools_endpoint,
            promql=promql_settings,
        )
