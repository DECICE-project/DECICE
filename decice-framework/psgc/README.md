# Platform Specific Glue Code (PSGC)

[![CI Pipeline](https://img.shields.io/badge/CI-Pending-yellow)](<!-- URL to your CI pipeline -->)
[![Test Coverage](https://img.shields.io/badge/Coverage-Pending-yellow)](<!-- URL to your coverage report -->)

The Platform Specific Glue Code (PSGC) is a stateful, event-driven microservice that acts as the orchestration engine and platform adapter for the DECICE framework. It is the crucial "last mile" component that translates abstract workflow definitions from the Control Manager into concrete actions on a target platform (e.g., Kubernetes).

## Core Responsibilities

The PSGC is built around a proactive **Engine** that manages the entire lifecycle of a workflow on the target platform. Its primary responsibilities are:

1.  **Workflow Delegation:** Receives workflow definitions from the Control Manager, saves their state to a Redis repository, and prepares for execution.
2.  **Data Management:** Manages data ingress by providing pre-signed URLs for object storage (MinIO) and reacting to file upload events via webhooks.
3.  **Job Orchestration:**
    *   Requests scheduling decisions from the Control Manager for `READY` jobs.
    *   Creates platform-specific resources (e.g., Kubernetes PersistentVolumeClaims and Jobs) based on the scheduling decision.
    *   Manages the full lifecycle of a job, including data staging (via init containers) and execution.
4.  **State Reconciliation:** Continuously monitors the state of platform resources (e.g., Kubernetes Jobs) and its internal state repository (Redis) to ensure consistency and handle missed events.
5.  **Status Reporting:** Reports the real-time status of individual jobs and the final completion status of entire workflows back to the Control Manager.

## 🚀 Getting Started

This service is designed to be run as part of a unified, multi-service environment. Please see the main `README.md` in the project root for instructions on how to run the entire system.

### Local Development (Standalone)

For focused development, the PSGC can be run with a local `docker-compose` setup that includes its direct dependencies (Redis and MinIO).

**1. Install Dependencies**
```bash
poetry install
```

**2. Configure Environment**
Copy the environment template. The defaults are pre-configured for this Compose environment.
```bash
cp .env.example .env
```

**3. Launch the Local Stack**
This command will build the PSGC image and start the PSGC, Redis, and MinIO containers.
```bash
docker-compose up --build
```
The services will be available at:
-   **PSGC API:** [http://localhost:8040/docs](http://localhost:8040/docs)
-   **MinIO Console:** [http://localhost:9001](http://localhost:9001) (Log in with credentials from `.env`)

## 🧪 Running Tests

The service includes a comprehensive suite of unit and integration tests.

```bash
# Run all tests
poetry run pytest

# Run with a detailed coverage report
poetry run coverage run -m pytest
poetry run coverage report -m
```

## 📄 API Contract

The PSGC exposes a minimal API for receiving commands and events. The full OpenAPI specification is available at the `/docs` route.

-   **`POST /workflows`**: The primary endpoint for the Control Manager to delegate a new workflow.
-   **`POST /webhooks/minio`**: The internal endpoint for receiving file upload notifications from MinIO.
-   **`GET /health`**: A simple health check endpoint.

## ⚙️ Configuration

The service is configured via environment variables, documented in `.env.example`.

| Variable | Description | Example (in `.env.example`) |
| :--- | :--- | :--- |
| **PSGC Service** | | |
| `HOST` | The host on which this service will run. | `0.0.0.0` |
| `PORT` | The port on which this service will listen. | `8040` |
| **Redis** | | |
| `REDIS_HOST` | The hostname of the Redis service. | `redis` |
| `REDIS_PORT` | The port of the Redis service. | `6379` |
| **MinIO** | | |
| `MINIO_ENDPOINT` | The endpoint of the MinIO service. | `minio:9000` |
| `MINIO_ACCESS_KEY` | The root user for MinIO. | `minioadmin` |
| `MINIO_SECRET_KEY` | The root password for MinIO. | `minioadmin` |
| `MINIO_SECURE` | Set to `true` to use TLS with MinIO. | `false` |
| **Control Manager** | | |
| `CM_SERVICE_HOST` | The hostname of the Control Manager. | `host.docker.internal` |
| `CM_SERVICE_PORT` | The port of the Control Manager. | `8000` |


-----

## MinIO

### MinIO Docker
```
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
```

```
docker run -d \
--name minio \
--network="host" \
-e MINIO_ROOT_USER=minioadmin \
-e MINIO_ROOT_PASSWORD=minioadmin \
-e MINIO_NOTIFY_WEBHOOK_ENABLE_1=on \
-e MINIO_NOTIFY_WEBHOOK_ENDPOINT_1=http://localhost:8040/webhooks/minio \
minio/minio server /data
```

* When using: `docker run -d --name minio --network="host" minio/minio server /data`
```
# docker command to open a interactive terminal directly in the running minio bucket
docker exec -it minio /bin/sh

# minio mc commands to setup and test the event notification webhook
mc alias set myminio http://localhost:9000 minioadmin minioadmin
mc mb myminio/workflows
mc admin config set myminio notify_webhook:1 endpoint="http://localhost:8040/webhooks/minio"
mc admin service restart myminio
mc event add myminio/workflows arn:minio:sqs::1:webhook --event put




mc event add myminio/mybucket arn:minio:sqs::1:webhook --event put
```

* When using environment variables run: `setup.sh`

**The Service on `http://localhost:8040/webhooks/minio` has to run first before executing the webhook command, otherwise MinIO won't continue!**
