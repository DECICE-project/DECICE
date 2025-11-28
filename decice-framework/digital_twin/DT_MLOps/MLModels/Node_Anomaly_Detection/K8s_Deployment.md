# 📊 Node Anomaly Detection - Kubernetes Deployment

This setup deploys an **anomaly detection service** as a DaemonSet on every Kubernetes node, exposes its Prometheus metrics, and enables monitoring through a ServiceMonitor.

## 🚀 Components

### 1. **DaemonSet (`DaemonSet.yaml`)**

- Runs one `anomaly-detector` pod on **every node**.
- Mounts local data from `/mnt/data/offline-data`.
- Each pod exposes metrics at `:8002/metrics`.
- Uses tolerations to ensure it can run on nodes with custom taints.
- Includes:
    - Resource requests & limits (CPU/memory)
    - Liveness & readiness probes
    - Environment variable for the host node’s IP (`NODE_IP`)

```jsx
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: anomaly-detector
  namespace: mlops
spec:
  selector:
    matchLabels:
      app: anomaly-detector
  template:
    metadata:
      labels:
        app: anomaly-detector
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8002"
        prometheus.io/path: "/metrics"
    spec:
      tolerations:
      - key: "special"
        operator: "Exists"
        effect: "NoSchedule"
      - key: "node.kubernetes.io/network-unavailable"
        operator: "Exists"
        effect: "NoSchedule"
      containers:
      - name: detector
        image: fatemehbozorgi/e4anomalydetection:v2
        command: ["python", "onlinemain.py"]
        args: ["--node", "$(NODE_IP):9100"]
        env:
        - name: NODE_IP
          valueFrom:
            fieldRef:
              fieldPath: status.hostIP
        volumeMounts:
        - name: offline-data
          mountPath: /mnt/data
      volumes:
      - name: offline-data
        hostPath:
          path: /mnt/data/offline-data
          type: DirectoryOrCreate

```

---

### 2. **Service (`Service.yaml`)**

- Headless service (`clusterIP: None`) that selects all `anomaly-detector` pods.
- Provides a consistent discovery endpoint for Prometheus scraping.
- Exposes `http-metrics` on port **8002**.

```jsx
apiVersion: v1
kind: Service
metadata:
  name: anomaly-detector
  namespace: MLOps
  labels:
    app: anomaly-detector
spec:
  selector:
    app: anomaly-detector
  ports:
    - name: metrics
      port: 8002
      targetPort: 8002
  type: ClusterIP

```

---

### 3. **ServiceMonitor (`ServiceMonitor.yaml`)**

- Custom resource for **Prometheus Operator**.
- Selects the `anomaly-detector` service by label.
- Scrapes metrics from `/metrics` every **15s** with a **10s timeout**.
- Namespace-scoped (`mlops`).

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: anomaly-detector-monitor
  namespace: mlops   # or monitoring if you prefer
  labels:
    release: prometheus-stack  # must match Prometheus `serviceMonitorSelector`
spec:
  selector:
    matchLabels:
      app: anomaly-detector
  endpoints:
  - port: metrics
    path: /metrics
    interval: 15s

```

## 📈 Metrics

Each `anomaly-detector` pod publishes Prometheus metrics such as:

```
anomaly_<model_name>_<node_ip>_<port>
```

Example:

```
anomaly_arima_172_18_16_135_9100
```

These metrics allow you to track anomalies **per node** and **per model**.

## 🛠️ Deployment

1. Apply the DaemonSet:
    
    ```bash
    kubectl apply -f DaemonSet.yaml
    ```
    
2. Apply the Service:
    
    ```bash
    kubectl apply -f Service.yaml
    ```
    
3. Apply the ServiceMonitor (requires Prometheus Operator):
    
    ```bash
    kubectl apply -f ServiceMonitor.yaml
    ```
    

---

## 🔍 Verification

- Check pods:
    
    ```bash
    kubectl get pods -n mlops -l app=anomaly-detector -o wide
    ```
    
- Check service:
    
    ```bash
    kubectl get svc anomaly-detector -n mlops
    
    ```