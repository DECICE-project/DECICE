# Anomaly Detection on Kubernetes Ecosystem

This repository contains various models for detecting anomalies within the Kubernetes ecosystem.

[Deployment in E4 Cluster](./K8s_Deployment.md)
---

## Description

This project leverages a range of anomaly detection techniques to monitor and maintain the health of systems within a Kubernetes environment. The repository includes models based on statistical, machine learning, and deep learning methods, each evaluating system status (normal or anomalous). Results are saved in a structured JSON file for easy tracking and analysis.

### Models Included

- **Statistical Methods**: Z-score, ARIMA (AutoRegressive Integrated Moving Average)
- **Machine Learning Methods**: Isolation Forest, One-Class SVM
- **Deep Learning Methods**: Temporal Convolutional Network (TCN), Convolutional Neural Network (CNN), Long Short-Term Memory (LSTM), and Autoencoder

The deep learning models, such as TCN, CNN, LSTM, and Autoencoder, first load pretrained parameters from the training phase and use them during inference to assess system health. This setup ensures efficient and accurate anomaly detection at runtime.

Each model provides its assessment of system status, allowing for a robust, multi-perspective approach to anomaly detection in Kubernetes environments.


## Installation

### Prerequisites
1. **Kubernetes** (required for Kubeflow)
2. **Kubeflow**: Kubeflow is an open-source ML toolkit for Kubernetes. 
3. **Docker** (required for building Docker images)


## Usage

To start anomaly detection, run the main script `main.py` with the following arguments:

```bash
python main.py --prometheus-url <PROMETHEUS_URL> --polling-interval <INTERVAL> --pod-name <POD_NAME>

```
--prometheus-url (required): URL for the Prometheus server (e.g., http://141.5.107.135:30090/)


--polling-interval: Polling interval in minutes (default is 10)


--pod-name (required): Name of the pod to monitor (e.g., envoy-0)

## Example

```bash
python main.py --prometheus-url http://141.5.107.135:30090/ --polling-interval 10 --pod-name envoy-0
```


## Kubeflow

Kubeflow is an open-source ML toolkit for Kubernetes. Once Kubernetes is set up, you can use MicroK8s for a lightweight Kubernetes deployment and follow the tutorial to set up Kubeflow locally. Kubeflow allows the development and deployment of scalable machine learning models within the Kubernetes ecosystem.

## Monitoring System

This project uses Grafana and Prometheus for monitoring system metrics. Prometheus captures metrics, which are then visualized in Grafana. Anomaly detection models pull specific metrics from Prometheus as needed.

## Python Scripts

The main Python script, main.py, performs the following tasks:

1. Extracts data from the Prometheus metrics endpoint.
2. Runs anomaly detection models.
3. Saves results to a JSON file.

Required Arguments for main.py:

1. --prometheus-url: URL of the Prometheus server (required).
2. --polling-interval: Polling interval in minutes (default is 10).
3. --pod-name: Pod name for monitoring (required).

## Dockerfile

The Dockerfile in this repository allows you to build a Docker image of the project. Docker images help maintain consistency across environments, ensuring that the code runs as expected across different setups.

## GitHub Actions

This project uses GitHub Actions to automate Docker image builds and push them to Docker Hub. The configuration for GitHub Actions is in the .github/workflows/main.yml file.
To Set Up GitHub Actions for Docker:

1. Go to Settings → Secrets and variables → Actions in your GitHub repository.
2. Create two secrets: DOCKER_USERNAME and DOCKER_PASSWORD.
3. Copy and paste the contents of .github/workflows/main.yml into a new GitHub Actions workflow.
4. Commit to trigger the workflow.

Refer to the GitHub Actions documentation for more details.

## Kubeflow Pipeline

The pipeline for this project is defined in pipeline.py. This script:
1. Creates a pipeline component using the Docker image (docker.io/fatemehbozorgi/test-repo).
2. Defines the arguments required for the main script (main.py).
3. Specifies a Kubeflow Pipeline using the @dsl.pipeline decorator.

### Example Pipeline Definition:
```python

@dsl.pipeline(
    name="Anomaly Detection Pipeline",
    description="A pipeline to detect anomalies in data."
)
def anomaly_detection_pipeline(prometheus_url: str, polling_interval: int, pod_name: str):
    anomaly_detection_task = anomaly_detection_op(
        prometheus_url=prometheus_url,
        polling_interval=polling_interval,
        pod_name=pod_name
    )

```
### To Create and Run the Pipeline:
```python
if __name__ == "__main__":
    client = kfp.Client()
    client.create_run_from_pipeline_func(
        anomaly_detection_pipeline,
        arguments={
            "prometheus_url": "http://141.5.107.135:30090/",
            "polling_interval": 10,
            "pod_name": "envoy-0"
        }
    )

```


