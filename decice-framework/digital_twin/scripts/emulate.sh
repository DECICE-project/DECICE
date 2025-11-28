#!/bin/bash

# Default values
DEFAULT_YAML="emulate.yaml"
DEFAULT_DT_URL="http://127.0.0.1:8010"
DEFAULT_FREQ=30

yaml_path=""
dt_url="$DEFAULT_DT_URL"
freq="$DEFAULT_FREQ"

usage() {
  echo "Usage: $0 <yaml_path> [--dt_url URL] [--freq SECONDS]"
  echo "  <yaml_path>: Path to emulation YAML file (default: $DEFAULT_YAML)"
  echo "  --dt_url URL: Digital Twin URL (default: $DEFAULT_DT_URL)"
  echo "  --freq SECONDS: Update frequency in seconds (default: $DEFAULT_FREQ)"
}

# Parse args manually
# First positional arg is yaml_path
if [[ $# -eq 0 ]]; then
  echo "Warning: No YAML path provided. Using default: $DEFAULT_YAML"
  yaml_path="$DEFAULT_YAML"
else
  yaml_path="$1"
  shift
fi

# Parse optional args --dt_url and --freq
while [[ $# -gt 0 ]]; do
  case $1 in
    --dt_url)
      dt_url="$2"
      shift 2
      ;;
    --freq)
      freq="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

echo "Using YAML path: $yaml_path"
echo "Using Digital Twin URL: $dt_url"
echo "Using update frequency: $freq seconds"

# Run the python script with args
python src/digital_twin/emulator/emulate.py "$yaml_path" --dt_url "$dt_url" --freq "$freq"