# Installing Prometheus for Metrics Collection

This guide explains how to install the `kube-prometheus-stack` Helm chart, which provides a full Prometheus and Grafana monitoring stack.

This stack is used to scrape metrics from Kepler and other sources, which are essential for building the power prediction model's training data.

## Installation Steps

1.  **Add the Prometheus community Helm repository:**

    ```bash
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    ```

2.  **Install the `kube-prometheus-stack`:**

    The following command installs the stack into the `monitoring` namespace. Key configurations include:
    - Disabling Alertmanager and Pushgateway, which are not needed for this project.
    - Configuring persistent storage for Prometheus.
    - Exposing Prometheus and Grafana via Ingress.

    **Note:** You may need to adjust the `grafana.ingress.hosts` and `prometheus.ingress.hosts` values to match your environment.

    ```bash
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
      --create-namespace --namespace monitoring \
      --set kube-state-metrics.enabled=true \
      --set alertmanager.enabled=false \
      --set prometheus-pushgateway.enabled=false \
      --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.accessModes[0]=ReadWriteOnce \
      --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=8Gi \
      --set prometheus.service.type=ClusterIP \
      --set prometheus.service.port=9090 \
      --set grafana.service.type=ClusterIP \
      --set grafana.ingress.enabled=true \
      --set grafana.ingress.ingressClassName=nginx \
      --set grafana.ingress.hosts[0]=grafana.lpt.local \
      --set prometheus.ingress.enabled=true \
      --set prometheus.ingress.ingressClassName=nginx \
      --set prometheus.ingress.hosts[0]=prometheus.lpt.local \
      --atomic --timeout 15m
    ```

## Verification

After installation, you can check that the Prometheus and Grafana pods are running:

```bash
kubectl get pods -n monitoring
```

You can then access the Prometheus and Grafana UIs at the hostnames you configured.
