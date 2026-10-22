"""
SmartScan AI - Digital Signal Processing (DSP) Module
Author: SmartScan AI Team (Member 2: DSP & Feature Extraction Lead)

Transforms raw waveform time-series arrays into compact physical and spectral features:
- Time-domain statistics (RMS, Peak, Crest Factor, Zero-Crossing Rate)
- Fast Fourier Transform (FFT) & Power Spectral Density (PSD)
- Spectral Centroid, Bandwidth (3-dB), Spectral Rolloff
- Spectral Entropy (quantifies signal complexity / randomness)
- SNR estimation
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np
from scipy import signal as sp_signal

from src.simulator import SignalSample


@dataclass
class SignalFeatures:
    """Extracted physical and statistical fingerprint of an RF signal window."""
    sample_id: str
    signal_type: str
    center_frequency: float
    spectral_centroid: float
    bandwidth_3db: float
    spectral_entropy: float
    spectral_rolloff: float
    rms_power: float
    peak_amplitude: float
    crest_factor: float
    zero_crossing_rate: float
    estimated_snr_db: float

    def to_feature_vector(self) -> np.ndarray:
        """Returns ordered numerical feature array for scikit-learn models."""
        return np.array([
            self.center_frequency,
            self.spectral_centroid,
            self.bandwidth_3db,
            self.spectral_entropy,
            self.spectral_rolloff,
            self.rms_power,
            self.peak_amplitude,
            self.crest_factor,
            self.zero_crossing_rate,
            self.estimated_snr_db
        ], dtype=np.float64)

    def to_dict(self) -> dict:
        """Returns JSON-serializable dictionary with rounded metrics."""
        return {
            "sample_id": self.sample_id,
            "signal_type": self.signal_type,
            "center_frequency_mhz": round(self.center_frequency / 1e6, 3),
            "spectral_centroid_mhz": round(self.spectral_centroid / 1e6, 3),
            "bandwidth_3db_mhz": round(self.bandwidth_3db / 1e6, 3),
            "spectral_entropy": round(self.spectral_entropy, 4),
            "spectral_rolloff_mhz": round(self.spectral_rolloff / 1e6, 3),
            "rms_power": round(self.rms_power, 4),
            "crest_factor": round(self.crest_factor, 2),
            "zero_crossing_rate": round(self.zero_crossing_rate, 4),
            "estimated_snr_db": round(self.estimated_snr_db, 1)
        }


FEATURE_NAMES = [
    "center_frequency",
    "spectral_centroid",
    "bandwidth_3db",
    "spectral_entropy",
    "spectral_rolloff",
    "rms_power",
    "peak_amplitude",
    "crest_factor",
    "zero_crossing_rate",
    "estimated_snr_db"
]


class SignalProcessor:
    """DSP Pipeline for electromagnetic signal feature extraction."""

    def __init__(self, downsample_fft_bins: int = 256):
        self.downsample_fft_bins = downsample_fft_bins

    def compute_spectrum(self, sample: SignalSample) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes the Fast Fourier Transform (FFT) Power Spectrum.
        Returns: (freqs_hz, power_spectrum_db)
        """
        x = sample.data
        n = len(x)
        fs = sample.sampling_rate

        # Apply Hanning window to reduce spectral leakage
        windowed = x * np.hanning(n)
        fft_vals = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(n, d=1.0 / fs)

        # Power spectrum in linear and decibels
        power = (np.abs(fft_vals) ** 2) / n
        power_db = 10.0 * np.log10(np.maximum(power, 1e-12))

        return freqs, power_db

    def extract_features(self, sample: SignalSample) -> SignalFeatures:
        """Extracts complete time and frequency feature set from a signal sample."""
        x = sample.data
        fs = sample.sampling_rate
        n = len(x)

        # --- 1. Time-Domain Metrics ---
        rms = float(np.sqrt(np.mean(x ** 2)))
        peak = float(np.max(np.abs(x)))
        crest = float(peak / (rms + 1e-9))
        
        # Zero-Crossing Rate (ZCR)
        zero_crossings = np.sum(np.diff(np.signbit(x).astype(int)) != 0)
        zcr = float(zero_crossings / max(1, n - 1))

        # --- 2. Frequency-Domain (FFT) Metrics ---
        freqs, power_db = self.compute_spectrum(sample)
        power_linear = 10.0 ** (power_db / 10.0)
        total_power = np.sum(power_linear) + 1e-12

        # Normalized Power Spectral Density (PDF)
        psd_norm = power_linear / total_power

        # Center Frequency (Peak bin)
        peak_idx = int(np.argmax(power_linear))
        center_freq = float(freqs[peak_idx])

        # Spectral Centroid (Center of spectral mass)
        spectral_centroid = float(np.sum(freqs * psd_norm))

        # 3-dB Bandwidth (Frequency span where power >= peak_power / 2)
        peak_power = power_linear[peak_idx]
        half_power_mask = power_linear >= (peak_power * 0.5)
        if np.any(half_power_mask):
            bw_indices = np.where(half_power_mask)[0]
            bandwidth_3db = float(freqs[bw_indices[-1]] - freqs[bw_indices[0]])
        else:
            bandwidth_3db = 0.0

        # Spectral Entropy (measures disorder / noise-like quality)
        # H = - sum(p * log2(p)), normalized to [0, 1]
        valid_p = psd_norm[psd_norm > 1e-15]
        raw_entropy = -np.sum(valid_p * np.log2(valid_p))
        max_entropy = np.log2(len(psd_norm))
        spectral_entropy = float(raw_entropy / max(1e-6, max_entropy))
        spectral_entropy = float(np.clip(spectral_entropy, 0.0, 1.0))

        # Spectral Rolloff (Frequency below which 85% of power resides)
        cumulative_power = np.cumsum(psd_norm)
        rolloff_idx = np.searchsorted(cumulative_power, 0.85)
        rolloff_idx = min(rolloff_idx, len(freqs) - 1)
        spectral_rolloff = float(freqs[rolloff_idx])

        # Estimated SNR (Peak power relative to median spectral noise floor)
        noise_floor_db = float(np.median(power_db))
        peak_power_db = float(power_db[peak_idx])
        estimated_snr_db = float(np.clip(peak_power_db - noise_floor_db, 0.0, 50.0))

        return SignalFeatures(
            sample_id=sample.sample_id,
            signal_type=sample.signal_type,
            center_frequency=center_freq,
            spectral_centroid=spectral_centroid,
            bandwidth_3db=bandwidth_3db,
            spectral_entropy=spectral_entropy,
            spectral_rolloff=spectral_rolloff,
            rms_power=rms,
            peak_amplitude=peak,
            crest_factor=crest,
            zero_crossing_rate=zcr,
            estimated_snr_db=estimated_snr_db
        )

    def get_spectrum_preview(self, sample: SignalSample) -> dict:
        """Returns downsampled spectrum (e.g. 256 bins) for fast browser rendering."""
        freqs, power_db = self.compute_spectrum(sample)
        step = max(1, len(freqs) // self.downsample_fft_bins)
        return {
            "frequencies_mhz": np.round(freqs[::step] / 1e6, 3).tolist(),
            "power_db": np.round(power_db[::step], 2).tolist()
        }
