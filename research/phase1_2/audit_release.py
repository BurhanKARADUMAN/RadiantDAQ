#!/usr/bin/env python3
"""Independent, read-only stdlib check of public Phase 1.2 CSV/JSON payloads.

Does not run GATE or read native ROOT. No mutation of simulation records.
"""
import csv
import hashlib
import json
from pathlib import Path
from collections import Counter
from math import isclose

ROOT=Path(__file__).resolve().parent

def csv_rows(relative):
    with (ROOT/relative).open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))

def check():
    control=json.loads((ROOT/'data/fluorescence_control/SUMMARY.json').read_text())
    assert control['status']=='VALIDATED'
    expected={('OFF',8457101):0,('ON',8457101):166,('OFF',8457202):0,('ON',8457202):161}
    got={'OFF':0,'ON':0}
    near={'OFF':0,'ON':0}
    for (condition,seed),roi_expected in expected.items():
        p=f'data/fluorescence_control/energy_per_primary/{condition}_seed{seed}.csv'
        rows=csv_rows(p)
        assert len(rows)==10000, (p,len(rows))
        assert [int(x['eventID']) for x in rows]==list(range(10000)),p
        energies=[float(x['deposited_energy_keV']) for x in rows]
        assert all(0 <= e <= 511.0001 for e in energies),p
        roi=sum(400<=e<=440 for e in energies)
        nfull=sum(490<=e<=520 for e in energies)
        assert roi == roi_expected,(p,roi,roi_expected)
        got[condition]+=roi
        near[condition]+=nfull
    assert got=={'ON':327,'OFF':0},got
    assert near=={'ON':10216,'OFF':10433},near
    for c in ('ON','OFF'):
        t=control['results'][c]
        assert t['histories']==20000 and t['roi_400_440']==got[c]
        assert t['nearfull_490_520']==near[c]
    events=csv_rows('data/track_evidence/ROI_event_linkage.csv')
    tracks=csv_rows('data/track_evidence/ROI_outgoing_gamma_tracks.csv')
    summary=json.loads((ROOT/'data/track_evidence/independent_audit_summary.json').read_text())
    assert len(events)==len(tracks)==327
    assert summary['N_events']==327 and summary['N_created_track_matches']==327
    assert summary['process_counts']=={'phot':324,'compt':3}
    assert max(abs(float(x['energy_minus_Edep_minus_sum_gamma_keV_assumed'])) for x in events)<0.0001
    assert len({(r['seed'],r['eventID']) for r in events})==327
    assert all(int(r['created_track_matched'])==1 for r in tracks)
    processes=Counter(r['creator_process'] for r in tracks)
    assert processes=={'phot':324,'compt':3},processes
    assert all(r['production_volume']=='crystal_log' for r in tracks)
    return {'status':'PASS','control_roi':got,'control_nearfull':near,'roi_event_links':len(events),'process_counts':dict(processes),'limitations':'derived CSV/JSON audit only, no native ROOT'}
if __name__=='__main__': print(json.dumps(check(),indent=2,ensure_ascii=False))
