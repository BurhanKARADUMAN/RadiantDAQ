from dataclasses import replace
import numpy as np
import pytest
from radiantdaq import DetectorConfig
from radiantdaq.physics import simulate_events, expected_detected_pe, expected_fired_cells


def test_pe_mean_grows_with_pde():
    c = DetectorConfig()
    assert expected_detected_pe(replace(c, photon_detection_efficiency=.4)) > expected_detected_pe(replace(c, photon_detection_efficiency=.2))


def test_saturation_is_bounded():
    c = DetectorConfig(microcells=200)
    r = simulate_events(c, 200, np.random.default_rng(42))
    assert np.all(r.fired_microcells <= c.microcells)
    assert np.all(r.fired_microcells >= 0)
    assert expected_fired_cells(c) <= c.microcells


def test_events_are_reproducible():
    c = DetectorConfig()
    a = simulate_events(c, 70, np.random.default_rng(3))
    b = simulate_events(c, 70, np.random.default_rng(3))
    np.testing.assert_array_equal(a.estimated_energy_kev, b.estimated_energy_kev)
    np.testing.assert_array_equal(a.timestamp_ns, b.timestamp_ns)


def test_monoenergetic_calibration_rough():
    c = DetectorConfig()
    r = simulate_events(c, 2000, np.random.default_rng(3))
    assert 495 < np.mean(r.estimated_energy_kev) < 525


def test_rejects_no_photodetection():
    with pytest.raises(ValueError, match='No light'):
        simulate_events(replace(DetectorConfig(), photon_detection_efficiency=0), 10, np.random.default_rng(5))
