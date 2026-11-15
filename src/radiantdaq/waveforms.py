"""Illustrative analog pulse shaping and sample-grid threshold crossing."""
from dataclasses import dataclass
import numpy as np
from .config import DetectorConfig
from .physics import expected_detected_pe


@dataclass
class Waveform:
    time_ns: np.ndarray
    clean_mv: np.ndarray
    noisy_mv: np.ndarray
    threshold_mv: float
    crossing_ns: float | None
    num_photoelectrons: int


def leading_edge_crossing(t: np.ndarray, v: np.ndarray, threshold_mv: float) -> float | None:
    """Linear interpolation of first upward threshold crossing, in ns."""
    if len(t) != len(v) or len(t) < 2 or not np.all(np.diff(t) > 0):
        raise ValueError('time and voltage must have equal lengths with strictly increasing time')
    indices = np.flatnonzero((v[:-1] < threshold_mv) & (v[1:] >= threshold_mv))
    if len(indices) == 0:
        return None
    i = int(indices[0])
    dy = v[i + 1] - v[i]
    return float(t[i] + (t[i + 1] - t[i]) * (threshold_mv - v[i]) / dy)


def simulate_waveform(cfg: DetectorConfig, rng: np.random.Generator) -> Waveform:
    cfg.validate()
    dt = cfg.adc_sampling_ns
    time = np.arange(0, cfg.pulse_window_ns, dt)
    n_pe = int(rng.poisson(expected_detected_pe(cfg)))
    photon_times = cfg.waveform_start_ns + rng.exponential(cfg.scintillation_decay_ns, size=n_pe)
    n_dark = int(rng.poisson(cfg.dark_count_rate_hz * cfg.pulse_window_ns * 1e-9))
    if n_dark:
        photon_times = np.concatenate([photon_times, rng.uniform(0, cfg.pulse_window_ns, n_dark)])
    counts, _ = np.histogram(photon_times, bins=np.arange(len(time) + 1) * dt)
    kernel_t = np.arange(0, min(6 * cfg.waveform_fall_ns, cfg.pulse_window_ns), dt)
    # Per-photon phenomenological single-PE analog impulse, not an RC/SiPM equivalent circuit.
    kernel = (1 - np.exp(-kernel_t / cfg.waveform_rise_ns)) * np.exp(-kernel_t / cfg.waveform_fall_ns)
    clean = np.convolve(counts, kernel, mode='full')[:len(time)] * cfg.waveform_single_pe_mv
    noisy = clean + rng.normal(0, cfg.waveform_noise_mv_rms, size=len(time))
    crossing = leading_edge_crossing(time, noisy, cfg.threshold_mv)
    return Waveform(time, clean, noisy, cfg.threshold_mv, crossing, n_pe)
