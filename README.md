![DECICE](/images/DECICE.png)

# DECICE: Device-Edge-Cloud Intelligent Collaboration Framework

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-green)](https://www.docker.com/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-orange)](https://www.tensorflow.org/)

**DECICE** is an open-source framework designed to orchestrate workloads across the **Compute Continuum**—seamlessly bridging the gap between IoT devices, Edge nodes, Cloud clusters, and High-Performance Computing (HPC) infrastructure.

At its core, DECICE utilizes an **Integrated AI Scheduler (IAIS)** powered by Deep Reinforcement Learning (PPO) to optimize workload placement based on real-time metrics like energy consumption, latency, and resource availability.

---

## 🚀 Key Features

* **🧠 AI-Driven Orchestration:** A Proximal Policy Optimization (PPO) agent that dynamically selects scheduling strategies (e.g., Round Robin, Min-Max, Energy-Aware) based on live cluster states.
* **🧪 Virtual Training Environment (VTE):** A robust MLOps pipeline to generate synthetic data, train models offline, and evaluate them against heuristics without impacting production.
* **🌐 Heterogeneous Support:** Unified API for managing Kubernetes Jobs, Deployments, and Slurm (HPC) batch jobs.
* **🔮 Digital Twin:** Real-time system modeling and predictive analytics using Prometheus and InfluxDB.
* **📊 Observability:** Built-in integration with **TensorBoard** for training metrics and a unified **Dashboard** for cluster topology visualization.
* **🔌 Workflow Integration:** Native support for **Argo Workflows** and **Snakemake** pipelines.

---

## 🏗️ Architecture

DECICE operates as a set of loosely coupled microservices:

1.  **Control Manager:** The central brain handling user authentication, workflow parsing, and state management.
2.  **Integrated AI Scheduler:** The decision engine containing the RL agent and Feature Engineering pipeline.
3.  **Scheduler Controller:** Intermediary that enriches job requests with real-time data from the Digital Twin.
4.  **PSGC (Platform Specific Glue Code):** The execution engine that translates abstract decisions into platform-specific actions (K8s manifests or Slurm scripts).
5.  **PromQL Wrapper & Digital Twin:** The telemetry layer providing a unified view of the infrastructure.

![Architecture Diagram](/images/architecture.png)
*(See `/docs` for detailed admin documentation and setup guide)*

---

## 🛠️ Getting Started - Local Setup

### Prerequisites
* **Docker Engine** & **Docker Compose** (v2.0+)
* **NVIDIA Drivers / CUDA** (Optional, recommended for training the AI Scheduler)
* **Python 3.10+** (For local script execution)
* **Minikube**

### 1. Clone the Repository
```bash
git clone https://github.com/DECICE-project/decice-framework.git
cd decice-framework
```

### 2. Configure Environment (Crucial!)
```bash
cp .env.example .env
```
Open .env and configure:
* `INTERNAL_API_KEY`: Generate a strong random string (e.g., `openssl rand -hex 32`).
* `DATA_BASE_DIR`: Default is `./data`. Ensure this path exists or let Docker create it.

## 3. Launch the Stack
```
docker compose up -d --build
```

## 4. Access the Interfaces
Once the containers are healthy:
* Dashboard (UI): http://localhost:3000
* OpenAPI (Swagger)
    * Control Manager: http://127.0.0.1:8000/
    * Digital Twin: http://127.0.0.1:8010/
    * Scheduler Controller: http://127.0.0.1:8020/
    * AI Scheduler: http://127.0.0.1:8030/
    * PSGC: http://127.0.0.1:8040/
    * PromQL-Wrapper: http://127.0.0.1:8050/
    * Slurm-Client: http://127.0.0.1:8060/
    * TensorBoard: http://localhost:6006
    * Grafana: http://localhost:3001 (Default creds: admin/admin)

# 🧠 Training the AI Scheduler
DECICE includes a fully API-driven training ground. You do not need to run manual scripts.

## 1. Generate Training Data Create a synthetic dataset representing your cluster topology
Use the OpenAPI specification or `POST`
```
curl -X POST "http://localhost:8030/data/generate/dataset_v1" \
     -H "X-Internal-Api-Key: <YOUR_KEY>" \
     -H "Content-Type: application/json" \
     -d '{"num_files": 100, "jobs_min": 5, "jobs_max": 20}'
```

## 2. Define a Model Architecture Register a new scheduler configuration (Hyperparameters)
Use the OpenAPI specification or `POST`
```
curl -X POST "http://localhost:8030/models/" \
     -H "X-Internal-Api-Key: <YOUR_KEY>" \
     -H "Content-Type: application/json" \
     -d '{"name": "ppo_v1_aggressive", "actor_lr": 0.0005}'
```

## 3. Start Training Launch a background worker process
Use the OpenAPI specification or `POST`
```
curl -X POST "http://localhost:8030/training/start" \
     -H "X-Internal-Api-Key: <YOUR_KEY>" \
     -H "Content-Type: application/json" \
     -d '{"scheduler_name": "ppo_v1_aggressive", "dataset_name": "dataset_v1", "cycles": 50}'
```
Monitor Progress Open TensorBoard at `http://localhost:6006` to watch the Actor/Critic loss convergence in real-time.

# 📂Repository Structure
...

# 🤝 Contributing
We welcome contributions!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

# Acknowledgment
This project has received funding from the European Union's Horizon Europe research and innovation programme under Grant Agreement No **101092582**.

# 📄 License
Distributed under the **Apache License, Version 2.0**. See `LICENSE` for more information.
