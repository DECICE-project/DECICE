#!/usr/bin/env python3
import argparse, joblib, json, numpy as np, pandas as pd

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--encoder", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--input", required=True, help="NDJSON from k8s_collect (one or many lines)")
    args = p.parse_args()

    # reuse the encoder CLI to transform
    import subprocess, tempfile, os
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".parquet")
    tmp.close()
    cmd = ["python", "k8s_encode.py", "transform",
           "--input", args.input, "--encoder", args.encoder, "--out", tmp.name]
    subprocess.check_call(cmd)

    df = pd.read_parquet(tmp.name)
    X = np.stack(df["features"].to_numpy())

    model = joblib.load(args.model)
    preds = model.predict(X).tolist()

    out = []
    for meta, y in zip(df[["namespace","workload_kind","workload_name","_spec_hash"]].to_dict(orient="records"), preds):
        meta["pred_avg_power_w"] = float(y)
        out.append(meta)

    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()



=? numpy array 393 features