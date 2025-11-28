import numpy as np
import pandas as pd
import pytest

from core.features.aggregate import NumAvailableNodes
from core.features.factory import (create_data_transformer,
                                   create_feature_engineer)
from core.schemas import ScheduleRequest


def test_data_transformer_integration(sample_schedule_request: ScheduleRequest):
    """
    Tests that the DataTransformer is correctly initialized by its factory,
    finds all extractor plugins, and successfully transforms a ScheduleRequest.
    """
    # create_scheduler_transformer() runs discovery and
    #   initializes the transformer with all discovered features.
    transformer = create_data_transformer()

    # Run the transformation
    # --- [FIX] workloads_df -> tasks_df ---
    tasks_df, nodes_df, latency_matrix = transformer.transform(sample_schedule_request)

    # Assert Tasks DataFrame
    assert isinstance(tasks_df, pd.DataFrame)
    # Based on sample_schedule_request, we have 2 tasks
    assert tasks_df.shape == (2, 4)
    expected_task_cols = [
        "gpu_is_required",
        "required_cpu",
        "required_memory",
        "task_id",  # --- [FIX] workload_id -> task_id
    ]
    # Check if all expected columns are present
    assert all(col in tasks_df.columns for col in expected_task_cols)
    assert tasks_df["required_cpu"].iloc[0] == 2
    assert tasks_df["gpu_is_required"].iloc[1] == 1  # Second job required a GPU

    # Assert Nodes DataFrame
    assert isinstance(nodes_df, pd.DataFrame)
    # sample_cluster_state has 3 nodes total (2 in pool-a, 1 in pool-b)
    assert nodes_df.shape == (3, 13)
    expected_node_cols = [
        "metrics_available_cpu_cores",
        "metrics_available_mem_mb",
        "metrics_cpu_cores",
        "metrics_cpu_util",
        "metrics_free_disk_mb",
        "metrics_mem_total_mb",
        "metrics_mem_util",
        "metrics_network_bandwidth_mbps",
        "metrics_power_watts",
        "metrics_total_disk_mb",
        "metrics_used_disk_mb",
        "node_id",
        "vertexpool_id",
    ]
    assert all(col in nodes_df.columns for col in expected_node_cols)
    # Check a calculated value on the first node (low util)
    # total=16, util=10.5% => 16 * (1 - 0.105) = 14.32
    assert pd.api.types.is_float_dtype(nodes_df["metrics_available_cpu_cores"])
    assert np.isclose(nodes_df["metrics_available_cpu_cores"].iloc[0], 14.32)
    # Check a conversion (64GB -> MB)
    assert np.isclose(nodes_df["metrics_mem_total_mb"].iloc[0], 64.0 * 1024)

    # Assert Latency Matrix
    assert isinstance(latency_matrix, dict)
    assert "pool-a" in latency_matrix
    assert "pool-b" in latency_matrix["pool-a"]
    assert latency_matrix["pool-a"]["pool-b"] == 5.2


def test_feature_engineer_integration(sample_schedule_request: ScheduleRequest):
    """
    Tests that the FeatureEngineer and DataTransformer work together.
    It builds the final, scaled feature vector from the raw request.

    NOTE: This test requires a valid (or dummy) scaler file to be present
    at the path specified in your config (settings.ALL_SCALERS_FILE_PATH).
    """
    # Create the real components using factories
    transformer = create_data_transformer()
    # This will try to load scalers from the path in your config
    try:
        engineer = create_feature_engineer()
    except Exception as e:
        pytest.skip(
            f"Skipping FeatureEngineer test: Failed to load scalers/config. Error: {e}"
        )

    # Run the full data pipeline
    tasks_df, nodes_df, latency_matrix = transformer.transform(sample_schedule_request)
    feature_vector = engineer.build_features(tasks_df, nodes_df, latency_matrix)

    # Assert final vector
    assert isinstance(feature_vector, np.ndarray)
    # Based on our discovery logs, we expect 19 aggregate features
    assert feature_vector.shape == (19,)
    assert feature_vector.dtype == np.float32

    # Check that the values are not just raw aggregates (i.e., scaling was applied)
    # We find the raw 'num_available_nodes' (3) and check it's not 3.0 in the scaled vector
    # (This assumes the scaler is not a no-op)
    raw_nodes = NumAvailableNodes().calculate(tasks_df, nodes_df, latency_matrix)
    assert raw_nodes == 3.0

    # Find the index of this feature in the sorted list
    feature_index = engineer.feature_names.index("num_available_nodes")
    scaled_value = feature_vector[feature_index]

    # If scalers are working, the scaled value should be different from the raw value
    # (unless the scaler was coincidentally fit to output 3.0)
    # This is a basic check that *some* transformation happened.
    if "num_available_nodes" in engineer.scalers:
        assert scaled_value != 3.0
    else:
        # If scalers weren't loaded, the value should be the raw value
        assert scaled_value == 3.0
