"""
SmartScan AI - Benchmarking & Performance Comparison Suite
Author: SmartScan AI Team

Directly implements Slide 9 of the project specification:
Compares Traditional Fixed-Order Scanning vs SmartScan Adaptive Scanning on the same signal dataset.
Measures:
1. Average Review Position (ARP) of Critical/Flagged Samples
2. Classification Accuracy on Known Signals
3. False-Alarm Rate (FAR) on Baseline Signals
4. Average Processing Latency (DSP + AI) per Sample
"""

import time
from typing import Dict, List
import numpy as np

from src.dsp import SignalProcessor
from src.models import SmartScanAIModels
from src.priority_engine import PriorityScoringEngine
from src.simulator import SignalSimulator


class BenchmarkSuite:
    """Runs automated empirical comparisons between Fixed-Order and Adaptive Review."""

    def __init__(self):
        self.simulator = SignalSimulator()
        self.processor = SignalProcessor()
        self.ai = SmartScanAIModels()
        self.ai.load_or_train()
        self.engine = PriorityScoringEngine()

    def run_comparison(self, sample_count: int = 40, anomaly_rate: float = 0.20) -> dict:
        """
        Ingests a synthetic dataset of mixed normal and anomalous signals.
        Evaluates triage efficiency under Fixed-Order Review vs Adaptive Prioritization.
        """
        # 1. Generate identical test batch
        samples = self.simulator.generate_random_batch(count=sample_count, anomaly_prob=anomaly_rate)

        processing_latencies: List[float] = []
        prioritized_items: List[dict] = []

        correct_classifications = 0
        total_known_samples = 0
        false_alarms = 0
        total_baseline_samples = 0

        # Process each signal through the pipeline
        for idx, sample in enumerate(samples):
            t0 = time.perf_counter()
            features = self.processor.extract_features(sample)
            prediction = self.ai.predict(features)
            eval_item = self.engine.evaluate_sample(features, prediction, arrival_order=idx + 1)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            processing_latencies.append(latency_ms)

            is_ground_truth_anomaly = (sample.signal_type == "ANOMALY_UNKNOWN")

            # Accuracy on known baseline classes
            if not is_ground_truth_anomaly:
                total_known_samples += 1
                total_baseline_samples += 1
                if prediction.predicted_class == sample.signal_type:
                    correct_classifications += 1
                # Check false alarm (normal signal falsely tagged as high anomaly)
                if eval_item.is_anomaly:
                    false_alarms += 1

            is_threat = is_ground_truth_anomaly or (sample.signal_type == "CHIRP_LFM")
            prioritized_items.append({
                "sample_id": sample.sample_id,
                "ground_truth_type": sample.signal_type,
                "is_critical": is_threat,
                "fixed_order_pos": idx + 1,
                "priority_score": eval_item.priority_score,
                "priority_level": eval_item.priority_level
            })

        # 2. Sort by Adaptive Priority (Descending)
        adaptive_sorted = sorted(prioritized_items, key=lambda x: x["priority_score"], reverse=True)
        for rank, item in enumerate(adaptive_sorted, start=1):
            item["adaptive_order_pos"] = rank

        # 3. Calculate Average Review Position (ARP) for Critical/Threat Samples
        critical_items = [it for it in adaptive_sorted if it["is_critical"]]
        if critical_items:
            avg_fixed_pos = float(np.mean([it["fixed_order_pos"] for it in critical_items]))
            avg_adaptive_pos = float(np.mean([it["adaptive_order_pos"] for it in critical_items]))
            improvement_pct = max(0.0, ((avg_fixed_pos - avg_adaptive_pos) / avg_fixed_pos) * 100.0)
        else:
            avg_fixed_pos = sample_count / 2.0
            avg_adaptive_pos = sample_count / 2.0
            improvement_pct = 0.0

        # Metrics
        accuracy = float((correct_classifications / max(1, total_known_samples)) * 100.0)
        far = float((false_alarms / max(1, total_baseline_samples)) * 100.0)
        avg_latency = float(np.mean(processing_latencies))

        return {
            "total_samples": sample_count,
            "critical_samples_count": len(critical_items),
            "fixed_order_avg_position": round(avg_fixed_pos, 1),
            "adaptive_avg_position": round(avg_adaptive_pos, 1),
            "position_improvement_pct": round(improvement_pct, 1),
            "classification_accuracy_pct": round(accuracy, 1),
            "false_alarm_rate_pct": round(far, 1),
            "average_latency_ms": round(avg_latency, 2),
            "samples_summary": [
                {
                    "sample_id": it["sample_id"],
                    "type": it["ground_truth_type"],
                    "score": round(it["priority_score"], 1),
                    "fixed_pos": it["fixed_order_pos"],
                    "adaptive_pos": it["adaptive_order_pos"]
                }
                for it in adaptive_sorted[:12]
            ]
        }
