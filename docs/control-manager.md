# Control Manager

## Overview
The Control Manager is the central coordination and logic layer of the DECICE framework.

It is responsible for:
* Communication between microservices
* Orchestration of operational workflows
* Maintaining system consistency
* Providing API endpoints for:
* User authentication & authorization
* Job submission & monitoring
* Scheduling

## Prerequisites
* Kubernetes cluster (v1.29+)
* Helm (version ≥ 3.x)

Namespace created for DECICE components:
```
kubectl create namespace decice
```

Secret for your image registry (must already exist in the namespace):
```
kubectl create secret docker-registry <your-secret-name> --docker-server=<your-server-name> --docker-username=<your-docker-username> --docker-password=<your-password> --namespace=decice
```

## Recommended Installation Approach

We strongly advise exporting the default values.yaml and customizing your own copy before installation:

```
helm show values myrepo/decice-control-manager > values.control-manager.yaml
```

Edit values.control-manager.yaml to match your environment, then install with:

```
helm install control-manager myrepo/decice-control-manager \
  -n decice \
  -f values.control-manager.yaml
```

## Configuration Parameters
Below is a list of parameters available in the chart and their default values:

| Parameter                         | Type   | Default                                                             | Description                                                   |
|-----------------------------------|--------|---------------------------------------------------------------------|---------------------------------------------------------------|
| applicationName                   | string | control-manager                                                     | Logical name of the application                               |
| replicaCount                      | int    | 1                                                                   | Number of pods in the deployment                              |
| image.registry                    | string | http://your-image-registry                                         | Container image registry                                      |
| image.repository                  | string | decice-control-manager                                              | Image repository name                                         |
| image.tag                         | string | test                                                                | Image tag/version                                             |
| image.secret                      | string | decice-image-registry                                               | Kubernetes secret name for private registry                   |
| image.imagePullPolicy             | string | IfNotPresent                                                        | Pod image pull policy                                         |
| service.name                      | string | control-manager-service                                             | Name of the Kubernetes Service                                |
| service.type                      | string | ClusterIP                                                           | Service type (ClusterIP, LoadBalancer, NodePort)              |
| service.servicePort               | int    | 8000                                                                | Port exposed by the service                                   |
| service.nodePort                  | int    | 30080                                                               | NodePort (only used if type: NodePort)                        |
| configMap.name                    | string | control-manager-config                                              | Name of the ConfigMap storing environment vars                |
| existingSecret.name               | string | jwt-secret                                                          | Name of the existing secret containing JWT key                |
| env.controlManagerHost            | string | 0.0.0.0                                                             | Host address for Control Manager binding                      |
| env.controlManagerPort            | int    | 8000                                                                | Port for Control Manager API                                  |
| env.prometheusService             | string | http://prometheus-stack-kube-prom-prom-prometheus.monitoring       | Prometheus service URL                                        |
| env.prometheusPort                | int    | 9090                                                                | Prometheus service port                                       |
| env.digitalTwinService            | string | digital-twin-service                                                | Digital Twin microservice name                                |
| env.digitalTwinPort               | int    | 8010                                                                | Digital Twin service port                                     |
| env.promqlWrapperService          | string | promql-json-wrapper-service                                         | PromQL wrapper service name                                   |
| env.promqlWrapperPort             | int    | 8050                                                                | PromQL wrapper port                                           |
| env.psgcService                   | string | psgc-service                                                        | PSGC microservice name                                        |
| env.psgcPort                      | int    | 8040                                                                | PSGC service port                                             |
| env.schedulerService              | string | ai-scheduler-service                                                | Scheduler service name                                        |
| env.schedulerPort                 | int    | 8030                                                                | Scheduler service port                                        |
| env.schedulerControllerService    | string | scheduler-controller-service                                        | Scheduler controller service name                             |
| env.schedulerControllerPort       | int    | 8020                                                                | Scheduler controller service port                             |
| env.redisService                  | string | redis://redis-cm-master                                             | Redis connection string                                       |
| env.redisPort                     | int    | 6379                                                                | Redis port                                                    |
| env.environment                   | string | production                                                          | Deployment environment (prod/dev)                             |
| env.jwtAlgorithm                  | string | HS256                                                               | JWT signing algorithm                                         |
| env.tokenExpireMinutes            | int    | 60                                                                  | Expiration time for tokens                                    |
| env.sessionExpireSeconds          | int    | 6000                                                                | Expiration time for sessions                                  |
| env.corsAllowedOrigins            | string | *                                                                   | CORS allowed origins                                          |
| env.corsAllowedMethods            | string | *                                                                   | CORS allowed HTTP methods                                     |
| env.corsAllowedHeaders            | string | *                                                                   | CORS allowed headers                                          |
| env.corsAllowCredentials          | bool   | True                                                                | Allow CORS credentials                                        |
| env.postgresUser                  | string | testuser                                                            | PostgreSQL username                                            |
| env.postgresPassword              | string | testpassword                                                        | PostgreSQL password                                            |
| env.postgresDb                    | string | userdb                                                              | PostgreSQL database name                                      |
| env.internalAPIKey                | string | some-key...                                                         | Internal API key for secure inter-service communication       |


## Bundled Database Deployments
The Control Manager Helm chart also deploys basic Redis and PostgreSQL instances to satisfy its runtime dependencies:
* PostgreSQL: Stores user authentication data, session info, and other Control Manager metadata.
* Redis: Used for caching and fast data exchange between components.

These bundled database instances are:
* Ephemeral — there are no Persistent Volumes defined.
* Single-pod deployments — no clustering or HA.

### Production Recommendations
If you plan to use the bundled Redis/PostgreSQL:
* You should modify their Kubernetes manifests (or helm subcharts, if present) to include PVCs for data durability:
* PostgreSQL: persistence on /var/lib/postgresql/data
* Redis: persistence on /data

If you prefer external managed services:
* Provision your own Redis/PostgreSQL outside DECICE via:
* Managed cloud services (e.g. AWS RDS, Azure Cache for Redis, Google Cloud SQL)
* Self-deployment with persistence enabled


## Verification
After installation:

```
kubectl get pods -n decice
kubectl logs <control-manager-pod-name> -n decice
```
The Control Manager should start and listen on the configured service port (8000 by default).
