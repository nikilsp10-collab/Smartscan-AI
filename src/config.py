"""
Configuration parameters for SmartScan AI.
Defines simulation sample rates, frequency bands, priority weights,
and ML model hyper-parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SimulationConfig:
    # Sampling frequency (Hz) - simulated Baseband/IF
    sampling_rate: float = 20_000_000.0  # 20 MHz
    sample_duration: float = 0.0005     # 500 microseconds per frame (10,000 samples)
    default_snr_db: float = 15.0        # Default Signal-to-Noise Ratio (dB)
    
    # Frequency bounds for simulation (Hz)
    min_freq: float = 1_000_000.0       # 1 MHz
    max_freq: float = 9_000_000.0       # 9 MHz
    
    # Classes of simulated electromagnetic signals
    signal_classes: List[str] = field(default_factory=lambda: [
        "CW",                # Continuous Wave / Carrier
        "PULSED_RADAR",      # Periodic pulsed radar emission
        "CHIRP_LFM",         # Linear Frequency Modulated chirp
        "FREQ_HOPPING",      # Frequency-hopping spread spectrum
        "NOISE_BACKGROUND",  # Background ambient AWGN
        "ANOMALY_UNKNOWN"    # Unrecognized / distorted / novel signal
    ])


@dataclass
class PriorityWeights:
    """Weights for the adaptive priority scoring formula:
       P = w_anomaly * AnomalyScore + w_threat * ThreatTier + w_uncertainty * (1 - Confidence) + w_snr * SNR_Norm
    """
    weight_anomaly: float = 0.40
    weight_threat: float = 0.25
    weight_uncertainty: float = 0.25
    weight_snr: float = 0.10

    # Threat tier multipliers for known signal categories
    threat_tier_map: Dict[str, float] = field(default_factory=lambda: {
        "ANOMALY_UNKNOWN": 1.0,     # Maximum threat attention
        "CHIRP_LFM": 0.85,          # High-tech tracking/fire-control radar
        "PULSED_RADAR": 0.70,       # Search/surveillance radar
        "FREQ_HOPPING": 0.60,       # Tactical secure communications
        "CW": 0.30,                 # Continuous carrier / beacon
        "NOISE_BACKGROUND": 0.05    # Pure noise baseline
    })


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = True
    db_path: str = "data/smartscan.db"


SIMULATION_CONFIG = SimulationConfig()
PRIORITY_WEIGHTS = PriorityWeights()
SERVER_CONFIG = ServerConfig()
