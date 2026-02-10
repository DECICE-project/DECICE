import kfp

from kfp import dsl

from kfp.components import load_component_from_text
from kfp.compiler import Compiler


def anomaly_detection():

    import os

    os.system("docker run fatemehbozorgi/test-repo:latest")


anomaly_detection_op = load_component_from_text("""
name: Anomaly Detection Component
description: A component to run anomaly detection.
inputs:
  - {name: prometheus_url, type: String}
  - {name: polling_interval, type: Integer}
  - {name: name, type: String}
  - {name: type, type: String}  
outputs: []
implementation:
  container:
    image: fatemehbozorgi/test-repo:latest
    command: ["python", "main.py"]
    args: [
  "--prometheus-url", {inputValue: prometheus_url},
  "--polling-interval", {inputValue: polling_interval},
  "--type", {inputValue: type},
  "--name", {inputValue: name}
]
""")


@dsl.pipeline(name="Anomaly Detection Pipeline", description="A pipeline to detect anomalies in data.")
def anomaly_detection_pipeline(prometheus_url: str, polling_interval: int, name: str, type_: str):
    anomaly_detection_task = anomaly_detection_op(
        prometheus_url=prometheus_url, polling_interval=polling_interval, name=name, type=type_
    )


if __name__ == "__main__":
    # client = kfp.Client()
    Compiler().compile(anomaly_detection_pipeline, "anomaly_detection_pipeline.yaml")
    print("Pipeline compiled to anomaly_detection_pipeline.yaml")
