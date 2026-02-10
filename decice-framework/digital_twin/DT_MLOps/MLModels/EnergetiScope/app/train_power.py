#!/usr/bin/env python3
import argparse, joblib, numpy as np, pandas as pd
from sklearn.neighbors import KNeighborsRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_absolute_error, r2_score

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--train", required=True)  # ./data/train_rows.parquet
    p.add_argument("--target", choices=["avg_power_w","energy_step_j","total_energy_j"], default="avg_power_w")
    p.add_argument("--out", required=True)   # model path
    p.add_argument("--neighbors", type=int, default=5)
    args = p.parse_args()

    df = pd.read_parquet(args.train)
    # features is an array column
    X = np.stack(df["features"].to_numpy())
    y = df[args.target].astype(float).to_numpy()
    # filter invalid targets
    keep = np.isfinite(y)
    X, y, df = X[keep], y[keep], df.loc[keep]
    if len(y) == 0:
        raise SystemExit(f"No finite values for target '{args.target}'. "
                         f"Try --target energy_step_j or fix labels.")

    # group by workload to avoid leakage
    groups = df["workload_name"].astype(str).to_numpy()
    n_groups = max(1, df["workload_name"].nunique())
    n_splits = min(5, n_groups)
    if n_splits < 2:
        raise SystemExit("Need at least 2 distinct workloads for CV. Collect more data.")
    gkf = GroupKFold(n_splits=n_splits)

    maes, r2s = [], []
    for tr, va in gkf.split(X, y, groups):
        model = KNeighborsRegressor(n_neighbors=args.neighbors, metric="cosine")
        model.fit(X[tr], y[tr])
        pva = model.predict(X[va])
        maes.append(mean_absolute_error(y[va], pva))
        r2s.append(r2_score(y[va], pva))

    print(f"CV MAE: {np.mean(maes):.3f} ± {np.std(maes):.3f} | R2: {np.mean(r2s):.3f}")

    # train on all
    model = KNeighborsRegressor(n_neighbors=args.neighbors, metric="cosine")
    model.fit(X, y)
    joblib.dump(model, args.out)
    print(f"[OK] saved model to {args.out}")

if __name__ == "__main__":
    main()
