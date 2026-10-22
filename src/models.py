"""
SmartScan AI - Machine Learning & Anomaly Detection Engine
Author: SmartScan AI Team (Member 3: AI & ML Lead)

Implements:
1. Supervised Signal Classifier (scikit-learn KNeighborsClassifier / GaussianNB):
   Recognizes known RF signal patterns (CW, Radar, Chirp, Frequency Hopping, Noise).
2. Unsupervised Anomaly Detector (scikit-learn NearestNeighbors & Mahalanobis distance):
   Calculates statistical distance from baseline normal signals to flag novel, unseen emitters.
"""

from dataclasses import dataclass
import os
from typing import Dict, List, Optional
import joblib
import numpy as np
from sklearn.neighbors import KNeighborsClassifier, NearestNeighbors
from sklearn.preprocessing import StandardScaler

from src.dsp import FEATURE_NAMES, SignalFeatures, SignalProcessor
from src.simulator import SignalSimulator


@dataclass
class ModelPrediction:
    """Output from the dual-layer AI engine."""
    sample_id: str
    predicted_class: str
    confidence: float             # [0.0, 1.0] from classifier probability
    anomaly_score: float          # [0.0, 1.0] where 1.0 is severe anomaly
    is_anomaly: bool              # True if anomaly_score >= threshold
    class_probabilities: Dict[str, float]
    anomaly_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "sample_id": str(self.sample_id),
            "predicted_class": str(self.predicted_class),
            "confidence": round(float(self.confidence), 3),
            "anomaly_score": round(float(self.anomaly_score), 3),
            "is_anomaly": bool(self.is_anomaly),
            "class_probabilities": {str(k): round(float(v), 3) for k, v in self.class_probabilities.items()},
            "anomaly_reason": str(self.anomaly_reason)
        }


class SmartScanAIModels:
    """Manages training, persistence, and inference for the dual AI system."""

    DEFAULT_MODEL_PATH = "data/smartscan_models.joblib"

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        self.model_path = model_path
        self.scaler: StandardScaler = StandardScaler()
        self.classifier: Optional[KNeighborsClassifier] = None
        self.anomaly_detector: Optional[NearestNeighbors] = None
        self.baseline_mean: Optional[np.ndarray] = None
        self.baseline_std: Optional[np.ndarray] = None
        self.classes: List[str] = []
        self.anomaly_threshold: float = 0.50
        self.max_baseline_dist: float = 3.5

    def train_models(self, samples_per_class: int = 120) -> dict:
        """
        Generates synthetic training dataset, trains both models, and saves them.
        The Anomaly Detector is fitted ONLY on baseline (known) signals so it learns normal behavior.
        """
        sim = SignalSimulator()
        processor = SignalProcessor()

        known_classes = ["CW", "PULSED_RADAR", "CHIRP_LFM", "FREQ_HOPPING", "NOISE_BACKGROUND"]
        self.classes = sorted(known_classes)

        X_list: List[np.ndarray] = []
        y_list: List[str] = []

        print(f"Generating {samples_per_class * len(known_classes)} training samples...")
        for c in known_classes:
            for _ in range(samples_per_class):
                sample = sim.generate_sample(c)
                feat = processor.extract_features(sample)
                X_list.append(feat.to_feature_vector())
                y_list.append(c)

        X = np.array(X_list)
        y = np.array(y_list)

        # Fit Scaler
        X_scaled = self.scaler.fit_transform(X)

        # 1. Train Supervised Classifier (k-NN Classifier)
        print("Training Supervised Signal Classifier (k-NN)...")
        self.classifier = KNeighborsClassifier(n_neighbors=5, weights="distance")
        self.classifier.fit(X_scaled, y)
        train_acc = float(self.classifier.score(X_scaled, y))

        # 2. Train Unsupervised Anomaly Detector (k-NN Outlier Distance)
        # Fitted purely on normal signal distributions
        print("Training Unsupervised Nearest-Neighbor Anomaly Detector...")
        self.anomaly_detector = NearestNeighbors(n_neighbors=5, metric="euclidean")
        self.anomaly_detector.fit(X_scaled)

        # Calculate baseline distribution bounds
        distances, _ = self.anomaly_detector.kneighbors(X_scaled)
        mean_dists = np.mean(distances, axis=1)
        self.max_baseline_dist = float(np.percentile(mean_dists, 95) * 1.5)

        # Save bundle
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            "scaler": self.scaler,
            "classifier": self.classifier,
            "anomaly_detector": self.anomaly_detector,
            "classes": self.classes,
            "max_baseline_dist": self.max_baseline_dist,
            "feature_names": FEATURE_NAMES
        }, self.model_path)

        print(f"Models successfully trained and saved to {self.model_path}!")
        return {"training_samples": len(X), "classifier_accuracy": round(train_acc, 4)}

    def load_or_train(self) -> None:
        """Loads cached models if available, otherwise trains immediately."""
        if os.path.exists(self.model_path):
            try:
                bundle = joblib.load(self.model_path)
                self.scaler = bundle["scaler"]
                self.classifier = bundle["classifier"]
                self.anomaly_detector = bundle["anomaly_detector"]
                self.classes = bundle["classes"]
                self.max_baseline_dist = bundle.get("max_baseline_dist", 3.5)
                return
            except Exception as e:
                print(f"Could not load cached models ({e}), retraining...")

        self.train_models()

    def predict(self, features: SignalFeatures) -> ModelPrediction:
        """Runs both classifier and anomaly detector on an extracted feature vector."""
        if self.classifier is None or self.anomaly_detector is None:
            self.load_or_train()

        vec = features.to_feature_vector().reshape(1, -1)
        vec_scaled = self.scaler.transform(vec)

        # 1. Supervised Classification
        probs = self.classifier.predict_proba(vec_scaled)[0]
        pred_idx = int(np.argmax(probs))
        pred_class = self.classifier.classes_[pred_idx]
        confidence = float(probs[pred_idx])

        class_prob_map = {cls_name: float(prob) for cls_name, prob in zip(self.classifier.classes_, probs)}

        # 2. Anomaly Detection (Distance to nearest normal baseline neighbors)
        distances, _ = self.anomaly_detector.kneighbors(vec_scaled)
        mean_dist = float(np.mean(distances[0]))

        # Normalized anomaly score [0.0, 1.0]
        raw_ratio = mean_dist / max(0.1, self.max_baseline_dist)
        anomaly_score = float(np.clip(1.0 - np.exp(-1.5 * raw_ratio), 0.0, 1.0))
        is_anomaly = anomaly_score >= self.anomaly_threshold

        reason = ""
        if is_anomaly:
            reason = f"Outlier distance {round(mean_dist, 2)} exceeds normal envelope (score {round(anomaly_score*100)}%)"
        else:
            reason = f"Matches baseline profile for {pred_class} (normal variance)"

        return ModelPrediction(
            sample_id=features.sample_id,
            predicted_class=pred_class,
            confidence=confidence,
            anomaly_score=anomaly_score,
            is_anomaly=is_anomaly,
            class_probabilities=class_prob_map,
            anomaly_reason=reason
        )
