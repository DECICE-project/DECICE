# PromQL-to-JSON Wrapper

## Overview
The PromQL-to-JSON Wrapper functions as the telemetry synchronization layer in the DECICE framework. It bridges the gap between:
* Prometheus — the persistent time-series database containing raw metrics
* Digital Twin and AI Scheduler — which require normalized JSON data

Responsibilities:
* Executes targeted PromQL queries against Prometheus
* Transforms raw metric responses into JSON schema
* Provides instantaneous state representation of the compute continuum

## Prerequisites
* Kubernetes cluster (v1.29+)
* Helm (≥ 3.x)
Namespace created for DECICE components (if you haven't done already):

```
kubectl create namespace decice
```


## Recommended Installation
Export the chart’s default values file and edit your own copy:

```
helm show values myrepo/promql-json-wrapper > values.promql-json-wrapper.yaml
```

Then install:

```
helm install promql-json-wrapper myrepo/promql-json-wrapper \
  -n decice \
  -f values.promql-json-wrapper.yaml
```

## Configuration Parameters
| Parameter                           | Type   | Default                                                   | Description                                           |
|-------------------------------------|--------|-----------------------------------------------------------|-------------------------------------------------------|
| applicationName                     | string | promql-json-wrapper                                       | Logical name of the app                               |
| replicaCount                        | int    | 1                                                         | Number of pods                                        |
| image.registry                      | string | http://your-image-registry                               | Container image registry                              |
| image.repository                    | string | promql-json-wrapper                                       | Image repository name                                 |
| image.tag                           | string | test                                                      | Image version/tag                                     |
| image.secret                        | string | decice-image-registry                                     | Secret for private registry pull                      |
| image.imagePullPolicy               | string | IfNotPresent                                              | Image pull policy                                     |
| service.name                        | string | promql-json-wrapper-service                               | Kubernetes Service name                               |
| service.type                        | string | NodePort                                                  | Service type (NodePort / ClusterIP)                   |
| service.servicePort                 | int    | 8050                                                      | Port exposed by service                               |
| service.nodePort                    | int    | 30050                                                     | NodePort value (only used if type: NodePort)          |
| configMap.name                      | string | promql-json-wrapper-config                                | ConfigMap name for env vars                           |
| env.promqlWrapperHost               | string | 0.0.0.0                                                   | Wrapper binding host                                  |
| env.promqlWrapperPort               | int    | 8050                                                      | Wrapper binding port                                  |
| env.prometheusService               | string | prometheus-stack-kube-prom-prometheus.monitoring          | Prometheus service                                    |
| env.prometheusPort                  | int    | 9090                                                      | Prometheus port                                       |
| env.digitalTwinService              | string | digital-twin-service                                      | Digital Twin service name                             |
| env.digitalTwinURL                  | string | http://digital-twin-service                               | Digital Twin URL                                      |
| env.digitalTwinPort                 | int    | 8010                                                      | Digital Twin port                                     |
| env.environment                     | string | production                                                | Environment name                                      |
| env.logLevel                        | string | info                                                      | Log verbosity level                                   |
| env.autoUpdateDTEnabled             | bool   | true                                                      | Enable automatic Digital Twin updates                 |
| env.autoUpdateDTFrequencySeconds    | float  | 30.0                                                      | Interval for Digital Twin updates                     |
| env.internalAPIKey                  | string | some api key                                              | Key for secure inter-service communication            |
| env.powerConsumptionPromqlQueries   | list   | (see default)                                             | List of PromQL queries for power consumption          |



## Verification
After installation:

```
kubectl get pods -n decice
kubectl logs <promql-json-wrapper-pod> -n decice
```

You should see startup logs indicating that the app started succesfully.
