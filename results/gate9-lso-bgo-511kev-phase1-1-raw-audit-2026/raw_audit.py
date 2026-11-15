#!/usr/bin/env python3
"""RadiantDAQ Phase 1.1: independently audit unmodified GATE 9.4 RAW/ROOT results.

Safe: read-only campaign files, outputs only into a separate fresh directory.
The audit probes track-level *hit evidence*, NOT world-boundary escapes or creator processes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

SOURCE_KEV = 511.0
ROI_LO, ROI_HI = 400.0, 440.0


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_csv(path, records, columns):
    with path.open('w', newline='', encoding='utf-8') as f:
        out = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        out.writeheader()
        out.writerows(records)


def decode_process(x):
    if isinstance(x, (bytes, np.bytes_)):
        return bytes(x).decode('utf-8', errors='replace').rstrip('\x00')
    return str(x).rstrip('\x00')


def read_mhd_total(run):
    candidates = list(run.glob('*Edep.mhd'))
    if len(candidates) != 1:
        raise ValueError(f'{run}: expected exactly one *Edep.mhd; found {len(candidates)}')
    mhd = candidates[0]
    meta = dict(x.strip().split('=', 1) for x in mhd.read_text(errors='replace').splitlines() if '=' in x)
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    if meta.get('CompressedData', 'False').lower() in ('true', '1'):
        raise ValueError('Compressed MetaImage not supported')
    dims = [int(d) for d in meta['DimSize'].split()]
    if not dims or min(dims) <= 0:
        raise ValueError('Invalid MetaImage dimensions')
    formats = {'MET_FLOAT': 'f4', 'MET_DOUBLE': 'f8', 'MET_INT': 'i4', 'MET_SHORT': 'i2'}
    if meta.get('ElementType') not in formats:
        raise ValueError('Unsupported MetaImage ElementType')
    # Resolve only within the run directory; never follow external payload paths.
    payload = meta['ElementDataFile']
    if payload == 'LOCAL' or Path(payload).name != payload:
        raise ValueError('External/LOCAL MetaImage payload not supported')
    raw = run / payload
    byte_order = '>' if meta.get('BinaryDataByteOrderMSB', 'False').lower() == 'true' else '<'
    arr = np.fromfile(raw, dtype=byte_order + formats[meta['ElementType']])
    if arr.size != math.prod(dims) or not np.all(np.isfinite(arr)) or np.any(arr < -1e-8):
        raise ValueError('Malformed or unphysical DoseActor payload')
    return float(arr.sum(dtype=np.float64)), (mhd, raw)


def inspect_hits(root_path, n):
    import uproot  # on WSL: python -m pip install -r requirements.txt
    with uproot.open(root_path) as f:
        if 'Hits' not in f:
            raise ValueError(f'{root_path}: ROOT tree Hits missing')
        tree = f['Hits']
        available = set(tree.keys())
        if not {'eventID', 'edep'}.issubset(available):
            raise ValueError('ROOT Hits lacks eventID or edep')
        fields = ['eventID', 'edep'] + [k for k in ('runID', 'PDGEncoding', 'trackID', 'parentID', 'processName') if k in available]
        arrays = {k: tree[k].array(library='np') for k in fields}
        event_ids = np.asarray(arrays['eventID'], dtype=np.int64)
        steps = np.asarray(arrays['edep'], dtype=np.float64)
        if not len(event_ids) or len(event_ids) != len(steps):
            raise ValueError('ROOT Hits empty/mismatched')
        if np.any(event_ids < 0) or np.any(event_ids >= n):
            raise ValueError('ROOT eventID outside [0,n)')
        if not np.all(np.isfinite(steps)) or np.any(steps < -1e-9):
            raise ValueError('ROOT contains invalid step energies')
        if 'runID' in arrays and len(np.unique(arrays['runID'])) != 1:
            raise ValueError('Multiple runID values; eventID might restart')
        energy = np.bincount(event_ids, weights=steps, minlength=n) * 1000.0
        if np.any(energy < -1e-6) or np.any(energy > SOURCE_KEV + 0.1):
            raise ValueError('Unphysical per-event crystal energy; investigate event bookkeeping')
        roi_ids = np.flatnonzero((energy >= ROI_LO) & (energy <= ROI_HI))
        return energy, event_ids, arrays, roi_ids, sorted(available)


def analyze_run(run, spec, materials_hash):
    required = ('hits.root', 'validated.json', 'run.mac', 'input.json', 'energy_per_primary_keV.csv')
    for name in required:
        if not (run / name).is_file():
            raise FileNotFoundError(f'{run}: missing {name}')
    v = load_json(run / 'validated.json')
    inputs = load_json(run / 'input.json')
    n = int(spec['n_primaries'])
    if not v.get('validated') or any(v.get(k) != spec[k] for k in ('id', 'seed', 'material', 'thickness_mm', 'n_primaries')):
        raise ValueError(f'{run}: inconsistent metadata / validation')
    if sha256(run / 'hits.root') != v.get('root_hash'):
        raise ValueError(f'{run}: original ROOT SHA mismatch')
    if sha256(run / 'run.mac') != v.get('macro_hash') or sha256(run / 'run.mac') != inputs.get('macro_sha256'):
        raise ValueError(f'{run}: original macro SHA mismatch')
    if inputs.get('material_db_sha256') != materials_hash:
        raise ValueError(f'{run}: material DB hash mismatch with campaign manifest')
    energy, event_ids, arr, roi_ids, branches = inspect_hits(run / 'hits.root', n)
    exported = np.loadtxt(run / 'energy_per_primary_keV.csv', delimiter=',', skiprows=1)
    if exported.shape != (n,) or not np.allclose(energy, exported, rtol=0, atol=0.0001):
        raise ValueError(f'{run}: regenerated event energies differ from exported CSV')
    dose_mev, (mhd, raw) = read_mhd_total(run)
    hashes = v.get('dose_file_hashes', {})
    for p in (mhd, raw):
        if hashes.get(p.name) != sha256(p):
            raise ValueError(f'{run}: DoseActor file hash mismatch: {p.name}')
    root_mev = float(energy.sum(dtype=np.float64) / 1000.0)
    tol_mev = max(0.0005, 0.0001 * abs(root_mev))
    if abs(root_mev - dose_mev) > tol_mev:
        raise ValueError(f'{run}: ROOT-DoseActor mismatch')
    if int(np.count_nonzero(energy > 1e-6)) != int(v['n_interacting']) or int(np.count_nonzero((energy >= 490) & (energy <= 520))) != int(v['n_near_full']):
        raise ValueError(f'{run}: event counts differ from validated.json')
    roi_mask = np.zeros(n, dtype=bool)
    roi_mask[roi_ids] = True
    relevant_steps = roi_mask[event_ids]
    step_labels = np.array([decode_process(k) for k in arr['processName']], dtype=object) if 'processName' in arr else None
    pdg = np.asarray(arr['PDGEncoding']) if 'PDGEncoding' in arr else None
    parent = np.asarray(arr['parentID']) if 'parentID' in arr else None
    track = np.asarray(arr['trackID']) if 'trackID' in arr else None
    all_labels = Counter(step_labels.tolist()) if step_labels is not None else Counter()
    roi_labels = Counter(step_labels[relevant_steps].tolist()) if step_labels is not None else Counter()
    events = []
    for ev in roi_ids:
        mask = event_ids == ev
        pset = sorted(set(step_labels[mask].tolist())) if step_labels is not None else []
        sec_gamma = int(np.count_nonzero((pdg[mask] == 22) & (parent[mask] > 0))) if pdg is not None and parent is not None else None
        sec_gamma_unique = len(set(zip(track[mask][(pdg[mask] == 22) & (parent[mask] > 0)].tolist(), parent[mask][(pdg[mask] == 22) & (parent[mask] > 0)].tolist()))) if sec_gamma is not None and track is not None else None
        events.append({
            'run_id': spec['id'], 'material': spec['material'], 'thickness_mm': spec['thickness_mm'],
            'seed': spec['seed'], 'event_id': int(ev), 'deposited_keV': round(float(energy[ev]), 7),
            'deficit_keV': round(float(SOURCE_KEV-energy[ev]), 7),
            'hit_steps': int(np.count_nonzero(mask)),
            'gamma_hit_steps': int(np.count_nonzero(pdg[mask] == 22)) if pdg is not None else '',
            'secondary_gamma_hit_steps': sec_gamma if sec_gamma is not None else '',
            'secondary_gamma_tracks_with_crystal_hits': sec_gamma_unique if sec_gamma_unique is not None else '',
            'hit_step_process_labels': ';'.join(pset)
        })
    summary = dict(
        run_id=spec['id'], material=spec['material'], thickness_mm=spec['thickness_mm'],
        n_primaries=n, seed=spec['seed'], root_hits=len(event_ids),
        n_roi=len(roi_ids), n_interacting=int(np.count_nonzero(energy > 1e-6)),
        n_near_full=int(np.count_nonzero((energy >= 490) & (energy <= 520))),
        root_edep_MeV=round(root_mev, 10), dose_edep_MeV=round(dose_mev, 10),
        abs_root_dose_difference_MeV=round(abs(root_mev-dose_mev), 10),
        max_energy_keV=round(float(np.max(energy)), 8),
        root_sha256=sha256(run / 'hits.root'),
        has_processName=int('processName' in arr),
        has_particle_genealogy=int({'parentID', 'trackID', 'PDGEncoding'}.issubset(arr)),
        all_hit_step_processes=dict(sorted(all_labels.items())),
        roi_hit_step_processes=dict(sorted(roi_labels.items())),
        branches=branches,
    )
    return summary, events


def run_audit(workspace, output):
    workspace, output = workspace.resolve(), output.resolve()
    if output == workspace or workspace in output.parents:
        raise ValueError('Output must be outside the original campaign workspace')
    if output.exists():
        raise FileExistsError(f'Refusing to modify existing output: {output}; choose a new directory')
    manifest = load_json(workspace / 'manifest.json')
    if manifest.get('n_runs') != 18 or len(manifest.get('runs', [])) != 18:
        raise ValueError('Expected the existing 18-run Phase 1 campaign')
    orig_hash = manifest['materials_sha256']
    db = Path(manifest['material_db'])
    if not db.exists() or sha256(db) != orig_hash:
        raise ValueError('Local GateMaterials.db absent or changed from campaign manifest')
    specs = manifest['runs']
    seeds = [s['seed'] for s in specs]
    if len(set(seeds)) != len(seeds):
        raise ValueError('Duplicate seed detected')
    summaries, roi = [], []
    # Do not create an output folder until ALL 18 inputs independently pass.
    for i, spec in enumerate(specs, start=1):
        print(f'[AUDIT {i}/18] {spec["id"]}', flush=True)
        s, events = analyze_run(workspace / 'runs' / spec['id'], spec, orig_hash)
        summaries.append(s)
        roi.extend(events)
    output.mkdir(parents=True, exist_ok=False)
    summ_cols = ['run_id', 'material', 'thickness_mm', 'n_primaries', 'seed', 'root_hits', 'n_roi', 'n_interacting', 'n_near_full', 'root_edep_MeV', 'dose_edep_MeV', 'abs_root_dose_difference_MeV', 'max_energy_keV', 'root_sha256', 'has_processName', 'has_particle_genealogy']
    event_cols = ['run_id', 'material', 'thickness_mm', 'seed', 'event_id', 'deposited_keV', 'deficit_keV', 'hit_steps', 'gamma_hit_steps', 'secondary_gamma_hit_steps', 'secondary_gamma_tracks_with_crystal_hits', 'hit_step_process_labels']
    write_csv(output / 'raw_run_audit.csv', summaries, summ_cols)
    write_csv(output / 'roi_400_440_events.csv', roi, event_cols)
    histogram = []
    for m in ('BGO', 'LSO'):
        es = np.array([r['deposited_keV'] for r in roi if r['material'] == m])
        for left in range(400, 440):
            histogram.append(dict(material=m, bin_low_keV=left, bin_high_keV=left+1,
                                  count=int(np.count_nonzero((es >= left) & (es < left+1)))))
    write_csv(output / 'roi_histogram_1kev.csv', histogram, ['material', 'bin_low_keV', 'bin_high_keV', 'count'])
    result = dict(status='independently_rechecked_raw_files', n_runs=len(summaries),
                  n_primaries=sum(s['n_primaries'] for s in summaries), roi_events_by_material={m:sum(s['n_roi'] for s in summaries if s['material']==m) for m in ('BGO', 'LSO')},
                  max_root_dose_diff_MeV=max(s['abs_root_dose_difference_MeV'] for s in summaries),
                  materials_db_sha256=orig_hash,
                  evidence_note='Hit steps and secondary gamma crystal-hit tracks do not establish actual escape or atomic deexcitation origin.',
                  raw_root_files_published=False, observations=summaries)
    (output / 'audit_manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    report = f'''# RadiantDAQ Phase 1.1 — Independent raw-data audit\n\n**Status:** 18 original ROOT Hits and DoseActor RAW files were re-read and checked locally.\n\n**Primaries:** {result['n_primaries']:,} in {len(summaries)} runs; 511-keV gamma, 3 x 3 mm LSO/BGO crystals.\n\n**ROI 400–440 keV:** BGO {result['roi_events_by_material']['BGO']}, LSO {result['roi_events_by_material']['LSO']}.\n\n**ROOT vs DoseActor:** all runs passed the documented absolute/relative energy-sum tolerance; max absolute discrepancy {result['max_root_dose_diff_MeV']:.8g} MeV.\n\n**Material database SHA-256:** `{orig_hash}`. All original ROOT, macro, MHD and RAW hashes agree with the 2026 campaign validation records.\n\n## Interpretation\n\nGATE ROOT `Hits` records are crystal energy-deposition *steps*. `processName`, `parentID` and `trackID` identify step labels and some genealogy *inside the scored volume*, not the definitive origin of a secondary or its crossing out of the crystal. An observed 400–440 keV deposited-energy feature is **compatible with** energy escape, but cannot be classified as characteristic X-ray escape without creator-process, initial secondary energy and boundary-crossing records. The `511 - Edep` deficit is not a detected escaped-photon energy.\n\n## Remaining work\n\n- Enable track/stepping instrumentation, creator process and boundary-crossing scoring in a **new** diagnostic experiment; preserve the 90k campaign.\n- Compare relevant material fluorescence energies and Geant4 atomic deexcitation settings.\n- Vary cuts and EM physics lists separately from seed uncertainty; no systematic uncertainty is claimed here.\n- No optical photons, SiPM response, measured energy resolution or coincidence time resolution are included.\n\n## Output files\n\n- `raw_run_audit.csv`: per-run independent checks\n- `roi_400_440_events.csv`: per-event exploratory hit evidence\n- `roi_histogram_1kev.csv`: deposited-energy distribution\n- `audit_manifest.json`: complete evidence/provenance record\n'''
    (output / 'RAW_AUDIT_REPORT.md').write_text(report, encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'observations'}, indent=2))
    print(f'Output: {output}')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    run_audit(a.workspace, a.output)


if __name__ == '__main__':
    main()
