"""Simplified, synthetic scintillation and SiPM photon-counting observables."""
from dataclasses import dataclass
import numpy as np
from .config import DetectorConfig


@dataclass
class Events:
    detected_photoelectrons: np.ndarray
    fired_microcells: np.ndarray
    apparent_photoelectrons: np.ndarray
    estimated_energy_kev: np.ndarray
    timestamp_ns: np.ndarray
    triggered: np.ndarray


def expected_detected_pe(cfg: DetectorConfig) -> float:
    return (cfg.gamma_energy_kev / 1000.0 * cfg.light_yield_ph_per_mev
            * cfg.optical_collection * cfg.photon_detection_efficiency)


def expected_fired_cells(cfg: DetectorConfig) -> float:
    # Mean-field occupancy approximation, before cross-talk and dark counts.
    mean_pe = expected_detected_pe(cfg)
    return cfg.microcells * (1.0 - np.exp(-mean_pe / cfg.microcells))


def simulate_events(cfg: DetectorConfig, n_events: int, rng: np.random.Generator) -> Events:
    cfg.validate()
    if n_events < 2:
        raise ValueError('n_events must be at least 2')
    if expected_detected_pe(cfg) <= 0:
        raise ValueError("No light can be detected: PDE and/or optical collection is zero")
    # All events are assumed to deposit the entire 511 keV in one scintillator.
    # Event-to-event collection variation mimics unresolved intrinsic contributions;
    # it is NOT a validated material model.
    event_scales = np.clip(
        rng.normal(loc=1.0, scale=cfg.intrinsic_fwhm_fraction / 2.354820045, size=n_events),
        0.2, None,
    )
    n_detected = rng.poisson(expected_detected_pe(cfg) * event_scales)

    # Finite SiPM cells: one Bernoulli trial per microcell, Poisson occupancy model.
    # Ignores temporal recharge/recovery and repeated hits within the integration window.
    hit_probability = -np.expm1(-n_detected / cfg.microcells)
    fired = rng.binomial(cfg.microcells, hit_probability)
    # Simplified single-generation cross-talk, bounded by still-available cells.
    extra_xt = np.minimum(rng.binomial(fired, cfg.optical_crosstalk_probability), cfg.microcells - fired)
    dark = rng.poisson(cfg.dark_count_rate_hz * cfg.integration_window_ns * 1e-9, n_events)
    apparent = (fired + extra_xt + dark
                + rng.normal(0.0, cfg.electronic_noise_pe_rms, n_events))
    # Illustrative single-point 511-keV calibration, not an independent energy scale.
    reference_signal = (expected_fired_cells(cfg) * (1 + cfg.optical_crosstalk_probability)
                        + cfg.dark_count_rate_hz * cfg.integration_window_ns * 1e-9)
    if reference_signal <= 0:
        raise ValueError('No light can be detected: PDE and/or optical collection is zero')
    energy_kev = cfg.gamma_energy_kev * apparent / reference_signal

    # Timing proxy: exact exponential order-statistic waiting times for the k-th
    # detected photon; then independent Gaussian SPTR and electronics jitter.
    # This is NOT a threshold-crossing time obtained from the generated waveform.
    k = cfg.trigger_photoelectrons
    triggered = n_detected >= k
    timestamp = np.full(n_events, np.nan, dtype=float)
    if np.any(triggered):
        n = n_detected[triggered]
        waiting_means = cfg.scintillation_decay_ns / (n[:, None] - np.arange(k)[None, :])
        optical_time = rng.exponential(scale=waiting_means).sum(axis=1)
        sigma = np.hypot(cfg.sipm_sptr_sigma_ns, cfg.electronics_timing_sigma_ns)
        timestamp[triggered] = optical_time + rng.normal(0.0, sigma, size=n.size)
    return Events(n_detected, fired, apparent, energy_kev, timestamp, triggered)
