# Installing Kepler for Power Monitoring

This guide shows how to install the [Kepler](https://kepler.sh/) power monitoring tool using its Helm chart. These instructions assume you have Helm installed and configured for your Kubernetes cluster.

Kepler is used to collect power consumption metrics, which are then scraped by Prometheus to build the training labels for the power prediction model.

## Installation Steps

1.  **Add the Kepler Helm repository:**

    ```bash
    helm repo add kepler https://sustainable-computing-io.github.io/kepler-helm-chart
    helm repo update
    ```

2.  **Create the namespace and install Kepler:**

    The following command creates the `kepler` namespace (if it doesn't exist) and installs Kepler into it.

    We enable the `ServiceMonitor` so that Prometheus can automatically discover and scrape Kepler's metrics. The `release=prometheus` label is added to the `ServiceMonitor` to match the selector used by the Prometheus Operator in this project.

check
```bash
# Look at the Prometheus CR to see the selector it uses
kubectl -n monitoring get prometheus -o jsonpath='{range .items[*]}{.metadata.name}{" => "}{.spec.serviceMonitorSelector.matchLabels}{"\n"}{end}'

# Also check the Helm release label on the Prometheus object
kubectl -n monitoring get prometheus -o jsonpath='{range .items[*]}{.metadata.labels.helm\.sh/release}{"\n"}{end}'
```
if `release: prometheus` then use the following command

    ```bash
    kubectl create ns kepler || true

    helm upgrade --install kepler kepler/kepler \
      --namespace kepler \
      --set serviceMonitor.enabled=true \
      --set serviceMonitor.labels.release=prometheus
    ```

if `release: prometheus-stack` then use the following command
    ```bash
    kubectl create ns kepler || true

    helm upgrade --install kepler kepler/kepler \
      --namespace kepler \
      --set serviceMonitor.enabled=true \
      --set serviceMonitor.labels.release=prometheus
    ```


## Verification

After installation, you can check that the Kepler pods are running:

```bash
kubectl get pods -n kepler
```

You should also be able to see Kepler's metrics in your Prometheus dashboard.
