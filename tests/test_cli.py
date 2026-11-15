import json
from radiantdaq.cli import do_demo, do_sweep
from radiantdaq.config import DetectorConfig


def test_demo_files(tmp_path):
    data=do_demo(tmp_path, 80, 100, DetectorConfig(), 1.0)
    for name in ['summary.json','event_level_synthetic.csv','sample_waveform.csv','01_sipm_waveform.png','02_energy_response.png','03_timing_difference.png']:
        assert (tmp_path / name).exists()
    assert data['provenance'].startswith('SYNTHETIC')
    assert json.loads((tmp_path / 'summary.json').read_text())['seed']==100


def test_sweep_files(tmp_path):
    x=do_sweep(tmp_path, 60, 200, DetectorConfig())
    assert len(x)==8
    assert (tmp_path / 'synthetic_parameter_sweep.csv').is_file()
    assert (tmp_path / '04_parameter_sensitivity.png').is_file()
