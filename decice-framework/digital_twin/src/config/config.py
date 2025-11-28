import os

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class ServiceConfig(BaseModel):
    port: int
    service: str


class InfluxDBConfig(BaseModel):
    url: str
    token: str
    bucket: str
    org: str


class ServiceSettings(BaseSettings):
    host: str = Field(..., default_factory=lambda: os.getenv("DT_HOST", "0.0.0.0"))
    port: int = Field(..., default_factory=lambda: os.getenv("DT_PORT", 8010))

    scheduler_controller: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(
            port=os.getenv("SC_PORT", 8020),
            service=os.getenv("SC_SERVICE", "127.0.0.1"),
        )
    )

    promql_wrapper: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(
            port=os.getenv("PROMQL_WRAPPER_PORT", 8050),
            service=os.getenv("PROMQL_WRAPPER_SERVICE", "127.0.0.1"),
        )
    )

    influxdb: InfluxDBConfig | None = Field(
        default_factory=lambda: InfluxDBConfig(
            url=os.getenv("INFLUXDB_URL", ""),
            token=os.getenv("INFLUXDB_TOKEN", ""),
            bucket=os.getenv("INFLUXDB_BUCKET", ""),
            org=os.getenv("INFLUXDB_ORG", ""),
        )
        if all(os.getenv(env_var) for env_var in ["INFLUXDB_TOKEN", "INFLUXDB_BUCKET", "INFLUXDB_ORG", "INFLUXDB_URL"])
        else print("Could not read INFLUXDB vars from .env")
    )


load_dotenv()
service_settings = ServiceSettings()
