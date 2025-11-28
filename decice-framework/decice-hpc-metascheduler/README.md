# DECICE HPC Meta-Scheduler

[![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=flat&logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Volcano](https://img.shields.io/badge/Volcano-FF6B6B?style=flat&logo=apache&logoColor=white)](https://volcano.sh/)
[![SLURM](https://img.shields.io/badge/SLURM-4CAF50?style=flat&logo=linux&logoColor=white)](https://slurm.schedmd.com/)

A microservice for intelligent HPC job scheduling across heterogeneous computing environments. The meta-scheduler automatically routes computational workloads to the most appropriate scheduler (Volcano, SLURM InterLink, or Kubernetes default) based on job requirements and resource characteristics.

## 🌟 Key Features

### 🚀 **Intelligent Scheduling**
- **Multi-Scheduler Support**: Seamlessly integrates Volcano, SLURM InterLink, and Kubernetes schedulers
- **Load-Aware Routing**: Real-time load comparison using unified CPU/Memory/Queue metrics (AUTO mode)
- **Automatic Routing**: Smart job distribution based on scheduler capabilities and workload requirements
- **Image Format Handling**: Automatic conversion for SLURM Singularity compatibility (`docker://` prefix)

### 🏗️ **Production Architecture**
- **Microservice Design**: Cloud-native, containerized architecture
- **High Availability**: 3-replica deployment with pod anti-affinity
- **Auto-Scaling**: HPA configuration with CPU/memory metrics
- **Health Monitoring**: Comprehensive probes and health checks

### 🔧 **Advanced Features**
- **RESTful API**: Complete job lifecycle management with new metrics endpoints
- **Real-time Status**: Live pod status tracking and monitoring
- **Load-Aware Monitoring**: Unified Prometheus-based metrics collection from all schedulers
- **RBAC Integration**: Kubernetes role-based access control
- **Resource Management**: Configurable CPU/memory limits and requests
- **Decision Transparency**: Detailed load comparison and scheduling recommendation APIs

## 📋 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    DECICE Meta-Scheduler                        │
│                   (FastAPI Microservice)                       │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
    ┌─────▼─────┐           ┌─────▼─────┐
    │  Volcano  │           │   SLURM   │
    │ Scheduler │           │InterLink  │
    │           │           │           │
    │ • Batch   │           │• Remote   │
    │ • HPC     │           │• HPC      │
    │ • GPU     │           │• Legacy   │
    └───────────┘           └───────────┘
```

### Scheduler Routing Logic

| Target Scheduler | Use Case | Node Selection | Container Runtime | Load Awareness |
|-----------------|----------|----------------|-------------------|----------------|
| **VOLCANO** | Batch processing, GPU workloads | Standard workers | containerd | ✅ Monitored |
| **INTERLINK_SLURM** | Remote HPC, Legacy systems | Virtual nodes (`cn04`) | Singularity | ✅ Monitored |
| **AUTO** | Intelligent routing based on load | Best available | Auto-selected | ✅ Load-based |
| **DEFAULT** | Standard Kubernetes workloads | Any available | containerd | ❌ Not monitored |

## 🚀 Quick Start

### Prerequisites

- **Kubernetes Cluster**: v1.24+ with RBAC enabled
- **Volcano Scheduler**: Installed in `volcano-system` namespace
- **SLURM InterLink**: Virtual kubelet configured on designated nodes
- **Prometheus**: kube-prometheus-stack installed in `monitoring` namespace
- **kubectl**: Configured with cluster admin access

### Step-by-Step Deployment

#### 1. Deploy HPC Metrics Exporter

```bash
# Upload exporter to management node (e.g., guoehi-dev)
scp simple-hpc-exporter.py guoehi-dev:~/

# Start the exporter
ssh guoehi-dev
pkill -9 -f simple-hpc-exporter.py  # Stop existing instance
nohup python3 ~/simple-hpc-exporter.py > ~/hpc-exporter.log 2>&1 &

# Verify
curl http://localhost:8092/health
# Expected: {"status": "healthy", "host": "192.168.23.14"}

exit

# Troubleshooting: If you see "Address already in use" error
# ssh guoehi-dev "lsof -i :8092 -t | xargs kill -9"  # Force kill process using port 8092
# See DEPLOYMENT_FIX.md for detailed troubleshooting steps

# Deploy Kubernetes Service and ServiceMonitor
kubectl apply -f remote-hpc-k8s.yaml
kubectl get endpoints remote-hpc-metrics -n decice
# Should show: 192.168.23.3:8092
```

#### 2. Configure Volcano Metrics

```bash
kubectl apply -f volcano-metrics-config.yaml
kubectl get servicemonitor -n volcano-system
```

#### 3. Verify Prometheus Data Collection

Wait 1-2 minutes, then verify metrics are being collected:

```bash
# From a K8s node (e.g., cn01)
ssh cn01

# Test HPC metrics
curl -s "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090/api/v1/query?query=remote_hpc_nodes_total" | python3 -m json.tool

# Test Volcano metrics  
curl -s "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090/api/v1/query?query=volcano_e2e_job_scheduling_last_time" | python3 -m json.tool
```

Expected: HPC should show ~20 nodes, Volcano should show scheduling metrics.

#### 4. Deploy Meta-Scheduler

```bash
kubectl apply -f k8s-metascheduler-full.yaml
kubectl wait --for=condition=ready pod -l app=metascheduler-full -n decice --timeout=120s

# Verify deployment
kubectl get pods -n decice -l app=metascheduler-full
kubectl get svc -n decice metascheduler-full-service

# Check logs
kubectl logs -l app=metascheduler-full -n decice --tail=50
```

#### 5. Test the Deployment

```bash
# Test health endpoint
curl http://192.168.23.11:30081/health

# Test load comparison (requires authentication)
curl -H "Authorization: Bearer test-token" \
  http://192.168.23.11:30081/metrics/load-comparison

# Expected: JSON with volcano_load_score, hpc_load_score, and recommendation
```

### Quick Validation Tests

**Submit a Volcano job:**
```bash
curl -X POST http://192.168.23.11:30081/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "name": "volcano-test",
    "image": "alpine:latest",
    "schedulerTarget": "VOLCANO",
    "command": ["echo", "Hello Volcano"],
    "resources": {"cpu": "100m", "memory": "128Mi"}
  }'

# Verify placement
kubectl get pods -n decice -l scheduler=volcano -o wide
```

**Submit an auto-scheduled job:**
```bash
curl -X POST http://192.168.23.11:30081/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "name": "auto-test",
    "image": "alpine:latest",
    "schedulerTarget": "AUTO",
    "command": ["echo", "Auto-scheduled"],
    "resources": {"cpu": "200m", "memory": "128Mi"}
  }'

# Check which scheduler was selected
curl -H "Authorization: Bearer test-token" \
  http://192.168.23.11:30081/metrics/load-comparison
```

## 📖 API Reference

### Authentication

All API endpoints require a Bearer token:
```bash
Authorization: Bearer test-token
```

### Core Endpoints

#### Submit Job
```http
POST /jobs
Content-Type: application/json

{
  "name": "my-hpc-job",
  "image": "alpine:latest",
  "schedulerTarget": "VOLCANO|INTERLINK_SLURM",
  "command": ["sh", "-c", "echo Hello HPC World && sleep 30"],
  "resources": {
    "cpu": "100m",
    "memory": "128Mi"
  }
}
```

#### List Jobs
```http
GET /jobs
Authorization: Bearer test-token
```

#### Get Job Details
```http
GET /jobs/{job_id}
Authorization: Bearer test-token
```

#### Get Pod Status
```http
GET /jobs/{job_id}/pod-details
Authorization: Bearer test-token
```

#### Health Check
```http
GET /health
```

#### Load Comparison (New)
```http
GET /metrics/load-comparison
Authorization: Bearer test-token
```

#### Scheduling Recommendation (New)
```http
GET /metrics/recommendation?scheduler_target=AUTO
Authorization: Bearer test-token
```

#### All Scheduler Metrics (New)
```http
GET /metrics/schedulers
Authorization: Bearer test-token
```

### Example Usage

#### Submit Volcano Job
```bash
curl -X POST http://192.168.23.11:30081/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "name": "volcano-gpu-job",
    "image": "nvidia/cuda:11.8-runtime-ubuntu20.04",
    "schedulerTarget": "VOLCANO",
    "command": ["nvidia-smi"],
    "resources": {
      "cpu": "1000m",
      "memory": "2Gi"
    }
  }'
```

#### Submit SLURM Job
```bash
curl -X POST http://192.168.23.11:30081/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "name": "slurm-hpc-job",
    "image": "alpine:latest",
    "schedulerTarget": "INTERLINK_SLURM",
    "command": ["sh", "-c", "echo Running on SLURM && hostname"],
    "resources": {
      "cpu": "100m",
      "memory": "64Mi"
    }
  }'
```

#### Submit Auto-Scheduled Job (New)
```bash
curl -X POST http://192.168.23.11:30081/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "name": "auto-scheduled-job",
    "image": "alpine:latest",
    "schedulerTarget": "AUTO",
    "command": ["sh", "-c", "echo Auto-scheduled job && hostname"],
    "resources": {
      "cpu": "500m",
      "memory": "256Mi"
    }
  }'
```

#### Check Load Comparison
```bash
curl http://192.168.23.11:30081/metrics/load-comparison \
  -H "Authorization: Bearer test-token"
```

## 🔧 Configuration

### High Availability Settings

- **Replicas**: 3 (minimum 2, maximum 10)
- **Anti-Affinity**: Pods distributed across different nodes
- **Rolling Updates**: Max surge 1, max unavailable 1
- **Auto-Scaling**: CPU 70%, Memory 80% thresholds

### Resource Limits

- **Per Pod**: 250m CPU, 512Mi Memory (requests)
- **Limits**: 500m CPU, 1Gi Memory
- **Probes**: Startup, Liveness, Readiness checks

### RBAC Permissions

The meta-scheduler has the following Kubernetes permissions:
- Create, read, update, delete Pods
- Read Pod status and logs
- Access to namespace: `decice`

## 🧪 Performance Testing

### Auto-Scaling Behavior

```bash
# Generate sustained load to trigger HPA
for i in {1..20}; do
  curl -X POST http://192.168.23.11:30081/jobs \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer test-token" \
    -d "{\"name\":\"hpa-test-$i\",\"image\":\"alpine:latest\",\"schedulerTarget\":\"VOLCANO\",\"command\":[\"sleep\",\"60\"]}"
  sleep 1
done

# Watch HPA scaling
kubectl get hpa metascheduler-full-hpa -n decice -w

# Monitor pod count
kubectl get pods -n decice -l app=metascheduler-full -w
```

## 📊 Monitoring & Observability

### Unified Load Calculation

The meta-scheduler uses a **unified load calculation formula** for both Volcano and HPC clusters:

```
Load Score = CPU_Usage×40% + Memory_Usage×40% + Queue_Jobs×20%
```

**Volcano Metrics**:
- CPU Usage: Cluster-wide CPU utilization (from `node_cpu_seconds_total`)
- Memory Usage: Cluster-wide memory utilization (from `node_memory_MemAvailable_bytes`)  
- Queue Jobs: Number of jobs in Volcano queues (from `volcano_queue_request_*`)

**HPC Metrics**:
- CPU Usage: SLURM cluster CPU allocation percentage (from `sinfo`)
- Memory Usage: SLURM cluster memory allocation percentage (from `sinfo`)
- Queue Jobs: Number of pending jobs in SLURM queue (from `squeue`)

**Decision Logic**:
- If load difference < 15 points: Prefer Volcano (local preference)
- Otherwise: Route to scheduler with lower load score

### Health Checks

- **Startup Probe**: 10s initial delay, 5s interval
- **Liveness Probe**: 60s initial delay, 30s interval
- **Readiness Probe**: 30s initial delay, 10s interval

### Service Status

```bash
# Check service health
curl http://192.168.23.11:30081/health

# Monitor pods
kubectl get pods -n decice -w

# Check HPA status
kubectl describe hpa metascheduler-full-hpa -n decice
```

### Logging

```bash
# View meta-scheduler logs
kubectl logs -l app=metascheduler-full -n decice -f

# Check specific pod logs
kubectl logs <pod-name> -n decice
```

## 🔍 Troubleshooting

> **📖 For detailed troubleshooting steps, see [DEPLOYMENT_FIX.md](DEPLOYMENT_FIX.md)**

### Common Issues

#### Port Already in Use (Address already in use)

```bash
# Problem: HPC exporter fails with "OSError: [Errno 98] Address already in use"
# Solution: Kill existing process and restart

ssh guoehi-dev "pkill -9 -f simple-hpc-exporter.py"
sleep 3
ssh guoehi-dev "nohup python3 ~/simple-hpc-exporter.py > ~/hpc-exporter.log 2>&1 &"

# Or use lsof to find and kill the specific process
ssh guoehi-dev "lsof -i :8092 -t | xargs kill -9"
```

#### API Endpoint Returns 404 Not Found

```bash
# Problem: curl http://192.168.23.11:30081/metrics/load-comparison returns {"detail":"Not Found"}
# Solution: Redeploy with updated ConfigMap

kubectl delete -f k8s-metascheduler-full.yaml
kubectl wait --for=delete pod -l app=metascheduler-full -n decice --timeout=60s
kubectl apply -f k8s-metascheduler-full.yaml
kubectl wait --for=condition=ready pod -l app=metascheduler-full -n decice --timeout=180s

# Verify endpoints are available
curl http://192.168.23.11:30081/health
curl -H "Authorization: Bearer test-token" http://192.168.23.11:30081/metrics/load-comparison
```

#### HPC Metrics Not Available

```bash
# Check exporter running
ssh guoehi-dev "ps aux | grep simple-hpc-exporter"

# Test endpoint
ssh guoehi-dev "curl http://localhost:8092/metrics"

# Verify Kubernetes service
kubectl get endpoints remote-hpc-metrics -n decice
```

#### Volcano Metrics Not Available

```bash
# Check Volcano pods
kubectl get pods -n volcano-system

# Verify ServiceMonitor
kubectl get servicemonitor -n volcano-system

# Test metrics endpoint
kubectl port-forward -n volcano-system svc/volcano-scheduler-metrics 8080:8080
curl http://localhost:8080/metrics
```

#### Auto-Scheduling Not Working

```bash
# Check load comparison
curl -H "Authorization: Bearer test-token" \
  http://192.168.23.11:30081/metrics/load-comparison

# Check logs
kubectl logs -l app=metascheduler-full -n decice | grep -i error

# Verify Prometheus connectivity
kubectl exec -it <pod-name> -n decice -- \
  curl http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090/api/v1/query?query=up
```

#### Pod Scheduling Failures

```bash
# Check node labels
kubectl get nodes --show-labels | grep node-type

# Verify SLURM node label
kubectl label node <virtual-node> node-type=slurm-interlink

# Check RBAC permissions
kubectl get sa metascheduler-sa -n decice
kubectl describe rolebinding metascheduler-rolebinding -n decice
```

## 🧪 Advanced Testing

### Load-Based Auto-Scheduling Test

Generate load to test intelligent routing:

```bash
# Submit 10 jobs to Volcano to increase load
for i in {1..10}; do
  curl -X POST http://192.168.23.11:30081/jobs \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer test-token" \
    -d "{
      \"name\": \"volcano-load-$i\",
      \"image\": \"alpine:latest\",
      \"schedulerTarget\": \"VOLCANO\",
      \"command\": [\"sleep\", \"120\"],
      \"resources\": {\"cpu\": \"500m\", \"memory\": \"256Mi\"}
    }"
  sleep 2
done

# Wait for metrics to update
sleep 30

# Check load scores
curl -H "Authorization: Bearer test-token" \
  http://192.168.23.11:30081/metrics/load-comparison

# Submit AUTO job - should route to less loaded scheduler
curl -X POST http://192.168.23.11:30081/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "name": "auto-after-load",
    "image": "alpine:latest",
    "schedulerTarget": "AUTO",
    "command": ["echo", "Auto-routed based on load"],
    "resources": {"cpu": "200m", "memory": "128Mi"}
  }'
```

### SLURM Job Verification

```bash
# Submit SLURM job
curl -X POST http://192.168.23.11:30081/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "name": "slurm-test",
    "image": "alpine:latest",
    "schedulerTarget": "INTERLINK_SLURM",
    "command": ["sh", "-c", "echo Running on SLURM && hostname"],
    "resources": {"cpu": "100m", "memory": "64Mi"}
  }'

# Verify on SLURM cluster
kubectl get pods -n decice -l scheduler=interlink-slurm -o wide
ssh guoehi-dev "ssh 192.168.23.14 'squeue | grep alpine'"
```

## 📊 Monitoring & Debugging

### View Jobs and Logs

```bash
# List all jobs
curl -H "Authorization: Bearer test-token" \
  http://192.168.23.11:30081/jobs

# Get job details
curl -H "Authorization: Bearer test-token" \
  http://192.168.23.11:30081/jobs/<job_id>

# View meta-scheduler logs
kubectl logs -l app=metascheduler-full -n decice --tail=100 -f
```

### Monitor HPC Exporter

```bash
# Check exporter status
ssh guoehi-dev "curl http://localhost:8092/health"

# View exporter logs
ssh guoehi-dev "tail -f ~/hpc-exporter.log"

# Check raw metrics
ssh guoehi-dev "curl http://localhost:8092/metrics | head -30"
```

### Query Prometheus Metrics

```bash
# From K8s node
ssh cn01

# HPC metrics
curl -s "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090/api/v1/query?query=remote_hpc_cpu_utilization_percent" | python3 -m json.tool

# Historical data (last 1 hour)
END=$(date +%s)
START=$((END - 3600))
curl -s "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090/api/v1/query_range?query=remote_hpc_nodes_total&start=${START}&end=${END}&step=300" | python3 -m json.tool
```

## 🏗️ Project Structure

```
decice-metascheduler/
├── app.py                          # Main FastAPI application (FULL VERSION)
├── k8s-metascheduler-full.yaml    # Complete Kubernetes deployment
│   └── ConfigMap (embedded)        # Simplified app.py for PoC deployment
├── pyproject.toml                  # Python project configuration
├── uv.lock                        # Dependency lock file
├── openapi.yaml                   # API specification
├── schemas.py                     # Pydantic models and enums
├── clients/                       # External service clients
│   ├── kubernetes_client.py       # Kubernetes API client
│   ├── slurm_client.py            # SLURM InterLink client
│   └── prometheus_metrics_client.py # Unified metrics client
├── services/                      # Business logic layer
│   └── scheduler_service.py       # Core scheduling logic
├── repository/                    # Data access layer
│   └── job_repository.py          # Job data operations
├── volcano-metrics-config.yaml   # Volcano Prometheus configuration
├── simple-hpc-exporter.py        # HPC metrics collector
├── remote-hpc-k8s.yaml           # HPC monitoring K8s integration
└── DEPLOYMENT_FIX.md             # Troubleshooting guide
```

### 📦 Two Deployment Versions

| Feature | ConfigMap Version | Full Version (app.py) |
|---------|-------------------|----------------------|
| **Location** | Embedded in k8s-metascheduler-full.yaml | Project root directory |
| **Purpose** | Quick PoC deployment | Full development/production |
| **Dependencies** | requirements.txt (6 packages) | pyproject.toml (full stack) |
| **Data Storage** | In-memory dictionary | SQLite + Alembic migrations |
| **Architecture** | Single file (~440 lines) | Layered architecture |
| **Endpoints** | ✅ All core + metrics endpoints | ✅ All core + metrics endpoints |
| **When to Use** | Fast K8s deployment, testing | Local dev, production builds |

**Note**: Both versions now include all necessary endpoints (`/health`, `/metrics/*`)!

## ⚙️ Configuration

### Auto-Scaling

- **Min Replicas**: 2, **Max Replicas**: 10
- **CPU Threshold**: 70%, **Memory Threshold**: 80%

```bash
kubectl get hpa metascheduler-full-hpa -n decice -w
```

### Security

- **Authentication**: Bearer token (`test-token` for dev)
- **RBAC**: Namespace `decice` only
- **Resources**: CPU 500m, Memory 1Gi per pod

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review Kubernetes logs for debugging
