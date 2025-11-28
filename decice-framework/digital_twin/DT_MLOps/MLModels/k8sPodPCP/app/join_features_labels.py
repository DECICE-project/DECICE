#!/usr/bin/env python3
import argparse, re, pandas as pd

RS_HASH = re.compile(r"^(?P<base>.+)-[a-f0-9]{9,}$")          # e.g. myapp-75b8db778
POD_FROM_RS = re.compile(r"^(?P<base>.+)-[a-f0-9]{9,}-[a-z0-9]{5}$")  # myapp-75b8db778-abcde

def canon_workload(kind: str, name: str) -> tuple[str, str]:
    """Return (canon_kind, canon_name) suitable to match Deployment features."""
    kind = (kind or "").strip()
    name = (name or "").strip()
    if kind == "Deployment":
        return "Deployment", name
    if kind == "ReplicaSet":
        m = RS_HASH.match(name)
        return ("Deployment", m.group("base")) if m else ("Deployment", name)
    if kind == "Pod":
        # Pods owned by a Deployment usually look like myapp-<rs-hash>-<pod5>
        m = POD_FROM_RS.match(name) or RS_HASH.match(name)
        return ("Deployment", m.group("base")) if m else ("Pod", name)
    # Pass through DaemonSet/StatefulSet/Job/CronJob (may not match features)
    return kind, name

def norm_keys(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ("namespace", "workload_kind", "workload_name"):
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    if "namespace" in df.columns:
        df["namespace"] = df["namespace"].str.lower()
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    F = pd.read_parquet(args.features)   # expects: namespace, workload_kind, workload_name, ...
    L = pd.read_parquet(args.labels)     # expects: namespace, workload_kind, workload_name, ...

    F = norm_keys(F)
    L = norm_keys(L)

    # Canonicalize BOTH sides (features are usually already Deployment, but harmless)
    F[['canon_kind','canon_name']] = F.apply(
        lambda r: pd.Series(canon_workload(r.get('workload_kind',''), r.get('workload_name',''))), axis=1
    )
    L[['canon_kind','canon_name']] = L.apply(
        lambda r: pd.Series(canon_workload(r.get('workload_kind',''), r.get('workload_name',''))), axis=1
    )

    # Join by namespace + canonical name (ignore kind to be more tolerant)
    left = L.rename(columns={"namespace":"ns"})  # avoid column collisions in merge suffixes
    right = F.rename(columns={"namespace":"ns"})
    keepF = [c for c in ['_spec_hash','features'] if c in right.columns]

    J = left.merge(
        right[['ns','canon_name'] + keepF],
        on=['ns','canon_name'],
        how='inner',
        suffixes=('_lab', '_feat'),
    ).rename(columns={"ns":"namespace"})

    if len(J) == 0:
        print('[WARN] 0 rows joined. Diagnostics:')
        Lk = L[['namespace','canon_name']].drop_duplicates()
        Fk = F[['namespace','canon_name']].drop_duplicates()
        inter = pd.merge(Lk, Fk, on=['namespace','canon_name'])
        print('  features unique (ns,canon_name):', len(Fk))
        print('  labels   unique (ns,canon_name):', len(Lk))
        print('  intersection                  :', len(inter))
        print('  sample features:\n', F[['namespace','workload_kind','workload_name']].drop_duplicates().head(10).to_string(index=False))
        print('  sample labels:\n',   L[['namespace','workload_kind','workload_name']].drop_duplicates().head(10).to_string(index=False))

    J.to_parquet(args.out, index=False)
    print(f'[OK] joined {len(J)} rows -> {args.out}')

if __name__ == "__main__":
    main()