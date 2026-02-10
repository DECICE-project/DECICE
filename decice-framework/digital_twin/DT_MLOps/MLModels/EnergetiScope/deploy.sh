#!/bin/bash

kubectl apply -f k8s/jobs/ns-pvc.yaml

kubectl apply -f k8s/jobs/rbac.yaml

kubectl apply -f k8s/jobs/job1-collect.yaml
kubectl wait -n energy --for=condition=complete --timeout=1m job/collect-snapshot

kubectl apply -f k8s/jobs/job2-label.yaml
kubectl wait -n energy --for=condition=complete --timeout=30m job/build-labels

kubectl apply -f k8s/jobs/job3-dataset.yaml
kubectl wait -n energy --for=condition=complete --timeout=30m job/join-train-rows

kubectl apply -f k8s/jobs/job4-train.yaml
kubectl wait -n energy --for=condition=complete --timeout=60m job/train-power

kubectl apply -f k8s/deploy-podpower-predict.yaml
kubectl wait -n energy --for=condition=available --timeout=30m deployment/podpower-predict

kubectl apply -f k8s/deploy-podpower-collector.yaml
kubectl wait -n energy --for=condition=available --timeout=30m deployment/podpower-collector





#!/bin/bash

python3 k8s_collect.py watch   --kinds Deployment Job CronJob Pod     --emit-initial   --output ./data/inference_requests.ndjson 
python3 k8s_collect.py watch --emit-initial --output ./data/inference_requests.ndjson
python3 k8s_collect.py from-file ./my-deployment.yaml



python3 k8s_collect.py watch \
  --kinds Deployment Job CronJob Pod \
  --emit-initial \
  --output ./data/inference_requests.ndjson



python3 k8s_collect.py watch \
--kinds Deployment Job CronJob Pod \
--emit-initial \
--suppress-tls-warnings > ./data/inference_requests.ndjson

python3 kepler_labels.py \
  --prom http://prometheus.n1.local \
  --owner-source auto \
  --mode window \
  --start $(date -u -d '5 days ago' +%s) \
  --end   $(date -u +%s) \
  --out ./data/labels.parquet
  --suppress-tls-warnings



python3 join_features_labels.py \
  --features ./data/features.parquet \
  --labels   ./data/labels.parquet \
  --out      ./data/train_rows.parquet