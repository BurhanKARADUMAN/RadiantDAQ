"""Mathematical checks with fictitious test numbers; no material claims."""
import math
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'phase1_2'))
from xcom_sanity import probability,run

def test_exponential():
    assert probability(1,1,10)==pytest.approx(1-math.exp(-1))
    assert probability(1,1,20)>probability(1,1,10)
    with pytest.raises(ValueError):probability('TBD',1,1)

def test_requires_reference():
    with pytest.raises(ValueError):
        run({'materials':{'BGO':{'mass_attenuation_cm2_g':1,'density_g_cm3':1,
                                 'thickness_mm':20,'source_url':'TBD'}}})
