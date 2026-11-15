"""Software fixtures only: no claim of GATE/Geant4 physics validation."""
import hashlib
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

import raw_audit as ra


def make_mhd(tmp_path, val=0.15):
    (tmp_path / 'scoring-Edep.mhd').write_text('DimSize = 1 1 1\nElementType = MET_FLOAT\nBinaryDataByteOrderMSB = False\nElementDataFile = scoring-Edep.raw\n')
    np.asarray([val], dtype='<f4').tofile(tmp_path / 'scoring-Edep.raw')


def fake_uproot(monkeypatch, entries):
    class Tree:
        def keys(self): return list(entries)
        def __getitem__(self, key): return types.SimpleNamespace(array=lambda library: np.asarray(entries[key]))
    class File:
        def __contains__(self, key): return key == 'Hits'
        def __getitem__(self, key): return Tree()
        def __enter__(self): return self
        def __exit__(self, *args): return False
    monkeypatch.setitem(sys.modules, 'uproot', types.SimpleNamespace(open=lambda path: File()))


def test_decode_process():
    assert ra.decode_process(b'phot\x00') == 'phot'
    assert ra.decode_process('compt') == 'compt'


def test_mhd_energy(tmp_path):
    make_mhd(tmp_path)
    val, files = ra.read_mhd_total(tmp_path)
    assert abs(val - .15) < 1e-7
    assert len(files) == 2


def test_mhd_path_traversal(tmp_path):
    (tmp_path / 'scoring-Edep.mhd').write_text('DimSize = 1 1 1\nElementType = MET_FLOAT\nElementDataFile = ../other.raw\n')
    with pytest.raises(ValueError, match='External'):
        ra.read_mhd_total(tmp_path)


def test_mhd_truncated_payload(tmp_path):
    (tmp_path / 'scoring-Edep.mhd').write_text('DimSize = 2 1 1\nElementType = MET_FLOAT\nElementDataFile = scoring-Edep.raw\n')
    np.asarray([1], dtype='<f4').tofile(tmp_path / 'scoring-Edep.raw')
    with pytest.raises(ValueError, match='Malformed'):
        ra.read_mhd_total(tmp_path)


def test_histogram_and_event_gating(monkeypatch, tmp_path):
    entries = {'eventID':[0,1,1,3], 'edep':[0.511,0.2,0.22,0.12], 'runID':[0,0,0,0],
               'PDGEncoding':[11,11,22,11], 'parentID':[1,1,1,1],
               'trackID':[2,2,3,2], 'processName':[b'phot',b'compt',b'phot',b'phot']}
    fake_uproot(monkeypatch, entries)
    (tmp_path / 'hits.root').write_bytes(b'fixture')
    energy, event_ids, arr, roi, branches = ra.inspect_hits(tmp_path/'hits.root',5)
    np.testing.assert_allclose(energy, [511,420,0,120,0])
    assert roi.tolist() == [1]
    assert len(branches) >= 2


def test_reject_bad_event_id(monkeypatch, tmp_path):
    fake_uproot(monkeypatch, {'eventID':[4], 'edep':[.2]})
    (tmp_path/'hits.root').write_bytes(b'fixture')
    with pytest.raises(ValueError, match='outside'):
        ra.inspect_hits(tmp_path/'hits.root', 4)


def test_reject_more_than_511(monkeypatch, tmp_path):
    fake_uproot(monkeypatch, {'eventID':[0], 'edep':[0.6]})
    (tmp_path/'hits.root').write_bytes(b'fixture')
    with pytest.raises(ValueError, match='Unphysical'):
        ra.inspect_hits(tmp_path/'hits.root', 1)


def test_per_run_raw_recheck(monkeypatch, tmp_path):
    spec = dict(id='BGO_T10_N5000_R01', seed=2026, material='BGO', thickness_mm=10, n_primaries=5)
    entries = {'eventID':[0,1,1,3], 'edep':[.511,.2,.22,.12], 'runID':[0,0,0,0],
               'PDGEncoding':[11,11,22,11], 'parentID':[1,1,1,1], 'trackID':[2,2,3,2],
               'processName':[b'phot',b'compt',b'phot',b'phot']}
    fake_uproot(monkeypatch, entries)
    (tmp_path / 'hits.root').write_bytes(b'fixture')
    (tmp_path / 'run.mac').write_text('/gate/physics/addPhysicsList emstandard_opt3\n')
    make_mhd(tmp_path, 1.051)
    np.savetxt(tmp_path / 'energy_per_primary_keV.csv', [511,420,0,120,0], header='deposited_energy_keV', comments='')
    db_hash='sample_material_hash'
    (tmp_path / 'input.json').write_text(json.dumps(dict(macro_sha256=ra.sha256(tmp_path/'run.mac'), material_db_sha256=db_hash)))
    v = dict(spec, validated=True, root_hash=ra.sha256(tmp_path/'hits.root'), macro_hash=ra.sha256(tmp_path/'run.mac'),
        dose_file_hashes={p.name:ra.sha256(p) for p in (tmp_path/'scoring-Edep.mhd',tmp_path/'scoring-Edep.raw')},
        n_interacting=3, n_near_full=1)
    (tmp_path / 'validated.json').write_text(json.dumps(v))
    summary, roi = ra.analyze_run(tmp_path, spec, db_hash)
    assert summary['n_roi'] == 1
    assert len(roi) == 1 and roi[0]['deposited_keV'] == 420
    assert roi[0]['secondary_gamma_tracks_with_crystal_hits'] == 1
    assert abs(summary['root_edep_MeV'] - 1.051) < 1e-7
    (tmp_path/'hits.root').write_bytes(b'changed')
    with pytest.raises(ValueError, match='SHA mismatch'):
        ra.analyze_run(tmp_path, spec, db_hash)


def test_refuses_inside_original_workspace(tmp_path):
    (tmp_path/'manifest.json').write_text('{}')
    with pytest.raises(ValueError,match='outside'):
        ra.run_audit(tmp_path, tmp_path/'outputs')


def test_reject_mismatching_material_db_hash(monkeypatch, tmp_path):
    """Protect provenance while accepting the actual Phase 1 input.json key."""
    spec = dict(id='BGO_T10_N5000_R01', seed=2026, material='BGO', thickness_mm=10, n_primaries=5)
    for name in ('hits.root', 'validated.json', 'run.mac', 'energy_per_primary_keV.csv'):
        (tmp_path / name).write_bytes(b'fixture')
    (tmp_path / 'input.json').write_text(json.dumps({'material_db_sha256': 'not_the_manifest_hash',
        'macro_sha256': ra.sha256(tmp_path/'run.mac')}))
    (tmp_path / 'validated.json').write_text(json.dumps({**spec, 'validated': True,
        'root_hash': ra.sha256(tmp_path/'hits.root'),
        'macro_hash': ra.sha256(tmp_path/'run.mac')}))
    with pytest.raises(ValueError, match='material DB hash mismatch'):
        ra.analyze_run(tmp_path, spec, 'actual_manifest_hash')
