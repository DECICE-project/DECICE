#!/usr/bin/env python3
"""
K8s InferenceRequest encoder:
- Fit:   k8s_encode.py fit --input data.ndjson --out encoder.joblib [--no-sbert]
- Trans: k8s_encode.py transform --input data.ndjson --encoder encoder.joblib --out features.parquet
"""
import argparse, json, os, sys, hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from joblib import dump, load

# --- optional SBERT (disable with --no-sbert)
try:
    from sentence_transformers import SentenceTransformer
    _SBERT_AVAILABLE = True
except Exception:
    _SBERT_AVAILABLE = False


# -------- schema & helpers --------
TEXT_KEYS_CONTAINER = ("image", "command", "args")
TEXT_KEYS_TOP = ("workload_kind", "workload_name")
CAT_KEYS = ("runtime_class", "node_type")
NUM_KEYS = ("gpu_count", "init_container_count", "sidecar_count")

# Per-container resources (flattened as sums; easy baseline)
RES_KEYS = (
    "req_cpu_mcpu", "req_mem_mib",
    "lim_cpu_mcpu", "lim_mem_mib"
)

def _sha16(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]

def _text_bundle(ir: Dict[str, Any]) -> str:
    """Concatenate semantically meaningful strings for SBERT."""
    parts: List[str] = []
    # top
    for k in TEXT_KEYS_TOP:
        v = ir.get(k)
        if v: parts.append(f"{k}:{v}")
    # labels/annotations
    for k,v in sorted((ir.get("labels") or {}).items()):
        parts.append(f"label:{k}={v}")
    for k,v in sorted((ir.get("annotations") or {}).items()):
        parts.append(f"ann:{k}={v}")
    # containers
    for c in ir.get("containers") or []:
        for k in TEXT_KEYS_CONTAINER:
            v = c.get(k)
            if isinstance(v, list):
                v = " ".join(map(str, v))
            if v:
                parts.append(f"{k}:{v}")
    return " | ".join(parts) if parts else "empty"


def _aggregate_resources(ir: Dict[str, Any]) -> Dict[str, float]:
    """Sum resource numbers across containers (baseline)."""
    sums = {k: 0.0 for k in RES_KEYS}
    for c in ir.get("containers") or []:
        for k in RES_KEYS:
            v = c.get(k)
            if v is not None:
                sums[k] += float(v)
    return sums


def _flat_row(ir: Dict[str, Any]) -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    row["namespace"] = ir.get("namespace")
    row["workload_kind"] = ir.get("workload_kind")
    row["workload_name"] = ir.get("workload_name")

    # categorical small set
    row["runtime_class"] = ir.get("runtime_class")
    row["node_type"] = ir.get("node_type")

    # counts
    row["gpu_count"] = ir.get("gpu_count", 0) or 0
    row["init_container_count"] = ir.get("init_container_count", 0) or 0
    row["sidecar_count"] = ir.get("sidecar_count", 0) or 0

    # resources
    sums = _aggregate_resources(ir)
    row.update(sums)  # adds req/lim cpu/mem sums

    # text bundle for SBERT
    row["_text"] = _text_bundle(ir)
    row["_spec_hash"] = _sha16(ir)  # handy for caching
    return row


# ---------- Encoder class ----------
@dataclass
class K8sEncoder:
    use_sbert: bool = True
    sbert_model_name: str = "all-MiniLM-L6-v2"

    # fitted artifacts
    scaler: Optional[StandardScaler] = None
    ohe: Optional[OneHotEncoder] = None
    sbert_name_: Optional[str] = None

    # cached model (runtime only)
    _sbert_model: Any = None

    def _ensure_sbert(self):
        if not self.use_sbert:
            return
        if not _SBERT_AVAILABLE:
            raise RuntimeError("sentence-transformers not installed; run: pip install sentence-transformers")
        if self._sbert_model is None:
            self._sbert_model = SentenceTransformer(self.sbert_model_name)
            self.sbert_name_ = self.sbert_model_name

    def fit(self, rows: List[Dict[str, Any]]):
        """Fit scalers/encoders from flattened rows."""
        df = pd.DataFrame(rows)

        # numeric matrix
        X_num = df[list(NUM_KEYS) + list(RES_KEYS)].astype(float).fillna(0.0)
        self.scaler = StandardScaler().fit(X_num)

        # categorical
        X_cat = df[list(CAT_KEYS)].astype(object).fillna("NA")
        self.ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        self.ohe.fit(X_cat)

        # sbert (no fitting, but we record model name)
        if self.use_sbert:
            self._ensure_sbert()
            self.sbert_name_ = self.sbert_model_name
        return self

    def _encode_sbert(self, texts: List[str]) -> np.ndarray:
        if not self.use_sbert:
            # Return zeros if SBERT disabled
            return np.zeros((len(texts), 0), dtype=np.float32)
        self._ensure_sbert()
        emb = self._sbert_model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return np.asarray(emb, dtype=np.float32)

    def transform(self, rows: List[Dict[str, Any]]) -> Tuple[np.ndarray, pd.DataFrame]:
        """Return (X, meta_df)"""
        df = pd.DataFrame(rows)

        # numeric
        X_num = df[list(NUM_KEYS) + list(RES_KEYS)].astype(float).fillna(0.0)
        X_num = self.scaler.transform(X_num) if self.scaler else X_num.values

        # categorical
        X_cat = df[list(CAT_KEYS)].astype(object).fillna("NA")
        X_cat = self.ohe.transform(X_cat) if self.ohe else np.zeros((len(df), 0))

        # text
        X_txt = self._encode_sbert(df["_text"].astype(str).tolist())

        # concat
        X = np.concatenate([X_num, X_cat, X_txt], axis=1)

        # meta (keep keys for later joins/debug)
        meta_cols = ["namespace", "workload_kind", "workload_name", "_spec_hash"]
        meta_df = df[meta_cols].copy()
        meta_df["vec_len"] = X.shape[1]
        return X.astype(np.float32), meta_df

    def save(self, path: str):
        dump({
            "use_sbert": self.use_sbert,
            "sbert_model_name": self.sbert_model_name,
            "sbert_name_": self.sbert_name_,
            "scaler": self.scaler,
            "ohe": self.ohe,
        }, path)

    @classmethod
    def load(cls, path: str) -> "K8sEncoder":
        d = load(path)
        enc = cls(use_sbert=d["use_sbert"], sbert_model_name=d["sbert_model_name"])
        enc.scaler = d["scaler"]
        enc.ohe = d["ohe"]
        enc.sbert_name_ = d.get("sbert_name_")
        return enc


# ---------- CLI ----------
def _read_ndjson(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                ir = json.loads(line)
                rows.append(_flat_row(ir))
            except Exception as e:
                print(f"[WARN] bad line skipped: {e}", file=sys.stderr)
    return rows

def cmd_fit(args):
    rows = _read_ndjson(args.input)
    if not rows:
        raise SystemExit("No rows found in input.")
    enc = K8sEncoder(use_sbert=(not args.no_sbert), sbert_model_name=args.sbert_model)
    enc.fit(rows)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    enc.save(args.out)
    print(f"[OK] saved encoder to {args.out}")

def cmd_transform(args):
    rows = _read_ndjson(args.input)
    enc = K8sEncoder.load(args.encoder)
    X, meta = enc.transform(rows)
    # write Parquet (features as list column)
    df = meta.copy()
    df["features"] = [x.astype(np.float32) for x in X]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"[OK] wrote {len(df)} rows to {args.out}; vector_dim={X.shape[1]}")

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    p_fit = sub.add_parser("fit", help="Fit encoder from NDJSON and save joblib.")
    p_fit.add_argument("--input", required=True, help="NDJSON produced by k8s_collect.py.")
    p_fit.add_argument("--out", required=True, help="Path to save encoder joblib.")
    p_fit.add_argument("--no-sbert", action="store_true", help="Disable SBERT text embeddings.")
    p_fit.add_argument("--sbert-model", default="all-MiniLM-L6-v2")

    p_tr = sub.add_parser("transform", help="Transform NDJSON using a fitted encoder into Parquet.")
    p_tr.add_argument("--input", required=True)
    p_tr.add_argument("--encoder", required=True)
    p_tr.add_argument("--out", required=True)

    args = p.parse_args()
    if args.cmd == "fit": cmd_fit(args)
    else: cmd_transform(args)

if __name__ == "__main__":
    main()
