"""Unit tests for macro generation and plan correctness. NOT GATE execution."""
from pathlib import Path
import sys
import re
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'phase1_2'))
from campaign import create_macro,cases_for,VARIANTS

base=(ROOT/'pilot_macros/BGO_T20_pilot_original.mac').read_text()

@pytest.mark.parametrize('v',VARIANTS)
def test_all_cases_one_seed_and_actor(v):
    macro=create_macro(base,v,8300001,300,'/tmp/GateMaterials.db')
    assert '/gate/random/setEngineSeed 8300001' in macro
    assert '300 gamma histories, independent seed 8300001' in macro
    assert '/gate/application/setTotalNumberOfPrimaries 300' in macro
    assert macro.count('/gate/actor/addActor PhaseSpaceActor')==2
    assert 'storeOutgoingParticles true' in macro
    assert 'storeSecondaries true' in macro
    assert macro.count('/gate/run/initialize')==1
    assert macro.count('/gate/physics/addPhysicsList')==1
    assert macro.count('/gate/crystal/attachCrystalSDnoSystem')==1
    if v=='fluo_off': assert '/process/em/fluo false' in macro
    if v=='cut_0p05mm':assert '/gate/physics/Gamma/SetCutInRegion crystal 0.05 mm' in macro
    if v=='tilt_2deg':assert '/gps/direction 0.034899496703 0. 0.999390827019' in macro


def test_full_independent_seeds():
    cases=cases_for('full',5000)
    assert len(cases)==36
    assert len({c['seed'] for c in cases})==len(cases)
    assert sum(c['n_primaries'] for c in cases)==180000
    assert {c['material'] for c in cases}=={'BGO','LSO'}


def test_smoke_two_runs():
    cases=cases_for('smoke',200)
    assert len(cases)==2
    assert [c['variant'] for c in cases]==['baseline','fluo_off']


def test_fail_closed_anchors():
    with pytest.raises(ValueError,match='seed'):
        create_macro(re.sub(r'^/gate/random/setEngineSeed.*$', '', base, flags=re.MULTILINE), 'baseline', 1, 100, 'x')
    with pytest.raises(ValueError,match='physics'):
        create_macro(base.replace('emstandard_opt3','emstandard'), 'emopt4', 1, 100, 'x')


def test_metaimage_total_and_hash(tmp_path):
    import numpy as np
    from campaign import read_doseactor_total
    data=np.array([0.1,0.2,0.3,0.4],dtype='<f4')
    data.tofile(tmp_path/'scoring-Edep.raw')
    (tmp_path/'scoring-Edep.mhd').write_text(
        'ObjectType = Image\nNDims = 3\nDimSize = 2 2 1\n'
        'ElementType = MET_FLOAT\nElementDataFile = scoring-Edep.raw\n')
    total,hashes=read_doseactor_total(tmp_path)
    assert total==pytest.approx(1.0,abs=1e-7)
    assert len(hashes)==2
