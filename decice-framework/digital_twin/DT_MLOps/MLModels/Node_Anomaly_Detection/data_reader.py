from prometheus_api_client import PrometheusConnect
import logging
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

# Set up logging to see warnings and errors
logging.basicConfig(level=logging.DEBUG)


def get_combined_usage_data(
    url="http://192.168.56.10:30090",
    start_time_str=None,
    end_time_str=None,
    cpu_query='sum(rate(container_cpu_usage_seconds_total{pod="vida-test"}[5m])) by (pod)',
    mem_query='sum(rate(container_memory_usage_bytes{pod="vida-test"}[5m])) by (pod)',
    io_query="node_disk_io_now",
    query_recieved_packets=None,
    query_transmit_packets=None,
):
    # Create a connection to the Prometheus server
    prom = PrometheusConnect(url=url, disable_ssl=True)

    # Convert string times to datetime objects
    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")

    def fetch_data(query, metric_name):
        try:
            usage_data = prom.custom_query_range(query=query, start_time=start_time, end_time=end_time, step="5s")
        except Exception as e:
            print(f"Error occurred for query {query}: {e}")
            return None

        # Convert the data to a Pandas DataFrame
        df = pd.DataFrame(usage_data)
        if df.empty:
            return pd.DataFrame()  # Return an empty DataFrame if no data

        l = df["values"]
        data = []

        # Flatten the list of tuples
        for sublist in l:
            for timestamp, usage in sublist:
                data.append({"Timestamp": timestamp, metric_name: usage})

        # Create a DataFrame from the collected data
        df = pd.DataFrame(data)

        # Convert Unix timestamp to datetime
        df["datetime"] = pd.to_datetime(df["Timestamp"], unit="s")
        df.set_index("datetime", inplace=True)
        df.drop(columns=["Timestamp"], inplace=True)
        df[metric_name] = df[metric_name].astype(float)

        # Drop duplicate indices
        df = df[~df.index.duplicated(keep="first")]

        return df

    # Fetch data for all queries
    cpu_df = fetch_data(cpu_query, "CPU Usage")
    mem_df = fetch_data(mem_query, "Memory Usage")
    io_df = fetch_data(io_query, "IO Usage")
    recPack_df = fetch_data(query_recieved_packets, "recPack")
    transPack_df = fetch_data(query_transmit_packets, "transPack")

    # Combine the dataframes along the columns
    combined_df = pd.concat([cpu_df, mem_df, io_df, recPack_df, transPack_df], axis=1)

    # Handle missing data
    combined_df = combined_df.interpolate("linear")  # Interpolate missing values

    return combined_df
