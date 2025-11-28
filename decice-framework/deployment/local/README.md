# DECICE Framework - Local Development Environment

This directory contains the unified Docker Compose setup for running the entire DECICE microservices ecosystem on a local machine for development and testing.

This setup uses `network_mode: host`, which allows all containerized services to share the host machine's network. This simplifies connecting to a local Kubernetes cluster (like Minikube or Kind) but requires that all inter-service communication uses `localhost`.

## Table of Contents

1.  [Architecture Overview](#1-architecture-overview)
2.  [Prerequisites](#2-prerequisites)
3.  [First-Time Setup](#3-first-time-setup)
4.  [Daily Workflow](#4-daily-workflow)
5.  [Service Endpoints](#5-service-endpoints)
6.  [Kubernetes (Kind vs. Minikube)](#6-kubernetes-kind-vs-minikube)
7.  [Minikube](#7-minikube)

---

### 1. Architecture Overview

This Docker Compose stack orchestrates the following services:

#### Application Microservices:
-   **`control-manager`**: The central orchestration and API gateway.
-   **`psgc`**: Platform Specific Glue Code for Kubernetes interactions.
-   **`scheduler`**: The AI-based scheduling service.
-   **`scheduler-controller`**: Manages and directs scheduling requests.
-   **`prom-json-wrapper`**: Gathers and formats metrics from Prometheus.
-   **`digital-twin`**: Maintains a real-time model of the cluster state.

#### Backing Services:
-   **`postgres`**: Relational database for the Control Manager.
-   **`redis`**: In-memory cache and message broker.
-   **`minio`**: S3-compatible object storage for workflows.
-   **`prometheus`**: Metrics collection and time-series database.
-   **`influxdb`**: Time-series database for the Digital Twin.

All services are configured to run on the host's network, meaning they communicate with each other and with backing services via `localhost` and their respective ports.

---

### 2. Prerequisites

Before you begin, ensure you have the following installed:

-   **Docker & Docker Compose:** To run the containerized services.
-   **A local Kubernetes Cluster:** This setup has been tested and is confirmed to work with **Minikube**. See the section on [Kubernetes](#6-kubernetes-kind-vs-minikube) for more details.
-   **`kubectl`:** Correctly configured to point to your local cluster (`current-context` should be set to `minikube`).
-   **(Optional but Recommended) `make`:** For using the simplified commands in the root `Makefile`.

---

### 3. First-Time Setup

1.  **Copy the Environment File:**
    Navigate to this directory (`/deployment/local`) and copy the example environment file. This file is ignored by Git and will store your local configuration.
    ```bash
    cp .env.example .env
    ```

2.  **Configure `.env`:**
    Open the newly created `.env` file. While most defaults are fine, you may want to review and customize credentials like `POSTGRES_USER` and `POSTGRES_PASSWORD`. **Do not change any of the `localhost` hostnames.**

3.  **Build the Docker Images:**
    From this directory, run the build command. This will build the Docker images for all the application microservices.
    ```bash
    docker-compose build
    ```
    *(This may take several minutes on the first run.)*

---

### 4. Daily Workflow

-   **Start All Services:**
    To launch the entire stack, run the following command from this directory:
    ```bash
    docker-compose up
    ```
    *(You can add the `-d` flag to run in detached mode.)*

-   **Stop All Services:**
    Press `Ctrl+C` in the terminal where the services are running. Then, to ensure containers are fully stopped and removed, run:
    ```bash
    docker-compose down
    ```

-   **View Logs:**
    To view the combined logs of all running services:
    ```bash
    docker-compose logs -f
    ```
    To view the logs of a specific service (e.g., `psgc`):
    ```bash
    docker-compose logs -f psgc
    ```

---

### 5. Service Endpoints

Once the stack is running, services are available on `localhost` at the following ports:

-   **Control Manager:** `http://localhost:8000`
-   **Digital Twin:** `http://localhost:8010`
-   **Scheduler Controller:** `http://localhost:8020`
-   **Scheduler:** `http://localhost:8030`
-   **PSGC:** `http://localhost:8040`
-   **Prometheus Wrapper:** `http://localhost:8050`

-   ---
-   **PostgreSQL:** `localhost:5432`
-   **Redis:** `localhost:6379`
-   **Prometheus UI:** `http://localhost:9090`
-   **MinIO API:** `http://localhost:9000`
-   **MinIO Console:** `http://localhost:9001`
-   **InfluxDB API:** `http://localhost:8086`

---

### 6. Kubernetes (Kind vs. Minikube)

This setup relies on `network_mode: host` to allow the `psgc` container to connect to the Kubernetes API server running on the host machine at `127.0.0.1`.

-   **Minikube (Recommended & Tested):** This setup works out-of-the-box with Minikube. Minikube correctly configures its API server to be accessible from `127.0.0.1`. Your `~/.kube/config` and `~/.minikube` directories are mounted into the `psgc` container to provide the necessary connection details and certificates.

-   **Kind (Experimental):** This setup **may not work with Kind without changes**. Kind runs its control plane inside a Docker container. Depending on your OS and Docker version, the Kind API server may not be accessible from `127.0.0.1` in a way that another container on the host network can reach. If you need to use Kind, you will likely need to revert to the bridge network architecture and use the `kubectl proxy` method described in this repository's history.

**For a simple and reliable local development experience, Minikube is the recommended choice for this configuration.**

### 7. Minikube
* Setup a cluster for PSGC
```
minikube start \
  --nodes=3 \
  --driver=docker \
  --kubernetes-version=v1.34.0 \
  --cpus=2 \
  --memory=2g
```
