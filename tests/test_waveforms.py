import numpy as np
import pytest
from radiantdaq import DetectorConfig
from radiantdaq.waveforms import leading_edge_crossing, simulate_waveform


def test_interpolated_crossing():
    assert leading_edge_crossing(np.array([0,1,2.]), np.array([0,2,0.]), 1) == pytest.approx(.5)


def test_no_crossing():
    assert leading_edge_crossing(np.array([0,1.]), np.array([0,0.]), 1) is None


def test_reject_bad_grid():
    with pytest.raises(ValueError):
        leading_edge_crossing(np.array([0,0.]), np.array([0,1.]), .5)


def test_waveform_generation():
    x=simulate_waveform(DetectorConfig(), np.random.default_rng(123))
    assert len(x.time_ns)==len(x.clean_mv)==len(x.noisy_mv)
    assert np.max(x.noisy_mv)>0
    assert x.crossing_ns is not None
    assert 0 < x.crossing_ns < 150
