"""
SmartScan AI - Test Suite
Verifies signal simulation, DSP extraction, ML inference, priority ranking, and Flask endpoints.
"""

import pytest
from src.app import app
from src.benchmark import BenchmarkSuite
from src.dsp import SignalProcessor
from src.models import SmartScanAIModels
from src.priority_engine import AdaptivePriorityQueue, PriorityScoringEngine
from src.simulator import SignalSimulator


@pytest.fixture
def simulator():
    return SignalSimulator()


@pytest.fixture
def processor():
    return SignalProcessor()


@pytest.fixture
def ai_models():
    models = SmartScanAIModels()
    models.load_or_train()
    return models


@pytest.fixture
def priority_engine():
    return PriorityScoringEngine()


def test_signal_simulator_generation(simulator):
    """Verifies all 6 signal types generate non-empty arrays with correct sample length."""
    types = ["CW", "PULSED_RADAR", "CHIRP_LFM", "FREQ_HOPPING", "NOISE_BACKGROUND", "ANOMALY_UNKNOWN"]
    for t in types:
        sample = simulator.generate_sample(t)
        assert sample.signal_type == t
        assert len(sample.data) == 10000
        assert len(sample.time_array) == 10000


def test_dsp_feature_extraction(simulator, processor):
    """Verifies DSP features are within realistic physical bounds."""
    sample = simulator.generate_chirp_lfm()
    feat = processor.extract_features(sample)
    assert feat.center_frequency > 0
    assert feat.bandwidth_3db > 0
    assert 0.0 <= feat.spectral_entropy <= 1.0
    assert feat.rms_power > 0
    assert len(feat.to_feature_vector()) == 10


def test_ai_anomaly_detection(simulator, processor, ai_models):
    """Verifies an anomaly receives a high anomaly score compared to a standard CW signal."""
    cw = simulator.generate_cw()
    anom = simulator.generate_anomaly_unknown()

    feat_cw = processor.extract_features(cw)
    feat_anom = processor.extract_features(anom)

    pred_cw = ai_models.predict(feat_cw)
    pred_anom = ai_models.predict(feat_anom)

    assert pred_anom.anomaly_score > pred_cw.anomaly_score
    assert pred_anom.is_anomaly is True


def test_priority_queue_sorting(simulator, processor, ai_models, priority_engine):
    """Verifies that high-urgency signals jump to the top of the queue."""
    q = AdaptivePriorityQueue()

    low_sample = simulator.generate_cw()
    high_sample = simulator.generate_anomaly_unknown()

    eval_low = priority_engine.evaluate_sample(
        processor.extract_features(low_sample),
        ai_models.predict(processor.extract_features(low_sample))
    )
    eval_high = priority_engine.evaluate_sample(
        processor.extract_features(high_sample),
        ai_models.predict(processor.extract_features(high_sample))
    )

    q.add(eval_low, low_sample.to_dict())
    q.add(eval_high, high_sample.to_dict())

    items = q.get_items()
    assert items[0]["sample_id"] == high_sample.sample_id
    assert items[0]["priority_score"] >= items[1]["priority_score"]


def test_benchmark_suite():
    """Verifies the Slide 9 benchmark suite runs and returns required metrics."""
    bench = BenchmarkSuite()
    res = bench.run_comparison(sample_count=15)
    assert "fixed_order_avg_position" in res
    assert "adaptive_avg_position" in res
    assert "classification_accuracy_pct" in res
    assert "average_latency_ms" in res
    assert res["average_latency_ms"] < 20.0  # Fast DSP + inference


def test_flask_api_routes():
    """Verifies Flask REST endpoints function properly."""
    client = app.test_client()

    # GET /
    res_index = client.get("/")
    assert res_index.status_code == 200

    # GET /api/queue
    res_queue = client.get("/api/queue")
    assert res_queue.status_code == 200
    assert "queue" in res_queue.get_json()

    # POST /api/simulate/batch
    res_batch = client.post("/api/simulate/batch", json={"count": 3})
    assert res_batch.status_code == 200
    assert res_batch.get_json()["added_count"] == 3

    # GET /api/benchmark
    res_bench = client.get("/api/benchmark?count=10")
    assert res_bench.status_code == 200
    assert res_bench.get_json()["status"] == "success"
