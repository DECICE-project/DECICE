# Digital Twin

## Overview
The Digital Twin (DT) is a key DECICE component that provides:
* Real-time operational metrics across the device–edge–cloud continuum
* Derived predictive metrics from embedded ML models (future estimates, anomaly detection)
* Data to inform AI Scheduler and policy-driven workload placement decisions

Core Functions:
* Retrieves raw telemetry from PromQL-to-JSON Wrapper
* Uses ML models to infer predictive states
* Combines live and forecast data for adaptive scheduling
* Stores metrics and predictions in InfluxDB (subchart dependency)

InfluxDB role:
* Persistent, queryable time-series store for snapshot data
* Feeds historical data into AI Scheduler and analytics pipelines

## Prerequisites
* Kubernetes cluster (vX.Y+)
* Helm ≥ 3.x
Namespace created for DECICE components:

```
kubectl create namespace decice
```

Critical: Persistent Volume Claim for InfluxDB must exist or be provisionable by cluster storage class.
InfluxDB will lose all data if its PVC is not enabled

## Recommended Installation
Export and customize:
```
helm show values myrepo/digital-twin > values.digital-twin.yaml
```
Install:
```
helm install digital-twin myrepo/digital-twin \
  -n decice \
  -f values.digital-twin.yaml
```

## Configuration Parameters
### DT

| Parameter                         | Type   | Default                     | Description                               |
|-----------------------------------|--------|-----------------------------|-------------------------------------------|
| applicationName                   | string | digital-twin                | App name                                  |
| replicaCount                      | int    | 1                           | Number of DT pod replicas                 |
| image.registry                    | string | http://your-image-registry | Container image registry                  |
| image.repository                  | string | decice-digital-twin        | Repository name                           |
| image.tag                         | string | test                        | Image tag                                 |
| image.secret                      | string | decice-image-registry       | Secret for private registry pulls         |
| image.imagePullPolicy             | string | IfNotPresent                | Pull policy                               |
| service.name                      | string | digital-twin-service        | Service name                              |
| service.type                      | string | NodePort                    | Service type                              |
| service.servicePort               | int    | 8010                        | Port exposed                              |
| service.nodePort                  | int    | 30081                       | NodePort (used if type: NodePort)         |
| configMap.name                    | string | digital-twin-config         | ConfigMap name                            |
| env.digitalTwinHost               | string | 0.0.0.0                     | Binding host                              |
| env.digitalTwinPort               | int    | 8010                        | Binding port                              |
| env.schedulerControllerService    | string | scheduler-controller-service| Downstream Scheduler Controller            |
| env.schedulerControllerPort       | int    | 8020                        | Port for Scheduler Controller             |
| env.promqlWrapperService          | string | promql-json-wrapper-service | PromQL wrapper service                    |
| env.promqlWrapperPort             | int    | 8050                        | PromQL wrapper port                       |
| env.influxdbToken                 | string | "influxdb-secret-token"     | Auth token for InfluxDB                   |
| env.influxdbUrl                   | string | "http://influxdb-dt"        | InfluxDB service URL                      |
| env.influxdbBucket                | string | "cluster_snapshot"          | Default bucket                            |
| env.influxdbOrg                   | string | "decice"                    | Organization name in InfluxDB             |

### InfluxDB

| Parameter                           | Type   | Default                | Description                                          |
|-------------------------------------|--------|------------------------|------------------------------------------------------|
| influxdb.enabled                    | bool   | true                   | Deploy InfluxDB subchart                             |
| influxdb.fullnameOverride           | string | influxdb-dt            | InfluxDB service/deployment name                     |
| influxdb.adminUser.user             | string | admin                  | Admin username                                       |
| influxdb.adminUser.password         | string | admindecice            | Admin password                                       |
| influxdb.adminUser.token            | string | influxdb-secret-token  | API token matching DT env.influxdbToken              |
| influxdb.adminUser.organization     | string | decice                 | Organization name                                    |
| influxdb.adminUser.bucket           | string | cluster_snapshot       | Default data bucket                                  |
| influxdb.persistence.enabled        | bool   | true                   | Enable persistent storage for InfluxDB               |
| influxdb.persistence.useExisting     | bool   | true                   | Use pre-created PVC                                  |
| influxdb.persistence.name           | string | influxdb-dt            | Name of PVC                                          |
| influxdb.persistence.size           | string | (commented, example 8Gi)| Size of volume                                       |
| influxdb.service.type               | string | NodePort               | InfluxDB service type                                |
| influxdb.service.port               | int    | 80                     | External port                                        |
| influxdb.service.nodePort           | int    | 32086                  | NodePort mapping                                     |
| influxdb.service.targetPort         | int    | 8086                   | InfluxDB container port                              |


## Persistence & Storage
For Digital Twin:

Core DT logs: optionally enabled via persistence.enabled in DT values
InfluxDB storage: highly recommended to always have persistence enabled

Either allow Helm to create the PVC via cluster’s StorageClass
Or pre-create PVC named influxdb-dt in namespace before installation

Example PVC for InfluxDB:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: influxdb-dt
  namespace: decice
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 8Gi
```

Add in deployment.yaml:

```yaml
          {{- if .Values.persistence.enabled }}
          volumeMounts:
            - name: dt-storage
              mountPath: {{ .Values.persistence.mountPath }}
          {{- end }}

      {{- if .Values.persistence.enabled }}
      volumes:
        - name: dt-storage
          persistentVolumeClaim:
            claimName: {{ .Values.persistence.claimName }}
      {{- end }}
```

## Verification

```
kubectl get pods -n decice
kubectl logs <digital-twin-pod> -n decice
```

Check that:
DT logs confirm the application startup
InfluxDB pod is healthy and service returns data at `http://<nodeIP>:32086`
