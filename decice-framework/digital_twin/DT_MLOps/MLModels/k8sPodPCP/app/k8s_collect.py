# k8s_collect.py
import os
import json
import argparse
import time
from collections import OrderedDict
from functools import lru_cache
from typing import Dict, List, Optional, Iterable, Tuple

try:
    import requests
except Exception:
    requests = None

from kubernetes import client, config, watch
from kubernetes.config.config_exception import ConfigException
from kubernetes.client.exceptions import ApiException
from pydantic import ValidationError

# If you have your logger, you can import it; otherwise basic prints will work.
try:
    from app.utils.logger_config import setup_logging
    logger = setup_logging(app_name="k8s-pod-power")
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("k8s-pod-power")

from models import InferenceRequest, ContainerSpec


# --- io helpers ---
def _open_output(path: Optional[str]):
    if not path:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return open(path, "a", buffering=1)  # line-buffered


def _post_if_needed(ir, url: Optional[str]):
    if not url:
        return
    if requests is None:
        logger.error("requests not installed; cannot POST. pip install requests")
        return
    try:
        r = requests.post(url, json=json.loads(ir.model_dump_json()), timeout=5)
        if r.status_code >= 300:
            logger.warning("POST %s -> %s: %s", url, r.status_code, r.text[:200])
    except Exception as e:
        logger.warning("POST error to %s: %s", url, e)


class SeenCache:
    def __init__(self, ttl_sec=10, max_items=5000):
        self.ttl = ttl_sec
        self.max = max_items
        self._d = OrderedDict()

    def seen(self, key):
        now = time.time()
        # purge old
        while self._d and (now - next(iter(self._d.values())) > self.ttl):
            self._d.popitem(last=False)
        # record & return previous existence
        existed = key in self._d
        self._d[key] = now
        if len(self._d) > self.max:
            self._d.popitem(last=False)
        return existed


# ---------- Quantity parsers ----------
def parse_cpu_to_mcpu(q: Optional[str]) -> Optional[int]:
    if not q:
        return None
    s = str(q).strip().lower()
    if s.endswith("m"):
        return int(float(s[:-1]))
    return int(float(s) * 1000)


def parse_mem_to_mib(q: Optional[str]) -> Optional[int]:
    if not q:
        return None
    s = str(q).strip().lower()
    multipliers = {
        "k": 1 / 1024, "ki": 1 / 1024,
        "m": 1, "mi": 1,
        "g": 1024, "gi": 1024,
        "t": 1024 * 1024, "ti": 1024 * 1024,
    }
    for suf, mul in multipliers.items():
        if s.endswith(suf):
            val = float(s[: -len(suf)])
            return int(val * mul)
    try:
        bytes_val = float(s)
        return int(bytes_val / (1024 * 1024))
    except ValueError:
        return None


# ---------- Extractors ----------
def _vol_type(v: Dict) -> str:
    keys = {
        "emptyDir", "hostPath", "persistentVolumeClaim", "configMap",
        "secret", "downwardAPI", "projected", "nfs", "ephemeral"
    }
    for k in keys:
        if k in v:
            return k
    return "other"


def _cronjob_pod_template(d: Dict) -> Dict:
    spec = d.get("spec") or {}
    jt = spec.get("jobTemplate") or spec.get("job_template") or {}
    jt_spec = jt.get("spec") or {}
    return jt_spec.get("template") or {}


def _to_container_spec(c: Dict) -> ContainerSpec:
    res = c.get("resources", {}) or {}
    req = res.get("requests", {}) or {}
    lim = res.get("limits", {}) or {}
    return ContainerSpec(
        name=c.get("name", ""),
        image=c.get("image", ""),
        command=c.get("command"),
        args=c.get("args"),
        req_cpu_mcpu=parse_cpu_to_mcpu(req.get("cpu")),
        req_mem_mib=parse_mem_to_mib(req.get("memory")),
        lim_cpu_mcpu=parse_cpu_to_mcpu(lim.get("cpu")),
        lim_mem_mib=parse_mem_to_mib(lim.get("memory")),
    )


def _count_sidecars(containers: List[Dict]) -> int:
    # (Optional) implement mesh/logging heuristics here
    return 0


def podtemplate_to_request(
    namespace: str,
    workload_kind: str,
    workload_name: str,
    pod_template: Dict,
    parent_spec: Optional[Dict] = None,
) -> InferenceRequest:
    meta = pod_template.get("metadata", {}) or {}
    spec = pod_template.get("spec", {}) or {}

    labels = dict(meta.get("labels", {}) or {})
    annotations = dict(meta.get("annotations", {}) or {})

    containers = [_to_container_spec(c) for c in (spec.get("containers") or [])]
    init_count = len(spec.get("initContainers") or [])
    volume_types = [_vol_type(v) for v in (spec.get("volumes") or [])]

    runtime_class = spec.get("runtimeClassName")
    node_selector = spec.get("nodeSelector") or {}
    node_type = (
        node_selector.get("node.kubernetes.io/instance-type") or
        node_selector.get("beta.kubernetes.io/instance-type")
    )

    # GPU (limits.*gpu*)
    gpu_count = 0
    for c in (spec.get("containers") or []):
        lim = (c.get("resources") or {}).get("limits") or {}
        for k, v in lim.items():
            if "gpu" in k:
                try:
                    gpu_count += int(float(v))
                except Exception:
                    pass

    parallelism = None
    completions = None
    if workload_kind.lower() == "job" and parent_spec:
        parallelism = parent_spec.get("parallelism")
        completions = parent_spec.get("completions")

    return InferenceRequest(
        namespace=namespace,
        workload_kind=workload_kind,
        workload_name=workload_name,
        labels=labels,
        annotations=annotations,
        containers=containers,
        init_container_count=init_count,
        sidecar_count=_count_sidecars(spec.get("containers") or []),
        volume_types=volume_types,
        node_type=node_type,
        runtime_class=runtime_class,
        gpu_count=gpu_count,
        parallelism=parallelism,
        completions=completions,
    )


def pod_to_request(pod: Dict) -> InferenceRequest:
    ns = pod["metadata"]["namespace"]
    name = pod["metadata"]["name"]
    labels = dict(pod["metadata"].get("labels") or {})
    annotations = dict(pod["metadata"].get("annotations") or {})
    spec = pod.get("spec") or {}

    # containers
    containers = [_to_container_spec(c) for c in (spec.get("containers") or [])]
    init_count = len(spec.get("initContainers") or [])

    # volumes
    volume_types = [_vol_type(v) for v in (spec.get("volumes") or [])]

    # scheduling/context
    runtime_class = spec.get("runtimeClassName")
    node_selector = spec.get("nodeSelector") or {}
    node_type = (
        node_selector.get("node.kubernetes.io/instance-type")
        or node_selector.get("beta.kubernetes.io/instance-type")
    )

    # gpu count
    gpu_count = 0
    for c in (spec.get("containers") or []):
        lim = (c.get("resources") or {}).get("limits") or {}
        for k, v in lim.items():
            if "gpu" in k:
                try:
                    gpu_count += int(float(v))
                except Exception:
                    pass

    # try to infer owner workload kind/name, else treat as Pod
    workload_kind = "Pod"
    workload_name = name
    for ref in (pod["metadata"].get("ownerReferences") or []):
        # Prefer higher-level owner if present (ReplicaSet→Deployment etc. is okay to keep as-is)
        workload_kind = ref.get("kind") or workload_kind
        workload_name = ref.get("name") or workload_name
        break

    return InferenceRequest(
        namespace=ns,
        workload_kind=workload_kind,
        workload_name=workload_name,
        labels=labels,
        annotations=annotations,
        containers=containers,
        init_container_count=init_count,
        sidecar_count=_count_sidecars(spec.get("containers") or []),
        volume_types=volume_types,
        node_type=node_type,
        runtime_class=runtime_class,
        gpu_count=gpu_count,
        parallelism=None,
        completions=None,
    )


# ---------- K8s config & clients (mirrors your reference style) ----------
def _load_k8s_config(kubeconfig: Optional[str] = None) -> None:
    """
    Try: explicit kubeconfig path -> local kubeconfig -> in-cluster.
    Raise ConfigException if none works.
    """
    try:
        if kubeconfig:
            logger.info("Loading kubeconfig from --kubeconfig=%s", kubeconfig)
            config.load_kube_config(config_file=kubeconfig)
            return
        logger.info("Trying to load local kubeconfig...")
        config.load_kube_config()
        logger.info("Loaded local kubeconfig.")
    except ConfigException:
        logger.warning("Local kubeconfig not found. Trying in-cluster config...")
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster config.")
        except ConfigException as e:
            logger.error("Failed to load any Kubernetes config.")
            raise


def _apply_ssl_settings(ca_file: Optional[str], verify_ssl: Optional[bool]) -> None:
    cfg = client.Configuration.get_default_copy()
    if verify_ssl is not None:
        cfg.verify_ssl = bool(verify_ssl)
    if ca_file:
        cfg.ssl_ca_cert = ca_file
    client.Configuration.set_default(cfg)


@lru_cache()
def get_apps_api(kubeconfig: Optional[str], ca_file: Optional[str], verify_ssl: Optional[bool]) -> client.AppsV1Api:
    _load_k8s_config(kubeconfig)
    _apply_ssl_settings(ca_file, verify_ssl)
    return client.AppsV1Api()


@lru_cache()
def get_batch_api(kubeconfig: Optional[str], ca_file: Optional[str], verify_ssl: Optional[bool]) -> client.BatchV1Api:
    _load_k8s_config(kubeconfig)
    _apply_ssl_settings(ca_file, verify_ssl)
    return client.BatchV1Api()


@lru_cache()
def get_core_api(kubeconfig: Optional[str], ca_file: Optional[str], verify_ssl: Optional[bool]) -> client.CoreV1Api:
    _load_k8s_config(kubeconfig)
    _apply_ssl_settings(ca_file, verify_ssl)
    return client.CoreV1Api()


# ---------- Watchers ----------
def stream_inference_requests(
    kinds: Tuple[str, ...] = ("Deployment", "Job", "CronJob"),
    namespaces: Optional[List[str]] = None,
    kubeconfig: Optional[str] = None,
    ca_file: Optional[str] = None,
    verify_ssl: Optional[bool] = None,
    seen_cache: "SeenCache" = None,
) -> Iterable[InferenceRequest]:
    """
    Watch K8s and yield InferenceRequest on ADDED/MODIFIED events.
    """
    w = watch.Watch()
    api_apps = get_apps_api(kubeconfig, ca_file, verify_ssl)
    api_batch = get_batch_api(kubeconfig, ca_file, verify_ssl)
    api_core = get_core_api(kubeconfig, ca_file, verify_ssl)

    if seen_cache is None:
        seen_cache = SeenCache()

    def handle_obj(kind: str, obj: Dict):
        ns = obj["metadata"]["namespace"]
        name = obj["metadata"]["name"]
        rv = obj["metadata"].get("resourceVersion") or "0"
        key = (ns, kind, name, rv)
        if seen_cache.seen(key):
            return
        if namespaces and ns not in namespaces:
            return
        if kind == "Deployment":
            tmpl = obj["spec"]["template"]
            yield podtemplate_to_request(ns, "Deployment", name, tmpl)
        elif kind == "Job":
            tmpl = obj["spec"]["template"]
            yield podtemplate_to_request(ns, "Job", name, tmpl, parent_spec=obj["spec"])
        elif kind == "CronJob":
            tmpl = _cronjob_pod_template(obj)
            if tmpl:
                yield podtemplate_to_request(ns, "CronJob", name, tmpl)
        elif kind == "Pod":
            yield pod_to_request(obj)

    try:
        if "Deployment" in kinds:
            for event in w.stream(api_apps.list_deployment_for_all_namespaces):
                if event["type"] in ("ADDED", "MODIFIED"):
                    yield from handle_obj("Deployment", event["object"].to_dict())

        if "Job" in kinds:
            for event in w.stream(api_batch.list_job_for_all_namespaces):
                if event["type"] in ("ADDED", "MODIFIED"):
                    yield from handle_obj("Job", event["object"].to_dict())

        if "CronJob" in kinds:
            for event in w.stream(api_batch.list_cron_job_for_all_namespaces):
                if event["type"] in ("ADDED", "MODIFIED"):
                    yield from handle_obj("CronJob", event["object"].to_dict())
        
        if "Pod" in kinds:
            for event in w.stream(api_core.list_pod_for_all_namespaces):
                if event["type"] in ("ADDED", "MODIFIED"):
                    yield from handle_obj("Pod", event["object"].to_dict())
    except ApiException as e:
        msg = f"K8s API error: {e.reason} (status: {e.status})"
        raise SystemExit(msg)
    except ConfigException as e:
        raise SystemExit(f"Kubernetes configuration could not be loaded: {e}")
    except Exception as e:
        raise SystemExit(str(e))


def list_and_emit_initial(
    kinds: Tuple[str, ...],
    namespaces: Optional[List[str]],
    kubeconfig: Optional[str],
    ca_file: Optional[str],
    verify_ssl: Optional[bool],
    seen_cache: "SeenCache",
) -> Iterable[InferenceRequest]:
    api_apps = get_apps_api(kubeconfig, ca_file, verify_ssl)
    api_batch = get_batch_api(kubeconfig, ca_file, verify_ssl)
    api_core = get_core_api(kubeconfig, ca_file, verify_ssl)

    if "Deployment" in kinds:
        for obj in api_apps.list_deployment_for_all_namespaces().items:
            d = obj.to_dict()
            ns = d["metadata"]["namespace"]
            name = d["metadata"]["name"]
            rv = d["metadata"].get("resourceVersion", "0")
            key = (ns, "Deployment", name, rv)
            if seen_cache.seen(key):
                continue
            if namespaces and ns not in namespaces:
                continue
            tmpl = d["spec"]["template"]
            yield podtemplate_to_request(ns, "Deployment", name, tmpl)

    if "Job" in kinds:
        for obj in api_batch.list_job_for_all_namespaces().items:
            d = obj.to_dict()
            ns = d["metadata"]["namespace"]
            name = d["metadata"]["name"]
            rv = d["metadata"].get("resourceVersion", "0")
            key = (ns, "Job", name, rv)
            if seen_cache.seen(key):
                continue
            if namespaces and ns not in namespaces:
                continue
            tmpl = d["spec"]["template"]
            yield podtemplate_to_request(ns, "Job", name, tmpl, parent_spec=d["spec"])

    if "CronJob" in kinds:
        for obj in api_batch.list_cron_job_for_all_namespaces().items:
            d = obj.to_dict()
            ns = d["metadata"]["namespace"]
            name = d["metadata"]["name"]
            rv = d["metadata"].get("resourceVersion", "0")
            key = (ns, "CronJob", name, rv)
            if seen_cache.seen(key):
                continue
            if namespaces and ns not in namespaces:
                continue
            tmpl = _cronjob_pod_template(d)
            if tmpl:
                yield podtemplate_to_request(ns, "CronJob", name, tmpl)
    if "Pod" in kinds:
        for obj in api_core.list_pod_for_all_namespaces().items:
            d = obj.to_dict()
            ns = d["metadata"]["namespace"]
            name = d["metadata"]["name"]
            rv = d["metadata"].get("resourceVersion", "0")
            key = (ns, "Pod", name, rv)
            if seen_cache.seen(key):
                continue
            if namespaces and ns not in namespaces:
                continue
            yield pod_to_request(d)


# ---------- CLI ----------
def _emit_from_obj(obj: Dict):
    kind = obj.get("kind")
    meta = obj.get("metadata", {}) or {}
    spec = obj.get("spec", {}) or {}
    ns = meta.get("namespace", "default")
    name = meta.get("name", "noname")

    if kind == "Deployment":
        ir = podtemplate_to_request(ns, "Deployment", name, spec["template"])
    elif kind == "Job":
        ir = podtemplate_to_request(ns, "Job", name, spec["template"], parent_spec=spec)
    elif kind == "CronJob":
        tmpl = spec["jobTemplate"]["spec"]["template"]
        ir = podtemplate_to_request(ns, "CronJob", name, tmpl)
    else:
        raise SystemExit(f"Unsupported kind: {kind}")

    print(ir.model_dump_json())


def main():
    parser = argparse.ArgumentParser(description="Collect inference inputs from K8s workloads.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_watch = sub.add_parser("watch", help="Watch cluster and emit InferenceRequest JSON lines.")
    p_watch.add_argument("--kinds", nargs="+", default=["Deployment", "Job", "CronJob"])
    p_watch.add_argument("--namespaces", nargs="*", default=None,
                         help="If omitted, watch all namespaces.")
    p_watch.add_argument("--emit-initial", action="store_true",
                         help="Emit current objects before watching.")
    p_watch.add_argument("--output", help="Write NDJSON to this file.")
    p_watch.add_argument("--post", help="POST each InferenceRequest to this URL.")
    p_watch.add_argument("--kubeconfig", default=os.getenv("KUBECONFIG"),
                         help="Path to kubeconfig (overrides detection).")
    p_watch.add_argument("--ca-file", default=os.getenv("K8S_CA_FILE"),
                         help="Path to cluster CA file (optional).")
    p_watch.add_argument("--verify-ssl", type=lambda v: v.lower() in ("1", "true", "yes"),
                         default=None, help="Force SSL verification on/off. Default: client default.")
    p_watch.add_argument("--suppress-tls-warnings", action="store_true",
                         help="Disable urllib3 InsecureRequestWarning (dev only).")

    p_file = sub.add_parser("from-file", help="Build InferenceRequest from a YAML manifest.")
    p_file.add_argument("path", help="Path to Deployment/Job/CronJob YAML")

    args = parser.parse_args()

    if getattr(args, "suppress_tls_warnings", False):
        import urllib3
        from urllib3.exceptions import InsecureRequestWarning
        urllib3.disable_warnings(InsecureRequestWarning)

    if args.cmd == "watch":
        out_f = _open_output(args.output)

        def _emit(ir):
            line = ir.model_dump_json()
            if out_f:
                out_f.write(line + "\n")
            print(line)

        seen_cache = SeenCache(ttl_sec=10)
        kinds = tuple(args.kinds)
        namespaces = args.namespaces

        if args.emit_initial:
            for ir in list_and_emit_initial(
                kinds, namespaces, args.kubeconfig, args.ca_file, args.verify_ssl, seen_cache
            ):
                _post_if_needed(ir, args.post)
                _emit(ir)

        for ir in stream_inference_requests(
            kinds, namespaces, args.kubeconfig, args.ca_file, args.verify_ssl, seen_cache
        ):
            _post_if_needed(ir, args.post)
            _emit(ir)
    else:
        import yaml
        with open(args.path, "r") as f:
            docs = list(yaml.safe_load_all(f))
        for obj in docs:
            _emit_from_obj(obj)


if __name__ == "__main__":
    main()
