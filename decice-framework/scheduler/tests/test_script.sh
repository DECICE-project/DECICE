#!/bin/bash

SCHEDULER_URL="http://localhost:8030/schedule"
CONTENT_TYPE="Content-Type: application/json"

read -r -d '' JSON_TEMPLATE << EOF
{
  "workloads": [
    {
      "id": "WORKLOAD_ID_PLACEHOLDER",
      "requirements": {
        "required_cpu": 1,
        "required_memory": 512,
        "required_gpu": null
      }
    }
  ],
  "cluster": {
    "lastUpdated": LAST_UPDATED_PLACEHOLDER,
    "vertexpools": [
      {
        "id": "vp-compute-1",
        "vertexpool_labels": {"region": "edge-east"},
        "nodes": [
          {
            "id": "minikube-m02",
            "name": "minikube-m02",
            "system": null,
            "node_info": {},
            "metrics": {
              "util": NODE_1_UTIL,
              "mem_util": NODE_1_MEM_UTIL,
              "network_bandwidth_mbps": NODE_1_NET,
              "free_disk_gb": 200.7,
              "total_disk_gb": 512.0,
              "cpu_cores": 8.0,
              "mem_total": 32768.0,
              "power_watts": NODE_1_POWER
            }
          },
          {
            "id": "minikube-m03",
            "name": "minikube-m03",
            "system": null,
            "node_info": {},
            "metrics": {
              "util": NODE_2_UTIL,
              "mem_util": NODE_2_MEM_UTIL,
              "network_bandwidth_mbps": NODE_2_NET,
              "free_disk_gb": 100.1,
              "total_disk_gb": 256.0,
              "cpu_cores": 4.0,
              "mem_total": 16384.0,
              "power_watts": NODE_2_POWER
            }
          }
        ]
      },
      {
        "id": "vp-compute-2",
        "vertexpool_labels": {"region": "cloud"},
        "nodes": [
          {
            "id": "node-b1",
            "name": "node-b1",
            "system": null,
            "node_info": {},
            "metrics": {
              "util": NODE_3_UTIL,
              "mem_util": NODE_3_MEM_UTIL,
              "network_bandwidth_mbps": NODE_3_NET,
              "free_disk_gb": 4000.5,
              "total_disk_gb": 5000.0,
              "cpu_cores": 32.0,
              "mem_total": 262144.0,
              "power_watts": NODE_3_POWER
            }
          }
        ]
      },
      {
        "id": "vp-device-1",
        "vertexpool_labels": {"region": "device-zone"},
        "nodes": []
      }
    ],
    "links": [
      {"vertexpool_a_id": "vp-compute-1", "vertexpool_b_id": "vp-compute-2", "network_delay_ms": 16.69},
      {"vertexpool_a_id": "vp-compute-2", "vertexpool_b_id": "vp-compute-1", "network_delay_ms": 14.21},
      {"vertexpool_a_id": "vp-compute-1", "vertexpool_b_id": "vp-compute-1", "network_delay_ms": 2.26},
      {"vertexpool_a_id": "vp-compute-2", "vertexpool_b_id": "vp-compute-2", "network_delay_ms": 0.56}
    ]
  }
}
EOF

# Usage: rand_float [max] [precision]
# Example: rand_float 100 2  (gives e.g., 73.41)
rand_float() {
  local max=${1:-100}
  local precision=${2:-2}
  local whole=$(( RANDOM % max ))
  local decimal=$(( RANDOM % 10**precision ))
  # Pad decimal if needed
  printf "%d.%0*d\n" "$whole" "$precision" "$decimal"
}

# Main Loop
echo "🚀 Sending 10 randomized test requests to $SCHEDULER_URL ..."
echo "--------------------------------------------------------"

for i in $(seq 1 10)
do
  echo "Request $i/10..."

  # Generate new metrics
  N1_UTIL=$(rand_float 95 2) # 0-94.xx
  N1_MEM=$(rand_float 90 2)  # 0-89.xx
  N1_NET=$(rand_float 1000 2)
  N1_POW=$(rand_float 100 2)

  N2_UTIL=$(rand_float 95 2)
  N2_MEM=$(rand_float 90 2)
  N2_NET=$(rand_float 200 2)
  N2_POW=$(rand_float 80 2)

  N3_UTIL=$(rand_float 95 2)
  N3_MEM=$(rand_float 90 2)
  N3_NET=$(rand_float 1500 2)
  N3_POW=$(rand_float 150 2)

  # Generate new UUID (requires uuidgen to be installed)
  NEW_UUID=$(uuidgen)
  # Generate new timestamp
  NEW_TIMESTAMP=$(date +%s.%N)

  # Substitute placeholders
  PAYLOAD="$JSON_TEMPLATE"
  PAYLOAD="${PAYLOAD//WORKLOAD_ID_PLACEHOLDER/$NEW_UUID}"
  PAYLOAD="${PAYLOAD//LAST_UPDATED_PLACEHOLDER/$NEW_TIMESTAMP}"
  
  PAYLOAD="${PAYLOAD//NODE_1_UTIL/$N1_UTIL}"
  PAYLOAD="${PAYLOAD//NODE_1_MEM_UTIL/$N1_MEM}"
  PAYLOAD="${PAYLOAD//NODE_1_NET/$N1_NET}"
  PAYLOAD="${PAYLOAD//NODE_1_POWER/$N1_POW}"
  
  PAYLOAD="${PAYLOAD//NODE_2_UTIL/$N2_UTIL}"
  PAYLOAD="${PAYLOAD//NODE_2_MEM_UTIL/$N2_MEM}"
  PAYLOAD="${PAYLOAD//NODE_2_NET/$N2_NET}"
  PAYLOAD="${PAYLOAD//NODE_2_POWER/$N2_POW}"
  
  PAYLOAD="${PAYLOAD//NODE_3_UTIL/$N3_UTIL}"
  PAYLOAD="${PAYLOAD//NODE_3_MEM_UTIL/$N3_MEM}"
  PAYLOAD="${PAYLOAD//NODE_3_NET/$N3_NET}"
  PAYLOAD="${PAYLOAD//NODE_3_POWER/$N3_POW}"
  
  # Send the request
  curl -X POST "$SCHEDULER_URL" \
       -H "$CONTENT_TYPE" \
       -d "$PAYLOAD"
  
  echo
  echo "--------------------------------------------------------"
  sleep 0.5
done

echo "✅ 10 requests sent."