# predict_service.py
import os, uvicorn, numpy as np, pandas as pd
from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel, ValidationError
import io, yaml
from joblib import load
from typing import Dict, Any, List

from k8s_encode import K8sEncoder, _flat_row    # reuse your encoder utils
from models import InferenceRequest             # your schema
from k8s_collect import podtemplate_to_request

# path ="/opt/local-path-provisioner/pvc-dde8a16d-5550-41b8-ac85-e75d5e49b7fc_energy_podpower-data"

# ENC_PATH = os.getenv("ENCODER_PATH", path+"/encoder.joblib")
# MOD_PATH = os.getenv("MODEL_PATH",   path+"/knn_energy.joblib")

ENC_PATH = os.getenv("ENCODER_PATH", "/artifacts/encoder.joblib")
MOD_PATH = os.getenv("MODEL_PATH",   "/artifacts/knn_energy.joblib")



app = FastAPI()
enc = K8sEncoder.load(ENC_PATH)
model = load(MOD_PATH)

class PredictOut(BaseModel):
    pred_energy_step_j: float
    workload_kind: str
    workload_name: str
    namespace: str
    spec_hash: str

@app.post("/predict", response_model=PredictOut)
def predict(ir: InferenceRequest):
    row = _flat_row(ir.model_dump())
    X, meta = enc.transform([row])
    y = float(model.predict(X)[0])
    m = meta.iloc[0].to_dict()
    return PredictOut(
        pred_energy_step_j=y,
        workload_kind=m["workload_kind"],
        workload_name=m["workload_name"],
        namespace=m["namespace"],
        spec_hash=m["_spec_hash"],
    )


# --- YAML → InferenceRequest helpers & endpoints ---
def _build_ir_from_obj(obj: dict) -> InferenceRequest:
    kind = (obj.get("kind") or "").strip()
    meta = obj.get("metadata") or {}
    spec = obj.get("spec") or {}
    ns = meta.get("namespace", "default")
    name = meta.get("name", "noname")
    try:
        if kind == "Deployment":
            tmpl = spec["template"]
            return podtemplate_to_request(ns, "Deployment", name, tmpl)
        elif kind == "Job":
            tmpl = spec["template"]
            return podtemplate_to_request(ns, "Job", name, tmpl, parent_spec=spec)
        elif kind == "CronJob":
            jt = spec["jobTemplate"]["spec"]["template"]
            return podtemplate_to_request(ns, "CronJob", name, jt)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported kind: {kind}. Use Deployment/Job/CronJob.")
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing field: {e}")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Pydantic validation error: {e}")


@app.post("/infer/from-yaml", tags=["Inference"], summary="Convert YAML → InferenceRequest JSON")
def infer_from_yaml(yaml_text: str = Body(..., media_type="text/plain")):
    """
    Paste your Deployment/Job/CronJob YAML manifest here. Returns InferenceRequest JSON(s).
    """
    try:
        docs = list(yaml.safe_load_all(io.StringIO(yaml_text)))
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    irs = []
    for d in docs:
        if not isinstance(d, dict):
            continue
        ir = _build_ir_from_obj(d)
        irs.append(ir.model_dump())
    return irs


@app.post("/predict/from-yaml", tags=["Prediction"], summary="Predict directly from YAML manifest", response_model=PredictOut)
def predict_from_yaml(yaml_text: str = Body(..., media_type="text/plain")):
    try:
        docs = list(yaml.safe_load_all(io.StringIO(yaml_text)))
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
    if not docs:
        raise HTTPException(status_code=400, detail="No valid YAML docs found.")
    first_doc = next((d for d in docs if isinstance(d, dict)), None)
    if first_doc is None:
        raise HTTPException(status_code=400, detail="No object manifests found in YAML.")
    ir = _build_ir_from_obj(first_doc)
    row = _flat_row(ir.model_dump())
    X, meta = enc.transform([row])
    y = float(model.predict(X)[0])
    m = meta.iloc[0].to_dict()
    return PredictOut(
        pred_energy_step_j=y,
        workload_kind=m["workload_kind"],
        workload_name=m["workload_name"],
        namespace=m["namespace"],
        spec_hash=m["_spec_hash"],
    )
if __name__ == "__main__":
    uvicorn.run("predict_service:app", host="0.0.0.0", port=8000)