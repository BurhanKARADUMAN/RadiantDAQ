"""Transparent summary statistics for synthetic events."""
from dataclasses import dataclass
import numpy as np
from .config import DetectorConfig
from .physics import simulate_events

FWHM_FROM_SIGMA = 2 * np.sqrt(2 * np.log(2))


def gaussian_equivalent_fwhm(samples: np.ndarray) -> float:
    """Gaussian-equivalent width from sample SD; NOT measured half-max histogram width."""
    arr = np.asarray(samples, dtype=float)
    if arr.size < 2 or not np.all(np.isfinite(arr)):
        raise ValueError('At least two finite values are required')
    return float(FWHM_FROM_SIGMA * np.std(arr, ddof=1))


def energy_resolution_fraction(energies_kev: np.ndarray) -> float:
    a = np.asarray(energies_kev, dtype=float)
    if a.size < 2 or not np.isfinite(a).all() or np.mean(a) <= 0:
        raise ValueError('Energy values must be finite and have a positive mean')
    return gaussian_equivalent_fwhm(a) / float(np.mean(a))


def accidental_coincidence_rate_hz(rate_a_hz: float, rate_b_hz: float, full_window_ns: float) -> float:
    """Low-occupancy approximation R_random ≈ R_A R_B W for |dt| < W/2."""
    if min(rate_a_hz, rate_b_hz, full_window_ns) < 0:
        raise ValueError('rates and width must be nonnegative')
    return rate_a_hz * rate_b_hz * full_window_ns * 1e-9


@dataclass
class PairResults:
    energy_a_kev: np.ndarray
    energy_b_kev: np.ndarray
    time_a_ns: np.ndarray
    time_b_ns: np.ndarray
    delta_t_ns: np.ndarray
    accepted: np.ndarray
    summary: dict


def simulate_pet_pair(cfg: DetectorConfig, n_events: int, seed: int, full_window_ns: float = 1.0) -> PairResults:
    cfg.validate()
    if full_window_ns <= 0:
        raise ValueError('full_window_ns must be positive')
    # Two independent detector chains; all simulated pairs are assumed true coincident
    # 511-keV full-energy interactions, so acceptance is NOT a PET system sensitivity.
    seed_sequence = np.random.SeedSequence(seed)
    ra, rb = [np.random.default_rng(s) for s in seed_sequence.spawn(2)]
    a = simulate_events(cfg, n_events, ra)
    b = simulate_events(cfg, n_events, rb)
    valid = a.triggered & b.triggered
    dt = np.full(n_events, np.nan, dtype=float)
    dt[valid] = a.timestamp_ns[valid] - b.timestamp_ns[valid]
    accepted = valid & (np.abs(dt) < full_window_ns / 2)
    if valid.sum() < 2:
        raise ValueError('Too few triggered true pairs for meaningful timing metrics')
    summary = {
        'n_generated_true_pairs': int(n_events),
        'n_triggered_true_pairs': int(valid.sum()),
        'n_accepted_true_pairs': int(accepted.sum()),
        'coincidence_window_full_ns': float(full_window_ns),
        'trigger_efficiency_given_full_deposition': float(valid.mean()),
        'window_acceptance_given_trigger': float(accepted.sum() / valid.sum()),
        'energy_resolution_a_fwhm_pct': float(100 * energy_resolution_fraction(a.estimated_energy_kev)),
        'energy_resolution_b_fwhm_pct': float(100 * energy_resolution_fraction(b.estimated_energy_kev)),
        'gaussian_equivalent_ctr_fwhm_ps': float(1000 * gaussian_equivalent_fwhm(dt[valid])),
        'mean_detected_pe_a': float(np.mean(a.detected_photoelectrons)),
        'mean_fired_cells_a': float(np.mean(a.fired_microcells)),
        'mean_energy_a_kev': float(np.mean(a.estimated_energy_kev)),
        'mean_energy_b_kev': float(np.mean(b.estimated_energy_kev)),
    }
    return PairResults(a.estimated_energy_kev, b.estimated_energy_kev,
                       a.timestamp_ns, b.timestamp_ns, dt, accepted, summary)
