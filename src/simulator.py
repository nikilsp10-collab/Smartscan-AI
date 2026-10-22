"""
SmartScan AI - Signal Simulator Module
Author: SmartScan AI Team (Member 1: Data & Simulation Lead)

Generates realistic mathematical representations of electromagnetic signals:
1. CW (Continuous Wave / Radio Carrier)
2. PULSED_RADAR (Periodic pulse train with pulse width and PRI)
3. CHIRP_LFM (Linear Frequency Modulation radar sweep)
4. FREQ_HOPPING (Tactical frequency-hopping spread spectrum)
5. NOISE_BACKGROUND (Ambient white noise floor)
6. ANOMALY_UNKNOWN (Novel / irregular / distorted waveform)
"""

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

from src.config import SIMULATION_CONFIG, SimulationConfig


@dataclass
class SignalSample:
    """Represents a single captured or simulated signal window."""
    sample_id: str
    signal_type: str
    time_array: np.ndarray
    data: np.ndarray
    sampling_rate: float
    snr_db: float
    metadata: Dict[str, float] = field(default_factory=dict)

    def to_dict(self, downsample_points: int = 500) -> dict:
        """Serializes sample metadata and a downsampled waveform for frontend JSON visualization."""
        step = max(1, len(self.data) // downsample_points)
        return {
            "sample_id": self.sample_id,
            "signal_type": self.signal_type,
            "sampling_rate": self.sampling_rate,
            "snr_db": round(float(self.snr_db), 2),
            "metadata": self.metadata,
            "time_preview": self.time_array[::step].tolist(),
            "waveform_preview": np.round(self.data[::step], 4).tolist()
        }


def add_awgn(signal: np.ndarray, snr_db: float) -> np.ndarray:
    """Adds Additive White Gaussian Noise (AWGN) to a signal for a specified SNR in dB."""
    signal_power = np.mean(signal ** 2)
    if signal_power == 0:
        return np.random.normal(0, 1.0, len(signal))
    
    snr_linear = 10.0 ** (snr_db / 10.0)
    noise_power = signal_power / snr_linear
    noise = np.random.normal(0, np.sqrt(noise_power), len(signal))
    return signal + noise


class SignalSimulator:
    """Simulator engine to create synthetic RF signal samples."""

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SIMULATION_CONFIG
        self.fs = self.config.sampling_rate
        self.duration = self.config.sample_duration
        self.num_samples = int(self.fs * self.duration)
        self.time_array = np.linspace(0, self.duration, self.num_samples, endpoint=False)

    def generate_cw(self, fc: Optional[float] = None, snr_db: Optional[float] = None) -> SignalSample:
        """Continuous Wave (CW): Steady single-frequency carrier tone."""
        if fc is None:
            fc = np.random.uniform(2_000_000, 8_000_000)
        if snr_db is None:
            snr_db = np.random.uniform(10.0, 25.0)

        phase_noise = np.random.normal(0, 0.05, self.num_samples)
        raw_signal = np.cos(2 * np.pi * fc * self.time_array + phase_noise)
        noisy_signal = add_awgn(raw_signal, snr_db)

        return SignalSample(
            sample_id=str(uuid.uuid4())[:8],
            signal_type="CW",
            time_array=self.time_array,
            data=noisy_signal,
            sampling_rate=self.fs,
            snr_db=snr_db,
            metadata={"center_frequency": fc, "bandwidth": 0.0, "pulse_width": self.duration}
        )

    def generate_pulsed_radar(self, fc: Optional[float] = None, snr_db: Optional[float] = None) -> SignalSample:
        """Pulsed Radar: Periodic bursts of RF pulses."""
        if fc is None:
            fc = np.random.uniform(3_000_000, 7_000_000)
        if snr_db is None:
            snr_db = np.random.uniform(8.0, 22.0)

        pri = self.duration / 3.0       # Pulse Repetition Interval (~3 pulses in window)
        pulse_width = pri * 0.25        # 25% Duty cycle

        pulse_envelope = np.zeros(self.num_samples)
        for i in range(3):
            t_start = i * pri
            t_end = t_start + pulse_width
            mask = (self.time_array >= t_start) & (self.time_array < t_end)
            pulse_envelope[mask] = 1.0

        carrier = np.cos(2 * np.pi * fc * self.time_array)
        raw_signal = pulse_envelope * carrier
        noisy_signal = add_awgn(raw_signal, snr_db)

        return SignalSample(
            sample_id=str(uuid.uuid4())[:8],
            signal_type="PULSED_RADAR",
            time_array=self.time_array,
            data=noisy_signal,
            sampling_rate=self.fs,
            snr_db=snr_db,
            metadata={"center_frequency": fc, "bandwidth": 1.0 / pulse_width, "pulse_width": pulse_width}
        )

    def generate_chirp_lfm(self, f_start: Optional[float] = None, f_end: Optional[float] = None, snr_db: Optional[float] = None) -> SignalSample:
        """Chirp / Linear Frequency Modulation (LFM) radar pulse: Frequency sweeps over time."""
        if f_start is None:
            f_start = np.random.uniform(2_000_000, 4_000_000)
        if f_end is None:
            f_end = f_start + np.random.uniform(2_000_000, 4_000_000)
        if snr_db is None:
            snr_db = np.random.uniform(10.0, 24.0)

        # Instantaneous phase for linear frequency sweep
        # f(t) = f_start + ((f_end - f_start) / duration) * t
        sweep_rate = (f_end - f_start) / self.duration
        instantaneous_phase = 2 * np.pi * (f_start * self.time_array + 0.5 * sweep_rate * (self.time_array ** 2))
        raw_signal = np.cos(instantaneous_phase)
        noisy_signal = add_awgn(raw_signal, snr_db)

        return SignalSample(
            sample_id=str(uuid.uuid4())[:8],
            signal_type="CHIRP_LFM",
            time_array=self.time_array,
            data=noisy_signal,
            sampling_rate=self.fs,
            snr_db=snr_db,
            metadata={
                "center_frequency": (f_start + f_end) / 2.0,
                "bandwidth": abs(f_end - f_start),
                "pulse_width": self.duration
            }
        )

    def generate_frequency_hopping(self, hops: int = 4, snr_db: Optional[float] = None) -> SignalSample:
        """Frequency Hopping Spread Spectrum (FHSS): Discrete frequency hops across time slices."""
        if snr_db is None:
            snr_db = np.random.uniform(8.0, 20.0)

        hop_frequencies = np.random.uniform(2_000_000, 8_000_000, size=hops)
        slice_len = self.num_samples // hops
        raw_signal = np.zeros(self.num_samples)

        for i, hop_fc in enumerate(hop_frequencies):
            idx_start = i * slice_len
            idx_end = self.num_samples if i == hops - 1 else (i + 1) * slice_len
            t_slice = self.time_array[idx_start:idx_end]
            raw_signal[idx_start:idx_end] = np.cos(2 * np.pi * hop_fc * t_slice)

        noisy_signal = add_awgn(raw_signal, snr_db)
        return SignalSample(
            sample_id=str(uuid.uuid4())[:8],
            signal_type="FREQ_HOPPING",
            time_array=self.time_array,
            data=noisy_signal,
            sampling_rate=self.fs,
            snr_db=snr_db,
            metadata={
                "center_frequency": float(np.mean(hop_frequencies)),
                "bandwidth": float(np.max(hop_frequencies) - np.min(hop_frequencies)),
                "pulse_width": self.duration / hops
            }
        )

    def generate_noise(self, snr_db: float = 0.0) -> SignalSample:
        """Ambient thermal white Gaussian noise without active transmitter."""
        raw_noise = np.random.normal(0, 1.0, self.num_samples)
        return SignalSample(
            sample_id=str(uuid.uuid4())[:8],
            signal_type="NOISE_BACKGROUND",
            time_array=self.time_array,
            data=raw_noise,
            sampling_rate=self.fs,
            snr_db=0.0,
            metadata={"center_frequency": self.fs / 4.0, "bandwidth": self.fs / 2.0, "pulse_width": 0.0}
        )

    def generate_anomaly_unknown(self, snr_db: Optional[float] = None) -> SignalSample:
        """
        Unknown / Anomaly Signal: Exotic non-standard electromagnetic emission.
        Simulates: Non-linear frequency sweep with sudden phase dislocations and burst amplitude jitter.
        """
        if snr_db is None:
            snr_db = np.random.uniform(12.0, 25.0)

        f_base = np.random.uniform(3_000_000, 6_000_000)
        # Non-linear quadratic chirp modulation with periodic phase jumps
        phase = (
            2 * np.pi * (f_base * self.time_array + 1.5e9 * (self.time_array ** 2.2))
            + np.sin(2 * np.pi * 50_000 * self.time_array) * 1.8
        )
        # Chaotic burst amplitude modulation
        envelope = 0.5 * (1.0 + np.sin(2 * np.pi * 8_000 * self.time_array) ** 3)
        raw_signal = envelope * np.sin(phase)
        noisy_signal = add_awgn(raw_signal, snr_db)

        return SignalSample(
            sample_id=str(uuid.uuid4())[:8],
            signal_type="ANOMALY_UNKNOWN",
            time_array=self.time_array,
            data=noisy_signal,
            sampling_rate=self.fs,
            snr_db=snr_db,
            metadata={
                "center_frequency": f_base,
                "bandwidth": 4_000_000.0,
                "pulse_width": self.duration,
                "is_synthetic_anomaly": 1.0
            }
        )

    def generate_sample(self, signal_type: str, **kwargs) -> SignalSample:
        """Dispatches generation by signal type name."""
        generators = {
            "CW": self.generate_cw,
            "PULSED_RADAR": self.generate_pulsed_radar,
            "CHIRP_LFM": self.generate_chirp_lfm,
            "FREQ_HOPPING": self.generate_frequency_hopping,
            "NOISE_BACKGROUND": self.generate_noise,
            "ANOMALY_UNKNOWN": self.generate_anomaly_unknown
        }
        if signal_type not in generators:
            raise ValueError(f"Unknown signal type: {signal_type}. Allowed: {list(generators.keys())}")
        return generators[signal_type](**kwargs)

    def generate_random_batch(self, count: int = 15, anomaly_prob: float = 0.20) -> List[SignalSample]:
        """Generates a batch of mixed signals representing incoming spectrum traffic."""
        baseline_types = ["CW", "PULSED_RADAR", "CHIRP_LFM", "FREQ_HOPPING", "NOISE_BACKGROUND"]
        batch = []
        for _ in range(count):
            if np.random.rand() < anomaly_prob:
                stype = "ANOMALY_UNKNOWN"
            else:
                stype = np.random.choice(baseline_types)
            batch.append(self.generate_sample(stype))
        return batch
