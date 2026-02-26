# WATMON

## Vertexpool Service
### Overview
WATMON (Wide-Area Telemetry Monitor) is designed to measure additional network performance metrics not available in Prometheus Node Exporter.

Architecture:

Vertexpool Service (central controller):
* Runs on a single node in the cluster.
* Maintains the mapping of all nodes/devices into Vertexpools (logical network groups).
* Assigns nodes to pools automatically based on network topology.
* Simplifies network graph modeling by aggregating intra-pool metrics and reducing measurement redundancy.

Provides APIs to Network Exporters for:
* Vertex list updates (nodes/devices + IPs)
* Vertexpool membership states
* Measurement strategy parameters (currently round-robin)

Network Exporters (daemonset — documented separately):
* Measure latency across vertices within and outside their pool.
* Controlled entirely by Vertexpool Service POST updates.

Benefits of Vertexpool Abstraction
* Reduced measurement overhead: fewer required network probe cycles.
* Simplified graph representation: fewer edges, averaged per pool-to-pool connection.
* Easier scaling: network monitoring overhead grows more slowly with node count.

### Prerequisites
* Kubernetes cluster (v1.29+)
* Helm ≥ 3.x

Namespace created for WATMON:

```
kubectl create namespace decice
```

Prometheus stack deployed and reachable from Vertexpool Service (prometheusUrl must be updated to match deployment).

Ensure the chosen nodeSelector label is present on the node that will run Vertexpool Service.

### Recommended Installation
Export and customize:

```
helm show values myrepo/watmon-service > values.watmon-service.yaml
```

Install:

```
helm install watmon-service myrepo/watmon-service \
  -n decice \
  -f values.watmon-service.yaml
```

### Configuration Parameters
| Parameter                           | Type   | Default                | Description                                          |
|-------------------------------------|--------|------------------------|------------------------------------------------------|
| settings.prometheusUrl                     | string | http://prometheus-stack-kube-prom-prometheus.monitoring:9090 | URL of Prometheus instance                               |
| settings.promql.networkDelayRangeSelector  | string | 1m                                                            | PromQL range selector for network delay metrics           |
| settings.hostDatabaseDirectoryPath         | string | /var/local/watmon_decice_service_data                         | Path on host node to store WATMON service database        |
| service.nodeSelector                       | string | hostname                                                       | Node label for where to run Vertexpool Service            |
| service.nodePort                           | int    | 30098                                                          | NodePort to expose Vertexpool Service API                 |
| image.registry                             | string | http://your-image-registry                                     | Image registry                                            |
| image.repository                           | string | watmon_decice_service                                          | Image repository                                          |
| image.tag                                  | string | test                                                           | Image tag                                                 |
| image.imagePullPolicy                      | string | IfNotPresent                                                   | Image pull policy                                         |
| image.secret                               | string | decice-image-registry                                          | Secret for registry authentication                        |




### Persistence & Data Storage
Vertexpool Service persists its database locally on the chosen host node (path configured via settings.hostDatabaseDirectoryPath).

This is not inside a PVC — meaning:

* If the node is drained or replaced, WATMON service data may be lost.
* For production, bind this path to a host-mounted persistent directory or configure storage that survives node changes.

### Deployment Notes
Single-node scheduling:
* The Vertexpool Service is designed to run on only one node.
* Adjust service.nodeSelector to match your intended node.
* Ensure Prometheus instance is accessible and network delay metrics are already being scraped.

### Verification
After installation:

```
kubectl get pods -n decice
kubectl logs <watmon-service-pod> -n decice
```

## Network Exporter

### Overview
The Network Exporter chart deploys a daemonset of exporter pods across all cluster nodes.

Each exporter:
* Measures latency to vertices in other Vertexpools and within its own pool.
* Selects a vertex from each pool in a round-robin manner to minimize measurement bias.

By default:
* Pings one vertex from every other Vertexpool every 5 seconds.
* Pings one vertex from its own Vertexpool every 30 seconds.

Receives POST updates from the Vertexpool Service to:
* Update vertex lists (nodes/devices and their IPs)
* Update Vertexpool membership states
* Modify measurement frequency and strategy

Because the exporters run as a daemonset, every node in the cluster gets its own exporter instance.

### Prerequisites
* Kubernetes cluster (v1.29+)
* Helm ≥ 3.x

The Vertexpool Service chart must be running — exporters rely on its POST updates.
Prometheus stack deployed and reachable from each exporter pod.
Correct prometheusUrl in values.yaml.

### Recommended Installation
Export and customize values:

```
helm show values myrepo/watmon-exporter > values.watmon-exporter.yaml
```

Install:

```
helm install watmon-exporter myrepo/watmon-exporter \
  -n decice \
  -f values.watmon-exporter.yaml
```

### Configuration Parameters


| Parameter                           | Type   | Default                | Description                                          |
|-------------------------------------|--------|------------------------|------------------------------------------------------|
| settings.prometheusUrl                      | string | http://prometheus-stack-kube-prom-prometheus.monitoring:9090       | URL of Prometheus instance                            |
| settings.promql.networkDelayRangeSelector   | string | 1m                                                                  | PromQL range selector for network delay metrics       |
| image.registry                              | string | http://your-image-registry                                          | Image registry URL                                    |
| image.repository                            | string | decice-image                                                        | Image repository name                                 |
| image.tag                                   | string | test                                                                | Image tag version                                     |
| image.secret                                | string | decice-image-registry                                               | Secret for private registry pull                      |
| image.imagePullPolicy                       | string | IfNotPresent                                                        | Image pull policy                                     |
| image.additionalNodeSelectorTerms           | list   | (empty)                                                             | Additional node selector terms for exporter placement |



### Deployment Notes
Since this is a daemonset, by default it runs on all schedulable nodes.
To restrict where exporters run, use image.additionalNodeSelectorTerms in values.yaml:

```yaml=
image:
  additionalNodeSelectorTerms:
    - matchExpressions:
        - key: node-role.kubernetes.io/worker
          operator: Exists
```

Exporters must be able to reach the Vertexpool Service’s exposed nodePort.


### Verification
After deployment:

```
kubectl get pods -n decice -l app=watmon-exporter
kubectl logs <watmon-exporter-pod> -n decice
