# DECICE Scheduler Controller

[![CI Pipeline](https://img.shields.io/badge/CI-Pending-yellow)](<!-- URL to CI pipeline -->)
[![Test Coverage](https://img.shields.io/badge/Coverage-Pending-yellow)](<!-- URL to coverage report -->)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/license/apache-1-1)


The Scheduler Controller is a lightweight microservice that acts as an orchestration layer between the `control_manager` and the scheduling components of the DECICE framework.

## Core Responsibility

This service has one primary function:

1.  It receives a workload scheduling request from the `control_manager`.
2.  It enriches this request by fetching real-time node data from the **Digital Twin** service.
3.  It forwards the enriched payload to the **Scheduler** service to get a final placement decision.

## 🚀 Getting Started

This service is designed to be run as part of the unified, multi-service environment. Please see the main `README.md` in the project root for instructions on how to run the entire system with `docker-compose`.

### Local Development (Standalone)

For focused development on this service, you can run it locally, provided its downstream dependencies (Digital Twin, Scheduler) are accessible over the network.

**1. Install Dependencies**
```bash
poetry install
```

**2. Configure Environment**
Copy the environment template and edit the URLs to point to your running downstream services.
```bash
cp .env.example .env
# Edit .env to set DT_BASE_URL and SCHEDULER_BASE_URL
```

**3. Run the Service**
```bash
poetry run python src/main.py
```
The API will be available at [http://localhost:8020](http://localhost:8020).

## 🧪 Running Tests

The service includes a full suite of unit and integration tests.

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run coverage run -m pytest
poetry run coverage report
```

## 📄 API Contract

The service provides a single primary endpoint. The full OpenAPI specification is available at the `/` route when the service is running.

-   **`POST /scheduler-controller`**: The main orchestration endpoint.

## ⚙️ Configuration

The service is configured via environment variables defined in a `.env` file. See `.env.example` for a complete template.

| Variable | Description | Example |
| :--- | :--- | :--- |
| `SC_HOST` | The host on which this service will run. | `0.0.0.0` |
| `SC_PORT` | The port on which this service will listen. | `8020` |
| `DT_SERVICE_HOST` | The hostname of the downstream Digital Twin service. | `digital-twin` |
| `DT_SERVICE_PORT` | The port of the downstream Digital Twin service. | `8010` |
| `SCHEDULER_HOST` | The hostname of the downstream Scheduler service. | `scheduler` |
| `SCHEDULER_PORT` | The port of the downstream Scheduler service. | `8030` |
