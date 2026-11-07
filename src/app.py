"""
SmartScan AI - Flask Web Application & REST API
Author: SmartScan AI Team (Member 5: Backend & System Integration Lead)

Provides REST endpoints for:
- Live Queue Streaming & Prioritization
- Signal Waveform & FFT Spectrum Extraction
- Batch & Single Signal Simulation
- Operator Triage & Acknowledgement
- Automated Benchmarking (Fixed-Order vs Adaptive Review)
"""

import os
from flask import Flask, jsonify, render_template, request

from src.benchmark import BenchmarkSuite
from src.config import SERVER_CONFIG
from src.dsp import SignalProcessor
from src.models import SmartScanAIModels
from src.priority_engine import AdaptivePriorityQueue, PriorityScoringEngine
from src.simulator import SignalSimulator

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, "templates")
static_dir = os.path.join(base_dir, "static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Initialize singletons
simulator = SignalSimulator()
processor = SignalProcessor(downsample_fft_bins=200)
ai_models = SmartScanAIModels()
ai_models.load_or_train()
priority_engine = PriorityScoringEngine()
queue = AdaptivePriorityQueue()
benchmark_suite = BenchmarkSuite()


def process_and_enqueue(sample):
    """Pipeline: Signal -> DSP Features -> AI Inference -> Priority Scoring -> Queue Enqueue."""
    features = processor.extract_features(sample)
    prediction = ai_models.predict(features)
    prioritized_item = priority_engine.evaluate_sample(features, prediction)

    # Build preview payload for plotting
    time_preview = sample.to_dict(downsample_points=350)
    spectrum_preview = processor.get_spectrum_preview(sample)
    spectrogram_preview = processor.compute_spectrogram(sample)

    payload = {
        "sample_id": sample.sample_id,
        "signal_type": sample.signal_type,
        "time_preview": time_preview["time_preview"],
        "waveform_preview": time_preview["waveform_preview"],
        "frequencies_mhz": spectrum_preview["frequencies_mhz"],
        "power_db": spectrum_preview["power_db"],
        "spectrogram": spectrogram_preview,
        "features": features.to_dict(),
        "prediction": prediction.to_dict(),
        "prioritization": prioritized_item.to_dict()
    }

    queue.add(prioritized_item, payload)
    return prioritized_item


# Seed initial signals into queue
initial_batch = simulator.generate_random_batch(count=8, anomaly_prob=0.25)
for s in initial_batch:
    process_and_enqueue(s)


# --- HTML Route ---

@app.route("/")
@app.route("/api/index")
@app.route("/api/index.py")
def index():
    """Serves the Tactical Operator Dashboard."""
    return render_template("index.html")


# --- REST API Routes ---

@app.route("/api/queue", methods=["GET"])
def get_queue():
    """Returns the current prioritized triage queue."""
    include_reviewed = request.args.get("include_reviewed", "true").lower() == "true"
    items = queue.get_items(include_reviewed=include_reviewed)
    return jsonify({
        "status": "success",
        "total_in_queue": len(items),
        "queue": items
    })


@app.route("/api/sample/<sample_id>", methods=["GET"])
def get_sample_details(sample_id):
    """Delivers detailed waveform, FFT spectrum, and explanation metrics for Chart.js."""
    preview = queue.get_preview(sample_id)
    if not preview:
        return jsonify({"status": "error", "message": "Sample ID not found"}), 404
    return jsonify({"status": "success", "data": preview})


@app.route("/api/sample/<sample_id>/review", methods=["POST"])
def review_sample(sample_id):
    """Marks a sample as reviewed by the operator."""
    found = queue.mark_reviewed(sample_id)
    if not found:
        return jsonify({"status": "error", "message": "Sample ID not found"}), 404
    return jsonify({"status": "success", "sample_id": sample_id, "reviewed": True})


@app.route("/api/simulate/batch", methods=["POST"])
def simulate_batch():
    """Simulates a batch of incoming RF signals and pushes them into the priority queue."""
    data = request.get_json() or {}
    count = int(data.get("count", 6))
    anomaly_rate = float(data.get("anomaly_rate", 0.25))

    samples = simulator.generate_random_batch(count=count, anomaly_prob=anomaly_rate)
    added_items = [process_and_enqueue(s).to_dict() for s in samples]

    return jsonify({
        "status": "success",
        "added_count": len(added_items),
        "total_queue_count": len(queue.queue),
        "newly_added": added_items
    })


@app.route("/api/simulate/single", methods=["POST"])
def simulate_single():
    """Injects a specific signal type into the spectrum queue."""
    data = request.get_json() or {}
    signal_type = data.get("signal_type", "CW")
    snr_db = data.get("snr_db")
    if snr_db is not None:
        snr_db = float(snr_db)

    try:
        sample = simulator.generate_sample(signal_type, snr_db=snr_db)
        item = process_and_enqueue(sample)
        return jsonify({
            "status": "success",
            "sample": item.to_dict()
        })
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/queue/clear", methods=["POST"])
def clear_queue():
    """Clears all signals from the active triage queue."""
    queue.clear()
    return jsonify({"status": "success", "message": "Queue cleared"})


@app.route("/api/benchmark", methods=["GET", "POST"])
def run_benchmark():
    """Runs comparative evaluation between Fixed-Order and Adaptive Review."""
    sample_count = 30
    if request.is_json and request.json:
        sample_count = int(request.json.get("sample_count", 30))
    elif request.args.get("count"):
        sample_count = int(request.args.get("count", 30))

    results = benchmark_suite.run_comparison(sample_count=sample_count)
    return jsonify({"status": "success", "benchmark": results})


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "system": "SmartScan AI Electronic Warfare Prioritization",
        "queue_size": len(queue.queue)
    })


if __name__ == "__main__":
    print(f"Starting SmartScan AI Operator Dashboard on http://{SERVER_CONFIG.host}:{SERVER_CONFIG.port}")
    app.run(host=SERVER_CONFIG.host, port=SERVER_CONFIG.port, debug=SERVER_CONFIG.debug)
