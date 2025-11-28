#!/bin/sh
set -e

if [ -z "$MINIO_SERVER_URL" ] || [ -z "$MINIO_ACCESS_KEY" ] || [ -z "$MINIO_SECRET_KEY" ]; then
  echo "Error: MINIO_SERVER_URL, MINIO_ACCESS_KEY, and MINIO_SECRET_KEY must be set."
  exit 1
fi

echo "Waiting for MinIO server at $MINIO_SERVER_URL..."
until mc alias set myminio "$MINIO_SERVER_URL" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"; do
    echo "MinIO not ready, sleeping for 2 seconds..."
    sleep 2
done
echo "MinIO is ready."

echo "Creating bucket 'workflows'..."
mc mb myminio/workflows --ignore-existing

echo "Clearing all existing webhook events on 'workflows' bucket..."
mc event remove myminio/workflows --force || true

echo "Adding webhook event for 'workflows' bucket..."
mc event add myminio/workflows arn:minio:sqs::psgc:webhook --event put

echo "MinIO configuration complete."
