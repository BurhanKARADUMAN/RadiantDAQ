"""Analytic statistics unit tests; invented toy counts never described as physics."""
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'phase1_2'))
from stats import wilson,aggregate,contrasts

def test_wilson_edges():
    a,b=wilson(0,100)
    assert a==0 and b>0
    a,b=wilson(100,100)
    assert a<1 and b==1
    with pytest.raises(ValueError):wilson(101,100)

def test_aggregate_and_difference():
    rows=[]
    for m,n in [('BGO',70),('LSO',45)]:
        for seed in (1,2):
            rows.append(dict(material=m,thickness_mm=20,variant='baseline',replicate=seed,
                             n_primaries=100,n_interaction=n,n_nearfull=n-10,n_400_440=5))
    pooled=aggregate(rows)
    assert len(pooled)==2
    assert pooled[0]['n_primaries']==200
    diffs=contrasts(pooled)
    assert len(diffs)==3
    assert next(d['BGO_minus_LSO_pp'] for d in diffs if d['metric']=='interaction')==pytest.approx(25)


def test_smoke_bgo_only_writes_header_only_contrast(tmp_path):
    import csv
    from stats import write_analysis, CONTRAST_COLUMNS
    rows = [dict(material='BGO', thickness_mm=20, variant=variant, replicate=1,
                 n_primaries=200, n_interaction=110, n_nearfull=70, n_400_440=2)
            for variant in ('baseline', 'fluo_off')]
    pooled, differences = write_analysis(rows, tmp_path)
    assert len(pooled) == 2
    assert differences == []
    with (tmp_path / 'material_differences.csv').open(newline='') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == CONTRAST_COLUMNS
        assert list(reader) == []
    text = (tmp_path / 'STATISTICAL_INTERPRETATION.md').read_text()
    assert 'Observed replicate counts per condition: [1]' in text
    assert 'header-only' in text
