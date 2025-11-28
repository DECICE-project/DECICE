# 🌱 Carbon Prediction API - E4

This project provides a **carbon intensity forecasting API** powered by Facebook Prophet and deployed on **Kubernetes** with **Prometheus monitoring**.

It predicts future carbon intensity (gCO₂/kWh) using historical hourly datasets and exposes REST endpoints and Prometheus metrics.

📂 Project Structure

```jsx
CarbonPrediction/
├── app/                     # Application code
│   ├── main.py              # FastAPI app with prediction endpoints
│   ├── model.py             # Model loading & forecasting utilities
│   └── prophet_model.pkl    # Trained Prophet model
├── dataset/                 # Carbon intensity datasets
│   ├── IT-NO_2021_hourly.csv
│   ├── IT-NO_2022_hourly.csv
│   ├── IT-NO_2023_hourly.csv
│   └── IT-NO_2024_hourly.csv
├── Dockerfile
├── requirements.txt
├── CarbonPredictionDaemonSet.yaml
├── CarbonPredictionService.yaml
└── CarbonPredictionServiceMonitor.yaml

```

## 🚀 Features

- ✅ Train and save a **Prophet time-series model**
- ✅ REST API using **FastAPI** with endpoints for daily, weekly, monthly, and custom range forecasts
- ✅ Exposes **Prometheus metrics** for carbon intensity predictions
- ✅ Deployable as a **Kubernetes DaemonSet**
- ✅ **ServiceMonitor** for automatic scraping by Prometheus (via kube-prometheus-stack)

## ☸️ Kubernetes Deployment

### 1. DaemonSet

```jsx
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: carbon-prediction
  namespace: mlops
spec:
  selector:
    matchLabels:
      app: carbon-prediction
  template:
    metadata:
      labels:
        app: carbon-prediction
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      tolerations:
      - key: "node.kubernetes.io/not-ready"
        operator: "Exists"
        effect: "NoSchedule"
      containers:
      - name: carbon-prediction
        image: fatemehbozorgi/carbon-prediction:v1
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: dataset
          mountPath: /app/dataset
      volumes:
      - name: dataset
        hostPath:
          path: /mnt/data/carbon-dataset
          type: DirectoryOrCreate

```

### 2. Service

```jsx
apiVersion: v1
kind: Service
metadata:
  name: carbon-prediction
  namespace: mlops
  labels:
    app: carbon-prediction
spec:
  selector:
    app: carbon-prediction
  ports:
    - name: http
      port: 8000
      targetPort: 8000
  type: ClusterIP
```

### 3. ServiceMonitor

```jsx
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: carbon-prediction-monitor
  namespace: monitoring
  labels:
    release: monitoring  # must match Prometheus serviceMonitorSelector
spec:
  selector:
    matchLabels:
      app: carbon-prediction
  namespaceSelector:
    matchNames:
      - mlops
  endpoints:
  - port: http
    path: /metrics
    interval: 15s

```

### 1. Apply DaemonSet & Service

```
kubectl apply -f CarbonPredictionDaemonSet.yaml
kubectl apply -f CarbonPredictionService.yaml
```

2. Apply ServiceMonitor (requires Prometheus Operator)

```jsx
kubectl apply -f CarbonPredictionServiceMonitor.yaml
```

DaemonSet ensures one pod per node, with dataset mounted at /mnt/data/carbon-dataset.

Service (ClusterIP) exposes port 8000.

ServiceMonitor configures Prometheus to scrape metrics from the service.

## 🔌 API Endpoints

| Endpoint | Description |
| --- | --- |
| `/` | Health check |
| `/predictday` | 24-hour forecast from now |
| `/predictweek` | 7-day forecast from now |
| `/predictmonth` | 30-day forecast from now |
| `/predictrange` | Forecast for custom time range (start, end in ISO8601) |
| `/metrics` | Prometheus metrics for next 24h predictions |

## Prometheus Metric for CI

```yaml
carbon_intensity
```