# k8s-collect — Turn K8s manifests & live workloads into **InferenceRequest** events

This tool watches your Kubernetes cluster (or parses YAML files) and emits a normalized **InferenceRequest** JSON for each relevant workload. It’s useful when you want a lightweight stream of pod/workload specs for downstream services (e.g., schedulers, model profilers, energy estimators).

---

## ✨ What it does

* **Watches** Deployments, Jobs, CronJobs (and optionally Pods) across namespaces.
* **Normalizes** container specs into a Pydantic model: `InferenceRequest` with a list of `ContainerSpec`s.
* **Streams** newline-delimited JSON (**NDJSON**) to stdout and/or a file.
* **Optionally POSTs** every event to an HTTP endpoint you provide.
* **Parses YAML** (“from-file” mode) to output the same JSON without hitting the cluster.

> The script expects `models.py` to define the Pydantic models `InferenceRequest` and `ContainerSpec`.

---

## 📦 Requirements

* Python 3.9+
* Packages: `kubernetes`, `pydantic`, `pyyaml` (for `from-file`), `requests` (only if using `--post`)

```bash
pip install kubernetes pydantic pyyaml requests
```

Optional env vars:

* `KUBECONFIG` — default kubeconfig path
* `K8S_CA_FILE` — custom CA file for the Kubernetes API client

---

## 🧰 CLI Usage

```bash
python k8s_collect.py <command> [options]
```

### Commands

1. `watch` — watch the cluster and emit `InferenceRequest` events.
2. `from-file <path>` — read a Deployment/Job/CronJob YAML and emit `InferenceRequest` JSON.

---

## 🔭 `watch` command

Watches for **ADDED**/**MODIFIED** events and emits normalized JSON for each object.

**Basic:**

```bash
python k8s_collect.py watch
```

**Filter kinds & namespaces, dump to file, and POST to an API:**

```bash
python k8s_collect.py watch \
  --kinds Deployment Job CronJob Pod \
  --namespaces default mohsen \
  --emit-initial \
  --output ./out/events.ndjson \
  --post http://localhost:8000/infer \
  --kubeconfig ~/.kube/config \
  --ca-file /etc/ssl/certs/ca.pem \
  --verify-ssl true
```

### Options

* `--kinds` *(list)*: Which resource kinds to watch. Supported: `Deployment`, `Job`, `CronJob`, `Pod`. Default: `Deployment Job CronJob`.
* `--namespaces` *(list)*: Restrict to these namespaces. Default: all namespaces.
* `--emit-initial`: Emit current objects first (a snapshot) before continuing to watch.
* `--output <path>`: Append NDJSON to this file (still prints to stdout).
* `--post <url>`: HTTP POST each event to this URL as JSON (`requests` required).
* `--kubeconfig <path>`: Path to kubeconfig. Defaults to `$KUBECONFIG` or autodetect; falls back to in-cluster config.
* `--ca-file <path>`: Custom CA bundle for the Kubernetes client.
* `--verify-ssl true|false`: Force SSL verification on/off. Default: client default.
* `--suppress-tls-warnings`: Hide `urllib3` insecure warnings (for dev only).

### Output format (NDJSON)

Each line is a serialized `InferenceRequest`. Example (fields may vary depending on your `models.py`):

```json
{
  "namespace": "mohsen",
  "workload_kind": "Deployment",
  "workload_name": "nginx",
  "labels": {"app": "nginx"},
  "annotations": {},
  "containers": [
    {
      "name": "nginx",
      "image": "nginx:1.27",
      "command": null,
      "args": null,
      "req_cpu_mcpu": 100,
      "req_mem_mib": 128,
      "lim_cpu_mcpu": 500,
      "lim_mem_mib": 512
    }
  ],
  "init_container_count": 0,
  "sidecar_count": 0,
  "volume_types": ["configMap", "persistentVolumeClaim"],
  "node_type": null,
  "runtime_class": null,
  "gpu_count": 0,
  "parallelism": null,
  "completions": null
}
```

> **De-duplication:** Events are cached for `ttl=10s` using a `(namespace, kind, name, resourceVersion)` key to avoid repeats.

---

## 📄 `from-file` command

Parse one or more YAML docs (Deployment/Job/CronJob) and emit the corresponding `InferenceRequest` JSON to stdout.

```bash
python k8s_collect.py from-file ./my-deploy.yaml
```

This **does not** contact the cluster. It is ideal for offline testing or CI.

---

## 🔐 Kube auth & config resolution

The client attempts the following, in order:

1. Use `--kubeconfig` if provided, else `$KUBECONFIG`.
2. Try the default local kubeconfig (`~/.kube/config`).
3. Fall back to **in-cluster** config (when running inside Kubernetes).

Use `--verify-ssl` and `--ca-file` to adjust TLS. Add `--suppress-tls-warnings` to hide insecure warnings in dev.

---

## 🧱 Minimal RBAC (read-only)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k8s-collect-read
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
```

Grant it with a `ClusterRoleBinding` to the ServiceAccount running this tool.

---

## 🧩 Pydantic model expectations

Your `models.py` should export:

* `ContainerSpec(name, image, command, args, req_cpu_mcpu, req_mem_mib, lim_cpu_mcpu, lim_mem_mib)`
* `InferenceRequest(namespace, workload_kind, workload_name, labels, annotations, containers, init_container_count, sidecar_count, volume_types, node_type, runtime_class, gpu_count, parallelism, completions)`

> The script uses `ir.model_dump_json()` to serialize, and `json.loads(...)` when POSTing.

---

## 🔌 Posting events to an HTTP endpoint

Add `--post http://your-service/endpoint` to `watch`. Each emitted `InferenceRequest` is sent as the request body (JSON). Non-2xx responses are logged as warnings; failures don’t stop the watcher.

Example FastAPI receiver:

```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/infer")
async def receive_inference(ir: dict):
    # validate & enqueue for downstream processing
    return {"ok": True}
```

Run the watcher:

```bash
python k8s_collect.py watch --post http://localhost:8000/infer
```

---

## 🧪 Programmatic usage (as a library)

You can import the generators and iterate them in your own code.

```python
from k8s_collect import stream_inference_requests, list_and_emit_initial, SeenCache

cache = SeenCache(ttl_sec=10)

# One-time snapshot
for ir in list_and_emit_initial(
    kinds=("Deployment", "Job", "CronJob", "Pod"),
    namespaces=["default"],
    kubeconfig=None, ca_file=None, verify_ssl=None,
    seen_cache=cache,
):
    handle(ir)

# Continuous stream
for ir in stream_inference_requests(
    kinds=("Deployment", "Job", "CronJob"),
    namespaces=None,
    kubeconfig=None, ca_file=None, verify_ssl=None,
    seen_cache=cache,
):
    handle(ir)
```

---

## 🧠 Key implementation details

* **Resource kinds:** `Deployment`, `Job`, `CronJob` (plus `Pod` if you include it in `--kinds`).
* **CronJob template:** extracted via `spec.jobTemplate.spec.template`.
* **GPU detection:** sums any `resources.limits` keys that include the substring `gpu`.
* **Resource parsing:** CPU to **mCPU** (e.g., `500m` → 500; `2` → 2000). Memory to **MiB** (supports Ki/Mi/Gi/Ti; raw bytes are converted to MiB).
* **Sidecars:** `_count_sidecars` is currently a stub — extend it with mesh/logging heuristics if needed.

---

## 🐳 Containerization (optional)

**Dockerfile (example):**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY k8s_collect.py models.py ./
RUN pip install kubernetes pydantic pyyaml requests
CMD ["python", "k8s_collect.py", "watch", "--emit-initial"]
```

**Run in-cluster (Deployment snippet):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-collect
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels: {app: k8s-collect}
  template:
    metadata:
      labels: {app: k8s-collect}
    spec:
      serviceAccountName: k8s-collect
      containers:
      - name: collector
        image: yourrepo/k8s-collect:latest
        args: ["watch", "--emit-initial", "--kinds", "Deployment", "Job", "CronJob"]
        env:
        - name: K8S_CA_FILE
          value: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        # Add --post URL if needed
```

---



