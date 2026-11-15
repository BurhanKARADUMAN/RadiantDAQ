from dataclasses import replace
import numpy as np
import pytest
from radiantdaq import DetectorConfig
from radiantdaq.metrics import (simulate_pet_pair, accidental_coincidence_rate_hz,
                                 gaussian_equivalent_fwhm, energy_resolution_fraction)


def test_fwhm_equivalent():
    x=np.array([1.,2.,3.])
    assert 2.35 < gaussian_equivalent_fwhm(x) < 2.36


def test_zero_variance_energy_resolution():
    assert energy_resolution_fraction(np.ones(5)*511) == pytest.approx(0.0)


def test_accidental_coincidence_window():
    assert accidental_coincidence_rate_hz(10_000, 20_000, 2) == pytest.approx(.4)


def test_pair_reproducible():
    a=simulate_pet_pair(DetectorConfig(), 150, 10)
    b=simulate_pet_pair(DetectorConfig(), 150, 10)
    assert a.summary==b.summary
    assert np.all(np.isfinite(a.delta_t_ns[np.isfinite(a.delta_t_ns)]))


def test_higher_jitter_increases_ctr():
    cfg=DetectorConfig()
    low=simulate_pet_pair(replace(cfg, electronics_timing_sigma_ns=.01), 2500, 42)
    high=simulate_pet_pair(replace(cfg, electronics_timing_sigma_ns=.35), 2500, 42)
    assert low.summary['gaussian_equivalent_ctr_fwhm_ps'] < high.summary['gaussian_equivalent_ctr_fwhm_ps']


def test_bad_inputs_raise():
    with pytest.raises(ValueError):
        accidental_coincidence_rate_hz(-1, 1e4, 1)
    with pytest.raises(ValueError):
        simulate_pet_pair(DetectorConfig(), 20, 42, 0)
