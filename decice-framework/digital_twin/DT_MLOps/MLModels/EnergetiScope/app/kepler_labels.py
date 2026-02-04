#!/usr/bin/env python3
import argparse, requests, numpy as np, pandas as pd

# Optional K8s fallback for owner mapping
from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.config.config_exception import ConfigException

def prom_range(prom_base: str, query: str, start: str, end: str, step: str) -> pd.DataFrame:
    r = requests.get(
        f"{prom_base.rstrip('/')}/api/v1/query_range",
        params={"query": query, "start": start, "end": end, "step": step},
        timeout=30,
    )
    r.raise_for_status()
    result = r.json().get("data", {}).get("result", [])
    rows = []
    for s in result:
        metric = s.get("metric", {})
        for ts, val in s.get("values", []):
            rows.append({"ts": float(ts), "value": float(val), **metric})
    df = pd.DataFrame(rows)
    return df

def norm_ns_pod(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    # namespace
    if "namespace" not in df.columns:
        for cand in ("container_namespace", "pod_namespace", "kubernetes_namespace", "ns"):
            if cand in df.columns:
                df.rename(columns={cand: "namespace"}, inplace=True)
                break
    # pod
    if "pod" not in df.columns:
        for cand in ("pod_name", "podname", "pod_uid", "podid"):
            if cand in df.columns:
                df.rename(columns={cand: "pod"}, inplace=True)
                break
    return df

def get_owner_map_via_k8s(namespaces=None) -> pd.DataFrame:
    try:
        try:
            k8s_config.load_kube_config()
        except ConfigException:
            k8s_config.load_incluster_config()
    except Exception as e:
        raise SystemExit(f"K8s config error: {e}")

    v1 = k8s_client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces().items
    rows = []
    for p in pods:
        ns = p.metadata.namespace
        if namespaces and ns not in namespaces:
            continue
        pod = p.metadata.name
        orefs = p.metadata.owner_references or []
        if orefs:
            ok = orefs[0].kind
            on = orefs[0].name
        else:
            ok, on = "Pod", pod
        rows.append({"namespace": ns, "pod": pod, "owner_kind": ok, "owner_name": on})
    return pd.DataFrame(rows)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prom", default="http://prometheus.lpt.local", help="Prometheus base URL")
    p.add_argument("--owner-source", choices=["prom","k8s","auto"], default="auto",
                   help="Where to get pod→owner mapping. 'auto' tries Prom first then K8s API. Default: k8s.")
    p.add_argument("--mode", choices=["job","window"], default="window")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--step", default="60s")
    p.add_argument("--ns", nargs="*", default=None, help="Namespace filter for K8s fallback owner map.")
    p.add_argument("--suppress-tls-warnings", action="store_true")
    args = p.parse_args()

    if args.suppress_tls_warnings:
        import urllib3
        from urllib3.exceptions import InsecureRequestWarning
        urllib3.disable_warnings(InsecureRequestWarning)

    # ---- owner mapping (prefer prom) ----
    owner = pd.DataFrame()
    if args.owner_source in ("prom", "auto"):
        try:
            owner = prom_range(
                args.prom,
                # pull all kinds; we will normalize below
                'max by(namespace,pod,owner_kind,owner_name) (kube_pod_owner)',
                args.start, args.end, args.step
            )
            owner = norm_ns_pod(owner)
            if not owner.empty:
                owner = owner[["namespace","pod","owner_kind","owner_name","ts"]]
        except Exception:
            owner = pd.DataFrame()

    if owner.empty:
        if args.owner_source == "prom":
            raise SystemExit("No owner mapping found from Prometheus (kube_pod_owner missing).")
        owner = get_owner_map_via_k8s(namespaces=args.ns)  # no ts column here

    # ---- Kepler metrics ----
    # POWER is optional in your build; try it, but it's OK if empty.
    try:
        power = prom_range(
            args.prom,
            'sum by (container_namespace,pod_name) (kepler_container_power_watt)',
            args.start, args.end, args.step
        )
    except Exception:
        power = pd.DataFrame()
    power = norm_ns_pod(power)
    if not power.empty:
        power.rename(columns={"value": "avg_power_w"}, inplace=True)

    # Your cluster exposes container-level energy; use that metric specifically.
    energy = prom_range(
        args.prom,
        'sum by (container_namespace,pod_name) (kepler_container_joules_total)',
        args.start, args.end, args.step
    )
    energy = norm_ns_pod(energy) if energy is not None else pd.DataFrame()
    # Drop any rows that still don't have namespace/pod (e.g., node/system series)
    if not energy.empty:
        need = {"namespace", "pod"}
        missing = [c for c in need if c not in energy.columns]
        if missing:
            # keep only rows that have the needed labels if present as alt names
            # (shouldn't happen now, but safe)
            pass
        energy = energy.dropna(subset=["namespace","pod"], how="any")
        if not energy.empty:
            energy = energy.sort_values(["namespace","pod","ts"])
    if not energy.empty:
        energy["energy_step_j"] = energy.groupby(["namespace","pod"])["value"].diff().clip(lower=0.0)

    # ---- build label table robustly ----
    if power.empty and energy.empty:
        raise SystemExit("No Kepler power/energy data returned. Check that Kepler is installed and scraped by Prometheus.")

    # ensure both sides exist with needed columns
    if power.empty:
        power = energy[["namespace","pod","ts"]].copy()
        power["avg_power_w"] = np.nan
    if energy.empty:
        energy = power[["namespace","pod","ts"]].copy()
        energy["energy_step_j"] = np.nan

    lab = power.merge(energy[["namespace","pod","ts","energy_step_j"]],
                      on=["namespace","pod","ts"], how="left")

    if "ts" in owner.columns:
        lab = lab.merge(owner, on=["namespace","pod","ts"], how="left")
    else:
        lab = lab.merge(owner, on=["namespace","pod"], how="left")

    # --- normalize owner to match features keys ---
    import re
    def _rs_to_deploy(name: str) -> str:
        # ReplicaSet "myapp-75b8db778" -> Deployment "myapp"
        return re.sub(r"-[a-f0-9]{9,}$", "", name or "")

    wk = lab["owner_kind"].fillna("Pod")
    wn = lab["owner_name"].copy()
    # Map ReplicaSet → Deployment (name without RS suffix)
    rs_mask = wk.eq("ReplicaSet") & wn.notna()
    wk.loc[rs_mask] = "Deployment"
    wn.loc[rs_mask] = wn.loc[rs_mask].map(_rs_to_deploy)
    # Fall back
    wn = wn.fillna(lab["pod"])
    lab["workload_kind"] = wk
    lab["workload_name"] = wn

    if args.mode == "job":
        out = lab.groupby(["namespace","workload_kind","workload_name","pod"], as_index=False).agg(
            avg_power_w=("avg_power_w","mean"),
            total_energy_j=("energy_step_j","sum"),
        )
    else:
        out = lab[["ts","namespace","workload_kind","workload_name","pod","avg_power_w","energy_step_j"]].copy()

    out.to_parquet(args.out, index=False)
    print(f"[OK] wrote {len(out)} rows to {args.out}")

if __name__ == "__main__":
    main()
