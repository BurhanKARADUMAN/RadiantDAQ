#!/usr/bin/env python3
"""Conservative event-linked outgoing-photon evidence from GATE 9 phase space.

Only reports candidate correlations when EventID + particle name + kinetic energy are present.
Do not equate a 511 keV deficit with the escaped photon energy; full accounting needs all tracks.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np


def _pick(names,needles):
    for term in needles:
        x=[n for n in names if n.lower().replace('_','')==term]
        if len(x)==1:return x[0]
    return None


def audit(root_path:Path, energy_path:Path, dest:Path):
    import uproot
    if dest.exists():raise FileExistsError(dest)
    from_root=np.loadtxt(energy_path,delimiter=',',skiprows=1)
    roi=np.flatnonzero((from_root>=400)&(from_root<=440))
    with uproot.open(root_path) as root:
        trees=[x for x in root.values() if hasattr(x,'num_entries')]
        if not trees:raise ValueError('No phase-space tree')
        tree=trees[0]; keys=list(tree.keys())
        ev=_pick(keys,['eventid','event']);particle=_pick(keys,['particlename','particle']);
        kinetic=_pick(keys,['ekine','kineticenergy']);process=_pick(keys,['productionprocess','trackcreatorprocess'])
        result=dict(root=str(root_path),branches=keys,entries=int(tree.num_entries),
                    roi_events=int(len(roi)),can_correlate=bool(ev and particle and kinetic),
                    caveat='Particle escape scoring only; creator/process and unit interpretation require Gate9 branch schema inspection.')
        if not result['can_correlate']:
            dest.write_text(json.dumps(result,indent=2)+'\n')
            return result
        evs=tree[ev].array(library='np'); ps=tree[particle].array(library='np')
        es=tree[kinetic].array(library='np')
        if len(evs)!=len(ps) or len(evs)!=len(es):raise ValueError('Inconsistent phase-space tree lengths')
        gamma_mask=np.array([(p.decode(errors='replace') if isinstance(p,bytes) else str(p)).strip().lower() in ('gamma','photon') for p in ps])
        roi_mask=np.isin(evs,roi)
        result['outgoing_gamma_rows']=int(gamma_mask.sum())
        result['roi_events_with_outgoing_gamma']=int(len(set(evs[gamma_mask & roi_mask].tolist())))
        result['outgoing_gamma_rows_from_roi_events']=int(np.count_nonzero(gamma_mask & roi_mask))
        result['roi_event_ids_with_outgoing_gamma']=sorted(set(int(z) for z in evs[gamma_mask & roi_mask]))[:1000]
        # Do NOT rescale photon kinetic energy without verifying native GATE branch units.
        data=es[gamma_mask & roi_mask]
        result['outgoing_gamma_energy_min_NATIVE_UNITS']=float(np.min(data)) if len(data) else None
        result['outgoing_gamma_energy_max_NATIVE_UNITS']=float(np.max(data)) if len(data) else None
        result['production_process_branch']=process
        if process:
            labels=tree[process].array(library='np')[gamma_mask & roi_mask]
            clean=[a.decode(errors='replace') if isinstance(a,bytes) else str(a) for a in labels]
            result['roi_outgoing_gamma_production_process_counts']={k:clean.count(k) for k in sorted(set(clean))}
        dest.write_text(json.dumps(result,indent=2)+'\n')
        return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--outgoing-root',required=True,type=Path)
    p.add_argument('--energy-csv',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();print(json.dumps(audit(a.outgoing_root,a.energy_csv,a.output),indent=2))

if __name__=='__main__':main()
