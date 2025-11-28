import requests
import json
from datetime import datetime, timezone
import time

BASE_URL = "http://localhost:8010"

# InluxDB Needs to be running and "my_bucket" bucket needs to be created.


def write_data():
    url = f"{BASE_URL}/api/timeseries/write_record/"
    headers = {"Content-Type": "application/json"}
    bucket = "my_bucket"

    points = []
    for i in range(5):
        point = {
            "measurement": "environment",
            "timetamp": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "tags": {"location": "office"},
            "fields": {
                "temperature": 22.5 + i,  # varying temperature
                "humidity": 60 + i,  # varying humidity
            },
        }
        points.append(point)

    response = requests.post(url, headers=headers, params={"bucket": bucket}, data=json.dumps(points))
    if response.status_code == 201:
        print("Data write successful!")
    else:
        print(f"Failed to write data: {response.status_code}, {response.text}")


def read_data():
    url = f"{BASE_URL}/api/timeseries/read_record/"
    headers = {"Content-Type": "application/json"}

    body = {
        "measurement": "environment",
        "bucket": "my_bucket",
        "time_range": {"start": "-1d"},
        # Optional tag filtering can be added, e.g.
        # "tags": {"location": "office"}
    }

    response = requests.post(url, headers=headers, data=json.dumps(body))
    if response.status_code == 200:
        data = response.json()
        print("Data retrieved successfully!")
        print(json.dumps(data, indent=4))
    else:
        print(f"Failed to retrieve data: {response.status_code}, {response.text}")


write_data()
time.sleep(1)  # optional pause to ensure data is available before reading
read_data()
