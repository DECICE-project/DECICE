# AI Scheduler

## Overview
The Integrated AI Scheduler is the intelligent decision-making core of DECICE.
It combines Deep Reinforcement Learning (DRL) with deterministic scheduling strategies to optimize workload placement across the device–edge–cloud continuum.

Core Functions:
* Receives enriched scheduling requests from the Scheduler Controller
* Processes real-time and predictive metrics from the Digital Twin
* Applies DRL-based and deterministic decision logic
* Produces optimal placement decisions for workloads
* Exposes high-performance APIs to upstream components for direct decision retrieval

## Prerequisites
* Kubernetes cluster (v1.29+)
* Helm ≥ 3.x
Namespace created for DECICE components:

```
kubectl create namespace decice
```

## Recommended Installation
Export the chart’s default values:

```
helm show values myrepo/ai-scheduler > values.ai-scheduler.yaml
```
Install:

```
helm install ai-scheduler myrepo/ai-scheduler \
  -n decice \
  -f values.ai-scheduler.yaml
```

## Configuration Parameters

| Parameter                         | Type   | Default                     | Description                               |
|-----------------------------------|--------|-----------------------------|-------------------------------------------|
| applicationName                   | string | ai-scheduler                | App name                                  |
| replicaCount                      | int    | 1                           | Number of AI scheduler pod replicas       |
| image.registry                    | string | http://your-image-registry | Container image registry                  |
| image.repository                  | string | decice-ai-scheduler        | Repository name                           |
| image.tag                         | string | test                        | Image tag                                 |
| image.secret                      | string | decice-image-registry       | Secret for private registry pulls         |
| image.imagePullPolicy             | string | IfNotPresent                | Pull policy                               |
| service.name                      | string | ai-scheduler-service        | Service name                              |
| service.type                      | string | ClusterIP                    | Service type                              |
| service.servicePort               | int    | 8030                        | Port exposed                              |
| configMap.name                    | string | ai-scheduler-config         | ConfigMap name                            |
| env.environment                   | string | production                  | Environment name for the deployment       |
| env.aiSchedulerHost               | string | 0.0.0.0                     | Binding host                              |
| env.aiSchedulerPort               | int    | 8030                        | Binding port                              |
| env.schedulerControllerService    | string | scheduler-controller-service| Downstream Scheduler Controller            |
| env.schedulerControllerPort       | int    | 8020                        | Port for Scheduler Controller             |
| env.internalAPIKey                | string | your-api-key                | API key for communication between components   |


## Verification
After installation:

```
kubectl get pods -n decice
kubectl logs <ai-scheduler-pod> -n decice
```
You should see logs confirming the application startup

## Notes

In large deployments, it’s recommended to run AI Scheduler in multiple replicas for resilience — controlled via replicaCount.
