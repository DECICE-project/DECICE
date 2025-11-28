import pandas as pd
import time
from datetime import datetime, timedelta
from importlib import reload
import numpy as np
from prometheus_api_client import PrometheusConnect
from prometheus_client import start_http_server, Gauge
import lstm_autoencoder as lstm
import TCN as TCN
import CNN as CNN
import zscore_calculator as ZC
import IsolationForest as IF
import OneClassSVM as SVM
import arima as reg
import data_reader as dr
import argparse
from fastapi import FastAPI
import uvicorn
from typing import Dict
from pytz import timezone
import threading
# Reload necessary modules
reload(dr)
reload(TCN)
reload(CNN)
reload(reg)
reload(SVM)
reload(ZC)
reload(lstm)
reload(IF)
from data_reader import get_combined_usage_data
from zscore_calculator import calculate_zscores
from lstm_autoencoder import train_lstm_detect_anomalies,evaluate_lstm_detect_anomalies 
from IsolationForest import detect_anomalies_isolation_forest 
from TCN import train_tcn,test_tcn
from CNN import CNN_Anomaly_detect,train_cnn_model
from OneClassSVM import  detect_anomalies_one_class_svm
from arima import detect_anomalies_arima
import pandas as pd
from prometheus_api_client import PrometheusConnect
import logging
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from fastapi import FastAPI
from typing import Dict

anomaly_data={}

def get_combined_usage_data(url="http://141.5.107.135:30090/", start_time_str=None, end_time_str=None,
                             cpu_query=None, mem_query=None, io_query=None):
    # Create a connection to the Prometheus server
    prom = PrometheusConnect(url=url, disable_ssl=True)
    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")

    def fetch_data(query, metric_name):
        while True:
            try:
                usage_data = prom.custom_query_range(query=query, start_time=start_time, end_time=end_time, step='5s')
                df = pd.DataFrame(usage_data)
                
                if df.empty:
                    return pd.DataFrame()

                data = [{'Timestamp': ts, metric_name: usage} for sublist in df['values'] for ts, usage in sublist]
                df = pd.DataFrame(data)
                df['datetime'] = pd.to_datetime(df['Timestamp'], unit='s')
                df.set_index('datetime', inplace=True)
                df.drop(columns=['Timestamp'], inplace=True)
                df[metric_name] = df[metric_name].astype(float)
                return df[~df.index.duplicated(keep='first')]
            
            except Exception as e:
                print(f"Error occurred for query {query}: {e}. Retrying in 10 seconds...")
                time.sleep(10)

    try:
        cpu_df = fetch_data(cpu_query, 'CPU Usage')
        mem_df = fetch_data(mem_query, 'Memory Usage')
        io_df = fetch_data(io_query, 'IO Usage')

        combined_df = pd.concat([cpu_df, mem_df, io_df], axis=1).interpolate('linear')
        return combined_df
    
    except Exception as e:
        print(f"Error while combining data: {e}. Retrying in 10 seconds...")
        time.sleep(10)
        return get_combined_usage_data(url, start_time_str, end_time_str, cpu_query, mem_query, io_query)

def is_anomaly_rate_below_threshold(anomaly_list, threshold=0.2):
        if anomaly_list.empty:
            anomaly_rate = 0
        else:
            # Calculate the anomaly rate
            num_anomalies = anomaly_list.sum()  # This will sum up the values if it's a Series
            anomaly_rate = num_anomalies / len(anomaly_list)

        # Return True if the anomaly rate is below the threshold, else False
        return anomaly_rate > threshold
def main_loop_pod(prometheus_url, name, minute,log_dir):
    global anomaly_data
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=minute)

    # Prometheus queries
    query_cpu = f'sum(rate(container_cpu_usage_seconds_total{{pod="{name}"}}[2m])) by (pod)'
    query_mem = f'sum(rate(container_memory_usage_bytes{{pod="{name}"}}[2m])) by (pod)'
    query_io = 'node_disk_io_now'

    while True:
        try:
            start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

            # Fetch data
            df = get_combined_usage_data(prometheus_url, start_time_str, end_time_str, query_cpu, query_mem, query_io)
            temp = df[['CPU Usage', 'Memory Usage', 'IO Usage']].copy()

            anomaly_data = {
                "Timestamp": datetime.now().astimezone(datetime.now().tzinfo),
                "TCN": bool(is_anomaly_rate_below_threshold(test_tcn(temp, ['CPU Usage', 'Memory Usage', 'IO Usage']))),
                "LSTM": bool(is_anomaly_rate_below_threshold(evaluate_lstm_detect_anomalies(temp, ['CPU Usage', 'Memory Usage', 'IO Usage'],log_dir))),
                "CNN": bool(is_anomaly_rate_below_threshold(CNN_Anomaly_detect(temp, ['CPU Usage', 'Memory Usage', 'IO Usage']))),
                "Z-Score": bool(is_anomaly_rate_below_threshold(calculate_zscores(temp, ['CPU Usage', 'Memory Usage', 'IO Usage']))),
                "ARIMA": bool(is_anomaly_rate_below_threshold(detect_anomalies_arima(temp, ['CPU Usage', 'Memory Usage', 'IO Usage']))),
                "Isolation Forest": bool(is_anomaly_rate_below_threshold(detect_anomalies_isolation_forest(temp, ['CPU Usage', 'Memory Usage', 'IO Usage']))),
                "One-Class SVM": bool(is_anomaly_rate_below_threshold(detect_anomalies_one_class_svm(temp, ['CPU Usage', 'Memory Usage', 'IO Usage'])))
            }

            print(anomaly_data)
            start_time = end_time
            end_time = start_time + timedelta(minutes=10)

        except Exception as e:
            print(f"Error occurred in the main loop: {e}")
            time.sleep(60)  

        time.sleep(600)  


def main_loop_node(prometheus_url, name, minute,log_dir):
    global anomaly_data
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=minute)

    # Prometheus queries
    query_cpu = f'sum(rate(container_cpu_usage_seconds_total{{node="{name}"}}[2m]))'
    query_mem = f'sum(rate(container_memory_usage_bytes{{node="{name}"}}[2m])) by (pod)'
    query_io = 'node_disk_io_now'
    

    while True:
        try:
            from tensorboardX import SummaryWriter
            import os
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                print('here the directory is created.')
            writer = SummaryWriter(log_dir)
            start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

            # Fetch data
            df = get_combined_usage_data(prometheus_url, start_time_str, end_time_str, query_cpu, query_mem, query_io)
            temp = df[['CPU Usage', 'Memory Usage', 'IO Usage']].copy()

            anomaly_data = {
                "type": 'node',
                "node name": name,
                "Timestamp": datetime.now().astimezone(datetime.now().tzinfo),
                "TCN": bool(is_anomaly_rate_below_threshold(test_tcn(temp, ['CPU Usage', 'Memory Usage', 'IO Usage']))),
                "LSTM": bool(is_anomaly_rate_below_threshold(evaluate_lstm_detect_anomalies(temp, ['CPU Usage', 'Memory Usage', 'IO Usage'],log_dir))),
                "CNN": bool(is_anomaly_rate_below_threshold(CNN_Anomaly_detect(temp, ['CPU Usage', 'Memory Usage', 'IO Usage']))),
                "Z-Score": bool(is_anomaly_rate_below_threshold(calculate_zscores(temp, ['CPU Usage', 'Memory Usage', 'IO Usage']))),
                "ARIMA": bool(is_anomaly_rate_below_threshold(detect_anomalies_arima(temp, ['CPU Usage', 'Memory Usage', 'IO Usage']))),
                "Isolation Forest": bool(is_anomaly_rate_below_threshold(detect_anomalies_isolation_forest(temp, ['CPU Usage', 'Memory Usage', 'IO Usage']))),
                "One-Class SVM": bool(is_anomaly_rate_below_threshold(detect_anomalies_one_class_svm(temp, ['CPU Usage', 'Memory Usage', 'IO Usage'])))
            }
            # writer.add_scalar(anomaly_data)
            for key, value in anomaly_data.items():
                writer.add_scalar(key, value)
            writer.close()
            print(anomaly_data)
            start_time = end_time
            end_time = start_time + timedelta(minutes=10)

        except Exception as e:
            print(f"Error occurred in the main loop: {e}")
            time.sleep(60) 

        time.sleep(600)  



# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


# Function to start background anomaly detection tasks
def start_background_task(prometheus_url, type, name, polling_interval,log_dir):
    logger.info(f"Starting background task for {type} with name {name} and interval {polling_interval}")
    if type == 'pod':
        thread = threading.Thread(target=main_loop_pod, args=(prometheus_url, name, polling_interval,log_dir))
        thread.daemon = True
        thread.start()
    elif type == 'node':
        thread = threading.Thread(target=main_loop_node, args=(prometheus_url, name, polling_interval,log_dir))
        thread.daemon = True
        thread.start()
    else:
        logger.warning('Choose one of the types: node or pod.')

# FastAPI endpoint to fetch anomaly data for a specific node or pod
@app.get("/anomaly/{type}/{name}", response_model=Dict)
def get_anomaly_data(type: str, name: str):
    """Endpoint to fetch the latest anomaly data for a pod or node."""
    return anomaly_data


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Anomaly Detection Pipeline')
    parser.add_argument('--prometheus-url', type=str, required=True, help='Prometheus server URL')
    parser.add_argument('--polling-interval', type=int, default=10, help='Polling interval in minutes')
    parser.add_argument('--type', type=str, required=True, help='Type of component: pod or node')
    parser.add_argument('--name', type=str, required=True, help='Name of the pod or node to monitor')
    parser.add_argument('--log-dir', type=str, required=True,help='Directory to save TensorBoard logs')
    args = parser.parse_args()
    log_dir = args.log_dir
    print('here we have the logdir and i wnat to see it',log_dir)
    # Start the background task for the specified pod or node
    start_background_task(args.prometheus_url, args.type, args.name, args.polling_interval,args.log_dir)
    uvicorn.run(app, host="0.0.0.0", port=8000)