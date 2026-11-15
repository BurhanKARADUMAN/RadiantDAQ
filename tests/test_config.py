from dataclasses import replace
import pytest
from radiantdaq.config import DetectorConfig


def test_default_cfg_valid():
    assert DetectorConfig().validate().microcells > 0


@pytest.mark.parametrize('field,val', [
    ('photon_detection_efficiency', -0.1),
    ('optical_collection', 1.1),
    ('microcells', 0),
    ('trigger_photoelectrons', 0),
    ('gamma_energy_kev', 0),
    ('scintillation_decay_ns', -4),
])
def test_rejects_nonphysical(field, val):
    with pytest.raises(ValueError):
        replace(DetectorConfig(), **{field: val}).validate()
