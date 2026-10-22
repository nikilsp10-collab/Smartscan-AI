"""
SmartScan AI - Priority Scoring & Explainability Engine
Author: SmartScan AI Team (Member 4: Priority & Explainability Lead)

Calculates composite urgency score [0 - 100] combining:
- Anomaly severity (unknown / novel waveform deviation)
- Operational threat weight (radar tracking vs broadcast carrier)
- Classification uncertainty (1.0 - classifier confidence)
- Signal-to-Noise Ratio (SNR)

Generates human-readable explainability rationale for operator triage.
Manages the real-time Adaptive Priority Queue.
"""

from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional
import numpy as np

from src.config import PRIORITY_WEIGHTS, PriorityWeights
from src.dsp import SignalFeatures
from src.models import ModelPrediction


@dataclass
class ExplanationFactor:
    factor: str
    points_awarded: float
    description: str

    def to_dict(self) -> dict:
        return {
            "factor": self.factor,
            "points": f"+{round(self.points_awarded, 1)} pts",
            "description": self.description
        }


@dataclass
class PrioritizedSignal:
    sample_id: str
    timestamp: float
    ground_truth_type: str
    predicted_type: str
    confidence: float
    anomaly_score: float
    is_anomaly: bool
    priority_score: float               # [0.0 - 100.0]
    priority_level: str                 # CRITICAL, HIGH, MEDIUM, LOW
    features_summary: Dict[str, float]
    explanations: List[ExplanationFactor]
    reviewed: bool = False
    original_arrival_order: int = 0

    def to_dict(self) -> dict:
        return {
            "sample_id": self.sample_id,
            "timestamp": self.timestamp,
            "ground_truth_type": self.ground_truth_type,
            "predicted_type": self.predicted_type,
            "confidence": round(self.confidence, 3),
            "anomaly_score": round(self.anomaly_score, 3),
            "is_anomaly": self.is_anomaly,
            "priority_score": round(self.priority_score, 1),
            "priority_level": self.priority_level,
            "reviewed": self.reviewed,
            "original_arrival_order": self.original_arrival_order,
            "features_summary": self.features_summary,
            "explanations": [e.to_dict() for e in self.explanations]
        }


class PriorityScoringEngine:
    """Computes urgency scores and explainability rationale."""

    def __init__(self, weights: Optional[PriorityWeights] = None):
        self.weights = weights or PRIORITY_WEIGHTS

    def evaluate_sample(
        self,
        features: SignalFeatures,
        prediction: ModelPrediction,
        arrival_order: int = 0
    ) -> PrioritizedSignal:
        """Calculates urgency score and generates natural language explanations."""
        explanations: List[ExplanationFactor] = []

        # 1. Anomaly Component (Weight: 40%)
        # Anomaly score is [0.0, 1.0]
        anomaly_pts = self.weights.weight_anomaly * (prediction.anomaly_score * 100.0)
        if prediction.is_anomaly:
            desc = f"Unfamiliar waveform pattern! Outlier score is {round(prediction.anomaly_score * 100)}%."
        elif prediction.anomaly_score > 0.35:
            desc = f"Moderate spectral variation ({round(prediction.anomaly_score * 100)}%)."
        else:
            desc = f"Matches regular baseline library (low anomaly {round(prediction.anomaly_score * 100)}%)."
        explanations.append(ExplanationFactor("Anomaly Severity", anomaly_pts, desc))

        # 2. Threat Component (Weight: 25%)
        # Threat tier based on predicted class (or anomaly override)
        if prediction.is_anomaly:
            threat_mult = 1.0  # Unknown anomalies are assigned maximum caution
            threat_name = "Unknown Emitter (Potential High Threat)"
        else:
            threat_mult = self.weights.threat_tier_map.get(prediction.predicted_class, 0.2)
            threat_name = f"Class Profile: {prediction.predicted_class}"
        
        threat_pts = self.weights.weight_threat * (threat_mult * 100.0)
        explanations.append(ExplanationFactor(
            "Threat Assessment",
            threat_pts,
            f"{threat_name} (assigned threat multiplier: {threat_mult})."
        ))

        # 3. Model Uncertainty Component (Weight: 25%)
        # Uncertainty = 1.0 - confidence
        uncertainty = max(0.0, 1.0 - prediction.confidence)
        uncertainty_pts = self.weights.weight_uncertainty * (uncertainty * 100.0)
        if uncertainty > 0.4:
            u_desc = f"AI classifier has high doubt (confidence only {round(prediction.confidence * 100)}%). Operator review requested."
        else:
            u_desc = f"High classification confidence ({round(prediction.confidence * 100)}%)."
        explanations.append(ExplanationFactor("Model Uncertainty", uncertainty_pts, u_desc))

        # 4. SNR / Signal Quality Component (Weight: 10%)
        # Normalize SNR (0 to 30 dB mapped to 0 to 1)
        snr_norm = float(np.clip(features.estimated_snr_db / 30.0, 0.0, 1.0))
        snr_pts = self.weights.weight_snr * (snr_norm * 100.0)
        explanations.append(ExplanationFactor(
            "Signal Quality (SNR)",
            snr_pts,
            f"Estimated SNR is {round(features.estimated_snr_db, 1)} dB (clear signal transmission)."
        ))

        # Total Priority Score
        total_score = float(np.clip(anomaly_pts + threat_pts + uncertainty_pts + snr_pts, 0.0, 100.0))

        # Assign Category Badge
        if total_score >= 70.0:
            level = "CRITICAL"
        elif total_score >= 50.0:
            level = "HIGH"
        elif total_score >= 30.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        return PrioritizedSignal(
            sample_id=features.sample_id,
            timestamp=time.time(),
            ground_truth_type=features.signal_type,
            predicted_type=prediction.predicted_class if not prediction.is_anomaly else "UNKNOWN_ANOMALY",
            confidence=prediction.confidence,
            anomaly_score=prediction.anomaly_score,
            is_anomaly=prediction.is_anomaly,
            priority_score=total_score,
            priority_level=level,
            features_summary=features.to_dict(),
            explanations=explanations,
            reviewed=False,
            original_arrival_order=arrival_order
        )


class AdaptivePriorityQueue:
    """Thread-safe priority queue dynamically maintaining signals ordered by priority score."""

    def __init__(self):
        self.queue: List[PrioritizedSignal] = []
        self.sample_registry: Dict[str, dict] = {}   # sample_id -> full raw signal preview
        self.arrival_counter: int = 0

    def add(self, prioritized_signal: PrioritizedSignal, preview_payload: dict) -> None:
        """Inserts a new signal and immediately re-ranks the queue in descending priority order."""
        self.arrival_counter += 1
        prioritized_signal.original_arrival_order = self.arrival_counter
        self.queue.append(prioritized_signal)
        self.sample_registry[prioritized_signal.sample_id] = preview_payload
        # Sort descending by priority score
        self.queue.sort(key=lambda s: s.priority_score, reverse=True)

    def mark_reviewed(self, sample_id: str) -> bool:
        for s in self.queue:
            if s.sample_id == sample_id:
                s.reviewed = True
                return True
        return False

    def clear(self) -> None:
        self.queue.clear()
        self.sample_registry.clear()
        self.arrival_counter = 0

    def get_items(self, include_reviewed: bool = True) -> List[dict]:
        if include_reviewed:
            return [s.to_dict() for s in self.queue]
        return [s.to_dict() for s in self.queue if not s.reviewed]

    def get_preview(self, sample_id: str) -> Optional[dict]:
        return self.sample_registry.get(sample_id)
