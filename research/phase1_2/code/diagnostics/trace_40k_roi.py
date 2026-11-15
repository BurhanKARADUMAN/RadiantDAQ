#!/usr/bin/env python3
"""Read-only 40k fluorescence ON ROI/phase-space event-linkage audit.

Input: the user's *original* GATE ROOT files in the 40k recovered-v3 study.
Output: a *fresh separate directory* of small derived CSV and JSON files.
No simulation, no modification to existing data. Requires numpy and uproot.

Important: a returned gamma of 60-110 keV, even linked to a created track,
does not alone prove an atomic Bi K X-ray. Production labels and boundary
geometry plus full energy flow must be assessed separately. Native Ekine units
MUST be confirmed (MeV is a working assumption below).
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from phase_space_roi_join import read_tree, photon, textval


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(2 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def check_within(path: Path, parent: Path) -> None:
    if not path.is_relative_to(parent):
        raise ValueError(f'Unexpected path outside study workspace: {path}')


def collect(args) -> None:
    work = args.workspace.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not work.is_dir() or not (work / 'manifest.json').is_file():
        raise FileNotFoundError(f'Invalid study workspace: {work}')
    if output == work or output.is_relative_to(work) or work.is_relative_to(output):
        raise ValueError('Output must be outside the original study workspace')
    if output.exists():
        raise FileExistsError(f'Output exists; choose a new --output folder: {output}')
    manifest = json.loads((work / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('status') != 'VALIDATED':
        raise ValueError('Source study manifest must have status VALIDATED')
    on_cases = [r for r in manifest['runs'] if r['condition'] == 'ON']
    if len(on_cases) != 2 or sorted(r['seed'] for r in on_cases) != [8457101, 8457202]:
        raise ValueError('Unexpected source ON runs')
    conv = {'MeV': 1000.0, 'keV': 1.0}[args.ekine_unit]

    events_out = []
    photons_out = []
    run_summaries = []
    for r in sorted(on_cases, key=lambda r: r['seed']):
        case = Path(r['path']).expanduser().resolve()
        check_within(case, work)
        seed = int(r['seed'])
        if r['status'] != 'VALIDATED' or r['crystal_flags_at_transport'] != [[1, 1, 1], [1, 1, 1]]:
            raise ValueError(f'Unvalidated or incorrect crystal flags: seed={seed}')
        energies_file = Path(r['energy_csv_path']).expanduser().resolve()
        check_within(energies_file, work)
        if digest(energies_file) != r['energy_csv_sha256']:
            raise ValueError(f'CSV SHA256 mismatch: {energies_file}')
        with energies_file.open('r', encoding='utf-8', newline='') as f:
            erows = list(csv.DictReader(f))
        ids = np.asarray([int(e['eventID']) for e in erows])
        energies = np.asarray([float(e['deposited_energy_keV']) for e in erows])
        if len(energies) != 10000 or not np.array_equal(ids, np.arange(10000)) or not np.all(np.isfinite(energies)):
            raise ValueError(f'Invalid 10k event energy CSV: seed={seed}')
        roi_ids = set(np.flatnonzero((energies >= 400) & (energies <= 440)).tolist())
        if len(roi_ids) != r['roi_400_440']:
            raise ValueError(f'ROI mismatch in source manifest: seed={seed}')
        print(f'[SEED {seed}] {len(roi_ids)} ROI events; reading GATE native ROOT (read-only)', flush=True)
        outgoing_root = case / 'outgoing.root'
        created_root = case / 'created.root'
        for nm, p in [('outgoing.root', outgoing_root), ('created.root', created_root)]:
            if digest(p) != r['phase_space'][nm]['sha256']:
                raise ValueError(f'Native ROOT SHA256 mismatch: {p}')
        outgoing = read_tree(outgoing_root)
        created = read_tree(created_root)
        for label, a in [('outgoing', outgoing), ('created', created)]:
            ev = a['EventID']
            if np.any(ev < 0) or np.any(ev >= 10000):
                raise ValueError(f'{seed} {label}: out-of-range EventID')
        made_gamma = {}
        for j in range(len(created['EventID'])):
            if photon(created['ParticleName'][j]):
                key = (int(created['RunID'][j]), int(created['EventID'][j]), int(created['TrackID'][j]))
                made_gamma[key] = j

        grouped = defaultdict(list)
        secondary_photons = 0
        creator_label_available = 0
        for j in range(len(outgoing['EventID'])):
            ev = int(outgoing['EventID'][j])
            if ev not in roi_ids:
                continue
            isgamma = photon(outgoing['ParticleName'][j])
            raw_energy = float(outgoing['Ekine'][j]) * conv
            if not np.isfinite(raw_energy) or raw_energy < 0:
                raise ValueError(f'Invalid outgoing kinetic energy at event={ev}')
            row = {
                'condition': 'ON', 'seed': seed, 'eventID': ev,
                'runID': int(outgoing['RunID'][j]), 'trackID': int(outgoing['TrackID'][j]),
                'parentID': int(outgoing['ParentID'][j]),
                'particle': textval(outgoing['ParticleName'][j]),
                'outgoing_Ekine_keV_assumed': raw_energy,
                'deposited_energy_keV': float(energies[ev]),
                'is_gamma': int(isgamma),
            }
            grouped[ev].append(row)
            if not isgamma:
                continue
            key = (row['runID'], ev, row['trackID'])
            made_idx = made_gamma.get(key)
            out_label_available = bool(outgoing['_creator_process_recorded'][j])
            creation_label_available = bool(made_idx is not None and created['_creator_process_recorded'][made_idx])
            process_label = (
                textval(outgoing['CreatorProcess'][j]) if out_label_available else
                textval(created['CreatorProcess'][made_idx]) if creation_label_available else ''
            )
            secondary = row['parentID'] > 0
            if secondary: secondary_photons += 1
            if process_label: creator_label_available += 1
            photons_out.append({**row, 'secondary': int(secondary),
                                'gamma_60_110_keV': int(60 <= raw_energy <= 110 and secondary),
                                'created_track_matched': int(made_idx is not None),
                                'creator_label_recorded': int(bool(process_label)),
                                'creator_process': process_label,
                                'production_volume': textval(outgoing['ProductionVolume'][j]),
                                'energy_complement_keV': float(511 - energies[ev]),
                                'single_photon_energy_delta_keV': float(511 - energies[ev] - raw_energy)})
        for ev in sorted(roi_ids):
            rows = grouped.get(ev, [])
            gamma = [x for x in rows if x['is_gamma']]
            secondary = [x for x in gamma if x['parentID'] > 0]
            candidates = [x for x in secondary if 60 <= x['outgoing_Ekine_keV_assumed'] <= 110]
            sum_g = sum(x['outgoing_Ekine_keV_assumed'] for x in gamma)
            sum_all = sum(x['outgoing_Ekine_keV_assumed'] for x in rows)
            events_out.append({
                'seed': seed, 'eventID': ev, 'deposited_keV': float(energies[ev]),
                'escape_energy_complement_keV': float(511 - energies[ev]),
                'n_outgoing_rows': len(rows), 'n_outgoing_gamma_rows': len(gamma),
                'n_outgoing_non_gamma_rows': len(rows) - len(gamma),
                'n_secondary_outgoing_gamma': len(secondary),
                'n_secondary_gamma_60_110_keV': len(candidates),
                'sum_outgoing_gamma_keV_assumed': sum_g,
                'sum_all_outgoing_particles_keV_assumed': sum_all,
                'energy_minus_Edep_minus_sum_gamma_keV_assumed': 511 - float(energies[ev]) - sum_g,
                'energy_minus_Edep_minus_sum_all_keV_assumed': 511 - float(energies[ev]) - sum_all,
                'gamma_track_ids_unique': int(len(set((x['runID'], x['trackID']) for x in gamma)) == len(gamma)),
            })
        summary = {'condition': 'ON', 'seed': seed, 'primaries': 10000,
                   'roi_events': len(roi_ids),
                   'roi_events_with_any_outgoing_gamma': sum(any(x['is_gamma'] for x in grouped.get(e,[])) for e in roi_ids),
                   'roi_events_with_60_110keV_outgoing_secondary': sum(any(x['is_gamma'] and x['parentID']>0 and 60<=x['outgoing_Ekine_keV_assumed']<=110 for x in grouped.get(e,[])) for e in roi_ids),
                   'outgoing_gamma_rows_from_roi': sum(p['seed']==seed for p in photons_out),
                   'outgoing_secondary_gamma_rows_from_roi': secondary_photons,
                   'outgoing_gamma_rows_with_creator_process': creator_label_available}
        print('   ', json.dumps(summary), flush=True)
        run_summaries.append(summary)
    if len(events_out) != 327:
        raise AssertionError(f'Unexpected total ROI count: {len(events_out)}')
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output/'ROI_event_linkage.csv', events_out, list(events_out[0]))
    write_csv(output/'ROI_outgoing_gamma_tracks.csv', photons_out, list(photons_out[0]) if photons_out else [])
    res = {'status': 'EVENT_LINKED_CANDIDATE_ANALYSIS_ONLY',
           'input_study_status':'VALIDATED', 'run_summaries': run_summaries,
           'source_native_ekine_unit_assumed': args.ekine_unit,
           'roi_events':len(events_out),
           'roi_events_with_60_110_secondary_candidate':sum(x['n_secondary_gamma_60_110_keV']>0 for x in events_out),
           'roi_events_with_outgoing_gamma':sum(x['n_outgoing_gamma_rows']>0 for x in events_out),
           'creator_process_labels_nonempty':dict(Counter(x['creator_process'] for x in photons_out if x['creator_process'])),
           'warning':'Event-linked outgoing candidate analysis, NOT a standalone proof that photon is Bi K fluorescence. Check creator label gaps, volume geometry, track parent, native Ekine units and full energy transport.'}
    (output/'SUMMARY.json').write_text(json.dumps(res,indent=2)+'\n',encoding='utf-8')
    print('Finished; original files unchanged. Output:',output)
    print(json.dumps(res,indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, default=Path.home()/'radiantdaq_region_fluo_paired_recovered_v3_2026')
    p.add_argument('--output',type=Path,default=Path.home()/'radiantdaq_fluo_40k_track_evidence_2026')
    p.add_argument('--ekine-unit',choices=['MeV','keV'],required=True,
                   help='Explicit working hypothesis for GATE ROOT PhaseSpace Ekine branch; verify this convention first')
    collect(p.parse_args())

if __name__ == '__main__':
    main()
