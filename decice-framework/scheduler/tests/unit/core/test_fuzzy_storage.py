import numpy as np
import pytest

from core.fuzzy_storage import FuzzyStorageResourcesAccessGate


@pytest.fixture
def fuzzy_gate_default() -> FuzzyStorageResourcesAccessGate:
    """Default Fuzzy Gate instance."""
    # Weights: CPU=0.35, Mem=0.35, Storage=0.20, Net=0.0 -> Sum=0.9 (Gap acceptable for tests)
    return FuzzyStorageResourcesAccessGate(
        cpu_weight=0.35, memory_weight=0.35, storage_weight=0.20, network_weight=0.0
    )


@pytest.fixture
def sample_job_dict_small() -> dict:
    """Small job, should fit easily."""
    return {"task_id": "job-small", "required_cpu": 1, "required_memory": 1024}


@pytest.fixture
def sample_job_dict_large_cpu() -> dict:
    """Large CPU job."""
    return {"task_id": "job-large-cpu", "required_cpu": 10, "required_memory": 8192}


@pytest.fixture
def sample_job_dict_large_mem() -> dict:
    """Large Mem job."""
    return {
        "task_id": "job-large-mem",
        "required_cpu": 2,
        "required_memory": 40 * 1024,
    }


@pytest.fixture
def sample_node_dict_low_util() -> dict:
    """Node dict with low utilization."""
    total_cpu = 16.0
    total_mem_gb = 64.0
    total_mem_mb = total_mem_gb * 1024
    total_disk_gb = 1000.0
    free_disk_gb = 800.0

    cpu_util_perc = 10.0
    mem_util_perc = 20.0

    return {
        "node_id": "node-low",
        "metrics_cpu_cores": total_cpu,
        "metrics_mem_total_mb": total_mem_mb,
        "metrics_available_cpu_cores": total_cpu * (1 - cpu_util_perc / 100.0),
        "metrics_available_mem_mb": total_mem_mb * (1 - mem_util_perc / 100.0),
        "metrics_cpu_util": cpu_util_perc,
        "metrics_mem_util": mem_util_perc,
        "metrics_free_disk_mb": free_disk_gb * 1024,
        "metrics_total_disk_mb": total_disk_gb * 1024,
        "metrics_used_disk_mb": (total_disk_gb - free_disk_gb) * 1024,
        "metrics_network_bandwidth_mbps": 1000.0,
    }


@pytest.fixture
def sample_node_dict_high_util() -> dict:
    """Node dict with high utilization."""
    total_cpu = 16.0
    total_mem_gb = 64.0
    total_mem_mb = total_mem_gb * 1024
    total_disk_gb = 1000.0
    free_disk_gb = 100.0

    cpu_util_perc = 95.0
    mem_util_perc = 90.0

    return {
        "node_id": "node-high",
        "metrics_cpu_cores": total_cpu,
        "metrics_mem_total_mb": total_mem_mb,
        "metrics_available_cpu_cores": total_cpu * (1 - cpu_util_perc / 100.0),
        "metrics_available_mem_mb": total_mem_mb * (1 - mem_util_perc / 100.0),
        "metrics_cpu_util": cpu_util_perc,
        "metrics_mem_util": mem_util_perc,
        "metrics_free_disk_mb": free_disk_gb * 1024,
        "metrics_total_disk_mb": total_disk_gb * 1024,
        "metrics_used_disk_mb": (total_disk_gb - free_disk_gb) * 1024,
        "metrics_network_bandwidth_mbps": 1000.0,
    }


def test_component_score_no_req(fuzzy_gate_default):
    score = fuzzy_gate_default._calculate_component_score("CPU", 0, 10, 0.5)
    assert score == 1.0


def test_component_score_no_fit(fuzzy_gate_default):
    score = fuzzy_gate_default._calculate_component_score("CPU", 12, 10, 0.5)
    assert score == 0.0


def test_component_score_good_fit_idle(fuzzy_gate_default):
    score = fuzzy_gate_default._calculate_component_score("CPU", 1, 10, 0.0)
    assert np.isclose(score, 0.9)


def test_component_score_good_fit_busy(fuzzy_gate_default):
    score = fuzzy_gate_default._calculate_component_score("CPU", 1, 10, 0.8)
    assert np.isclose(score, 0.18)


def test_component_score_util_clamp(fuzzy_gate_default):
    score_over = fuzzy_gate_default._calculate_component_score("CPU", 1, 10, 1.1)
    assert np.isclose(score_over, 0.0)
    score_under = fuzzy_gate_default._calculate_component_score("CPU", 1, 10, -0.1)
    assert np.isclose(score_under, 0.9)


def test_suitability_small_job_low_util(
    fuzzy_gate_default, sample_job_dict_small, sample_node_dict_low_util
):
    score = fuzzy_gate_default.calculate_node_suitability_for_task(
        sample_job_dict_small, sample_node_dict_low_util
    )
    # CPU: req=1, avail=14.4, util=0.1 => health=0.9, fit=1-(1/14.4)=0.9305... => score=0.8375
    # Mem: req=1024, avail=52428.8, util=0.2 => health=0.8, fit=1-(1024/52428.8)=0.9804... => score=0.784375
    # Sto: req=0 => score=1.0
    # Net: avail=1000, max=10000 => score=0.1
    # Final = (0.8375 * 0.35) + (0.784375 * 0.35) + (1.0 * 0.20) + (0.1 * 0.0)
    # Final = 0.293125 + 0.27453125 + 0.2 + 0.0 = 0.76765625
    assert score > fuzzy_gate_default.suitability_threshold
    assert np.isclose(score, 0.7676, atol=0.001)


def test_suitability_small_job_high_util(
    fuzzy_gate_default, sample_job_dict_small, sample_node_dict_high_util
):
    score = fuzzy_gate_default.calculate_node_suitability_for_task(
        sample_job_dict_small, sample_node_dict_high_util
    )
    # CPU: req=1, avail=0.8 => Does not fit! Score=0.0
    # Mem: req=1024, avail=6553.6, util=0.9 => health=0.1, fit=1-(1024/6553.6)=0.84375 => score=0.084375
    # Sto: req=0 => score=1.0
    # Net: avail=1000 => score=0.1
    # Final = (0.0 * 0.35) + (0.084375 * 0.35) + (1.0 * 0.20) + (0.1 * 0.0)
    # Final = 0.0 + 0.02953125 + 0.2 = 0.22953125
    assert score < fuzzy_gate_default.suitability_threshold  # Should be unsuitable
    assert np.isclose(score, 0.2295, atol=0.001)


def test_suitability_large_cpu_job_low_util(
    fuzzy_gate_default, sample_job_dict_large_cpu, sample_node_dict_low_util
):
    score = fuzzy_gate_default.calculate_node_suitability_for_task(
        sample_job_dict_large_cpu, sample_node_dict_low_util
    )
    # CPU: req=10, avail=14.4, util=0.1 => health=0.9, fit=1-(10/14.4)=0.3055... => score=0.275
    # Mem: req=8192, avail=52428.8, util=0.2 => health=0.8, fit=1-(8192/52428.8)=0.84375 => score=0.675
    # Sto: req=0 => score=1.0
    # Net: score=0.1
    # Final = (0.275 * 0.35) + (0.675 * 0.35) + (1.0 * 0.20) + (0.1 * 0.0)
    # Final = 0.09625 + 0.23625 + 0.2 = 0.5325
    assert score > fuzzy_gate_default.suitability_threshold
    assert np.isclose(score, 0.5325, atol=0.001)


def test_suitability_large_cpu_job_high_util(
    fuzzy_gate_default, sample_job_dict_large_cpu, sample_node_dict_high_util
):
    score = fuzzy_gate_default.calculate_node_suitability_for_task(
        sample_job_dict_large_cpu, sample_node_dict_high_util
    )
    # CPU: req=10, avail=0.8 => Does not fit! Score=0.0
    # Mem: req=8192, avail=6553.6 => Does not fit! Score=0.0
    # Sto: req=0 => score=1.0
    # Net: score=0.1
    # Final = (0.0 * 0.35) + (0.0 * 0.35) + (1.0 * 0.20) + (0.1 * 0.0)
    # Final = 0.2
    assert score < fuzzy_gate_default.suitability_threshold
    assert np.isclose(score, 0.2, atol=0.001)


def test_determine_suitable_nodes(
    fuzzy_gate_default,
    sample_job_dict_small,
    sample_job_dict_large_cpu,
    sample_node_dict_low_util,
    sample_node_dict_high_util,
):
    jobs = [sample_job_dict_small, sample_job_dict_large_cpu]
    nodes = [sample_node_dict_low_util, sample_node_dict_high_util]
    result = fuzzy_gate_default.determine_suitable_nodes(jobs, nodes)

    # Small job: score_low (0.767) > threshold(0.5), score_high (0.229) < threshold(0.5)
    assert "job-small" in result
    assert result["job-small"] == ["node-low"]

    # Large CPU job: score_low (0.532) > threshold(0.5), score_high (0.2) < threshold(0.5)
    assert "job-large-cpu" in result
    assert result["job-large-cpu"] == ["node-low"]


def test_determine_suitable_nodes_empty_jobs(
    fuzzy_gate_default, sample_node_dict_low_util
):
    result = fuzzy_gate_default.determine_suitable_nodes(
        [], [sample_node_dict_low_util]
    )
    assert result == {}


def test_determine_suitable_nodes_empty_nodes(
    fuzzy_gate_default, sample_job_dict_small
):
    result = fuzzy_gate_default.determine_suitable_nodes([sample_job_dict_small], [])
    assert result == {"job-small": []}


def test_determine_suitable_nodes_no_suitable(
    fuzzy_gate_default, sample_job_dict_large_mem, sample_node_dict_high_util
):
    # Large mem job (40GB) won't fit high util node's available mem (6.4GB)
    result = fuzzy_gate_default.determine_suitable_nodes(
        [sample_job_dict_large_mem], [sample_node_dict_high_util]
    )
    assert result == {"job-large-mem": []}
