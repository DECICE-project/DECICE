#!/bin/bash

# Define the directory for InfluxDB data in the current path
DATA_DIR="./influxdb_data"
INFLUXDB_ORG="decice"
INFLUXDB_BUCKET="cluster_snapshot"
INFLUXDB_URL="http://localhost:8086"

# Check if the directory exists
if [ ! -d "$DATA_DIR" ]; then
  echo "Directory $DATA_DIR does not exist. Creating it..."
  mkdir -p "$DATA_DIR"
  FIRST_TIME_SETUP=true
else
  FIRST_TIME_SETUP=false
fi

# Run the InfluxDB container if it's not already running
if [ ! "$(docker ps -q -f name=influxdb)" ]; then
  echo "InfluxDB container not running. Starting container..."
  docker run -d \
    --name=influxdb \
    --restart unless-stopped \
    -p 8086:8086 \
    -v "$(pwd)/influxdb_data:/var/lib/influxdb2" \
    influxdb:latest
else
  echo "InfluxDB container is already running."
fi

# Perform first-time setup only if directory does not exist or container is not set up
if [ "$FIRST_TIME_SETUP" = true ]; then
  echo "First-time setup: Enter username and password for InfluxDB..."

  # Prompt for username and password for InfluxDB setup
  read -p "Enter InfluxDB username: " USERNAME
  read -sp "Enter InfluxDB password: " PASSWORD
  echo

  # Setup InfluxDB with provided username, password, organization, and bucket
  docker exec influxdb influx setup \
    --username "$USERNAME" \
    --password "$PASSWORD" \
    --org "$INFLUXDB_ORG" \
    --bucket "$INFLUXDB_BUCKET" \
    --force

  # Retrieve the InfluxDB token
  INFLUXDB_TOKEN=$(docker exec influxdb bash -c "influx auth ls --json" | jq -r '.[0].token')
  
  # Remove existing .env file if it exists
  rm -f .env
  # Create a new empty .env file
  touch .env
  # Write to .env file with token, URL, bucket, and org information
  echo "INFLUXDB_TOKEN=$INFLUXDB_TOKEN" >> .env
  echo "INFLUXDB_URL=$INFLUXDB_URL" >> .env
  echo "INFLUXDB_BUCKET=$INFLUXDB_BUCKET" >> .env
  echo "INFLUXDB_ORG=$INFLUXDB_ORG" >> .env

  echo "InfluxDB setup complete. .env file written."
else
  echo "Skipping setup as the directory already exists."
fi

echo "InfluxDB container is now running with data persisted to $DATA_DIR."
