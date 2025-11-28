#!/bin/bash

while true; do
  curl -X 'GET' \
    'http://127.0.0.1:8050/pool?post_to_digital_twin=true' \
    -H 'accept: application/json'
  echo "Waiting 30 seconds..."
  sleep 30
done
