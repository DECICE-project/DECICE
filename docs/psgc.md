# Platform Specific Glue Code (PSGC)

## Overview

The Platform Specific Glue Code (PSGC) microservice is the execution bridge between the Control Manager and the target compute platforms (HPC, Cloud, Edge).

It operates as an event-driven orchestration engine, keeping abstract workflow states synchronized with actual infrastructure states via asynchronous watchers.

Key Functions:
* Executes deployment logic onto heterogeneous compute targets
* Watches and reconciles resource states across device–edge–cloud continuum
* Manages secure data upload operations via MinIO Object Storage:
* Generates time-limited pre-signed URLs for large datasets
* Avoids routing data through Control Manager, reducing bottlenecks
* Uses Redis for session and state information (lightweight caching)

Important Architectural Notes:
* This chart deploys basic MinIO and Redis instances for convenience
* These are not managed for HA or production hardening — customers may
    * Use their own managed MinIO/Redis
    * Update values.yaml to connect PSGC to external endpoints

## Prerequisites
* Kubernetes cluster (v1.29+)
* Helm ≥ 3.x

Namespace created for DECICE components:

```
kubectl create namespace decice
```

If using external MinIO/Redis:
* Ensure connectivity from PSGC pods to service endpoints
* Update env.minioService / env.redisService accordingly
* Ensure credentials are correct in env.minioAccessKey / env.minioSecretKey

## Recommended Installation
Export and customize:

```
helm show values myrepo/psgc > values.psgc.yaml
```

Install:

```
helm install psgc myrepo/psgc \
  -n decice \
  -f values.psgc.yaml
```

## Configuration Parameters

| Parameter                          | Type   | Default                       | Description                                             |
|------------------------------------|--------|---------------------------------|---------------------------------------------------------|
| applicationName                    | string | psgc                            | App name                                                |
| replicaCount                       | int    | 1                               | Number of pods                                          |
| image.registry                     | string | http://your-image-registry      | Image registry URL                                      |
| image.repository                   | string | decice-image registry           | Image repository                                        |
| image.tag                          | string | test                            | Image tag                                               |
| image.secret                       | string | decice-harbor                   | Secret for private registry                             |
| image.imagePullPolicy              | string | IfNotPresent                    | Image pull policy                                       |
| service.name                       | string | psgc-service                    | Service name                                            |
| service.type                       | string | NodePort                        | Service type                                            |
| service.servicePort                | int    | 8040                            | Service port                                            |
| configMap.name                     | string | psgc-config                     | ConfigMap name                                          |
| serviceAccount.name                | string | psgc-sa                         | Service account for PSGC                               |
| roles.roleName                     | string | psgc-role                       | Role for PSGC                                           |
| roles.clusterRoleName              | string | psgc-clusterrole                | ClusterRole for PSGC                                    |
| roleBindings.bindingName           | string | psgc-rolebinding                | RoleBinding name                                        |
| roleBindings.clusterBindingName    | string | psgc-clusterrolebinding         | ClusterRoleBinding name                                 |
| env.environment                    | string | production                      | Environment name                                        |
| env.psgcHost                       | string | 0.0.0.0                         | PSGC binding host                                       |
| env.psgcPort                       | int    | 8040                            | PSGC binding port                                       |
| env.controlManagerService          | string | control-manager-service         | Control Manager service name                            |
| env.controlManagerPort             | int    | 8000                            | Control Manager service port                            |
| env.redisService                   | string | redis://redis-psgc-master       | Redis connection string (used for PSGC sessions)        |
| env.redisPort                      | int    | 6379                            | Redis port                                              |
| env.redisDB                        | int    | 0                               | Redis DB index                                          |
| env.sessionExpireSeconds           | int    | 6000                            | Redis session expiration time                           |
| env.minioService                   | string | minio-service                   | MinIO service endpoint                                  |
| env.minioPort                      | int    | 9000                            | MinIO port                                              |
| env.slurmClientHost                | string | localhost                       | Slurm client host                                       |
| env.slurmClientPort                | int    | 8060                            | Slurm client port                                       |
| env.minioAccessKey                 | string | minioadmin                      | MinIO access key                                        |
| env.minioSecretKey                 | string | minioadmin                      | MinIO secret key                                        |
| env.minioSecure                    | bool   | false                           | Enable HTTPS for MinIO access                           |
| env.internalAPIKey                 | string | some key                        | API key for secure inter-component comms                |



## External MinIO and Redis Use
If customers choose external services:
Change env.minioService to external DNS/IP
Change env.redisService accordingly
Ensure correct port and credentials
Consider secure endpoint exposure via Ingress + TLS for production

## Internal MinIO Use

PSGC uses MinIO to:
* Provide a secure data ingress mechanism for workflows requiring external data uploads.
* Generate pre-signed URLs for users to upload large datasets without passing through the Control Manager.

Important Notes
The bundled MinIO deployment is basic — suitable for development or testing.

For production:
* Consider using a managed MinIO instance (or AWS S3/other object storage).
* Update PSGC’s values.yaml to point to external MinIO endpoints.
* When using internal MinIO, persistence must be enabled to avoid losing uploaded data if the pod restarts.

## Default MinIO Configuration Parameters
(from minio/values.yaml)
| Parameter                          | Type   | Default                       | Description                                             |
|------------------------------------|--------|---------------------------------|---------------------------------------------------------|
| replicaCount | int | 1 | Number of MinIO pods |
| image.repository | string | minio/minio | Image repository |
| image.tag | string | latest | Image tag/version |
| image.pullPolicy | string | IfNotPresent | Pull policy |
| service.name | string | minio-service | Service name |
| service.type | string | NodePort | Service type |
| service.port | int | 9000 | API service port |
| service.consolePort | int | 9001 | MinIO console port |
| service.apiNodePort | int | 30090 | NodePort for API endpoint |
| service.consoleNodePort | int | 30091 | NodePort for console UI |
| gateway.name | string | minio-gateway | Gateway name |
| gateway.host | string | hostname | Gateway host |
| gateway.listeners.api | string | minio-api | Gateway API listener name |
| gateway.listeners.console | string | minio-console | Gateway console listener name |
| persistence.enabled | bool | true | Enable persistent storage for MinIO |
| persistence.name | string | minio-data | PVC name |
| persistence.existingClaim | string | "" | Use existing PVC (leave empty for auto-create) |
| persistence.size | string | 10Gi | Storage capacity |
| persistence.storageClass | string | local-path | StorageClass name |
| configMap.name | string | minio-config | ConfigMap name |
| configMap.MINIO_ROOT_USER | string | minioadmin | MinIO admin username |
| configMap.MINIO_ROOT_PASSWORD | string | minioadmin | MinIO admin password |
| configMap.MINIO_BROWSER | string | on | Enable MinIO web console |
| configMap.MINIO_NOTIFY_WEBHOOK_ENABLE_1 | string | on | Enable webhook notifications |
| configMap.MINIO_NOTIFY_WEBHOOK_ENDPOINT_1 | string | http://psgc-service:8040/minio_event
 | Webhook endpoint for PSGC |

### Persistence Recommendations for MinIO

Persisting object storage is critical — without persistence:
Uploaded datasets will be lost after a pod restart or redeployment.

For internal MinIO:

```yaml
persistence:
  enabled: true
  name: minio-data
  size: 10Gi
  storageClass: local-path
```

This ensures that /data inside MinIO containers is backed by a Persistent Volume.


### Connecting PSGC to External MinIO
If you use an external MinIO or S3-compatible service:
Change PSGC’s values.yaml:

```yaml
env:
  minioService: external-minio.example.com
  minioPort: 9000
  minioAccessKey: `your-access-key`
  minioSecretKey: `your-secret-key`
  minioSecure: true  # use HTTPS if available
```

Deploy PSGC without the minio subchart enabled (disable in Helm install by not including that folder / or setting enabled: false).

## Verification
After deployment:

```
kubectl get pods -n decice
kubectl logs <minio-pod> -n decice
kubectl logs <psgc-pod> -n decice
```
