# Scheduler Controller

## Overview
The Scheduler Controller is responsible for managing and coordinating workload scheduling requests between the Digital Twin and the AI Scheduler in the DECICE architecture.

Core Functions:
* Accepts workload scheduling requests containing resource requirements (CPU, memory, storage, GPU).
* Validates incoming requests.
* Queries Digital Twin for latest node-level metrics — resource utilization, energy consumption, network performance.
* Enriches requests with infrastructure capabilities to provide a complete scheduling context.
* Applies optional filtering rules:
    * Node hardware capabilities
    * Energy usage limits
    * Geographic constraints
* Transmits enriched requests to the AI Scheduler.
* Receives placement decisions and exposes them through APIs for upstream services to consume, deploy workloads, and optionally audit.

## Prerequisites
* Kubernetes cluster (v1.29+)
* Helm (≥ 3.x)


DECICE namespace:

```
kubectl create namespace decice
```


## Recommended Installation
Export and customize the default values file:

```
helm show values myrepo/scheduler-controller > values.scheduler-controller.yaml
```

Install using:

```
helm install scheduler-controller myrepo/scheduler-controller \
  -n decice \
  -f values.scheduler-controller.yaml
```

## Configuration Parameters

| Parameter                        | Type   | Default                         | Description                                      |
|----------------------------------|--------|---------------------------------|--------------------------------------------------|
| applicationName                  | string | scheduler-controller            | Application name                                 |
| replicaCount                     | int    | 1                               | Number of pod replicas                           |
| image.registry                   | string | http://your-image-registry      | Container image registry URL                     |
| image.repository                 | string | decice-scheduler-controller     | Image repository name                            |
| image.tag                        | string | test                            | Image tag/version                                |
| image.secret                     | string | decice-image-registry           | Secret for pulling from private image registry   |
| image.imagePullPolicy            | string | IfNotPresent                    | Pull policy                                      |
| service.name                     | string | scheduler-controller-service    | Kubernetes Service name                          |
| service.type                     | string | ClusterIP                       | Service type                                     |
| service.servicePort              | int    | 8020                            | Port exposed by the service                      |
| configMap.name                   | string | scheduler-controller-config     | ConfigMap name                                   |
| env.schedulerControllerHost      | string | 0.0.0.0                         | Binding host for Scheduler Controller            |
| env.schedulerControllerPort      | int    | 8020                            | Binding port for Scheduler Controller            |
| env.digitalTwinService           | string | digital-twin-service            | Digital Twin service name                        |
| env.digitalTwinPort              | int    | 8010                            | Digital Twin port                                |
| env.controlManagerService        | string | control-manager-service         | Control Manager service name                     |
| env.controlManagerPort           | int    | 8000                            | Control Manager port                             |
| env.schedulerService             | string | ai-scheduler-service            | AI Scheduler service name                        |
| env.schedulerPort                | int    | 8030                            | AI Scheduler port                                |
| env.environment                  | string | production                      | Deployment environment                           |
| env.internalAPIKey               | string | some API key                    | Inter-service authentication key                 |



## Verification
Check after installation:

```
kubectl get pods -n decice
kubectl logs <scheduler-controller-pod> -n decice
```

Logs should confirm the successful startup.

## Additional Notes

Filtering rules for scheduling requests are not hardcoded; they can be implemented by modifying upstream request formats or extending the controller logic.

Placement decisions may include resource reservations; store these for audit or analysis if persistence is enabled.
