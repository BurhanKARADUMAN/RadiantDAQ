#!/usr/bin/env python3
"""RadiantDAQ: audited 511-keV BGO fluorescence-region paired transport controls.

New isolated workspace ONLY; anchored to an immutable, validated source macro.
Runs two independent seeds, each with ON and OFF regional fluorescence flags,
while keeping the global EM fluorescence setting on and all other settings fixed.
Hard stops on any mismatch, abort, missing output or inconsistent energy total.

WARNING: A correct regional printout does not by itself prove that every secondary
production mechanism has been disabled. Interpret physical results accordingly.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SOURCE_ID = 'BGO_T20_baseline_R1_S8301109'
SOURCE_SHA256 = 'ad908f97c4710f00f0a5506c6e9217768a923f781d1a572e1adcf58ffc6651e5'
PHYS = '/gate/physics/addPhysicsList emstandard_opt3'
INIT = '/gate/run/initialize'
DAQ = '/gate/application/startDAQ'
CONTROL_BEGIN = 'RADIANTDAQ_POSTINIT_REGION_CONTROL_BEGIN'
CONTROL_END = 'RADIANTDAQ_POSTINIT_REGION_CONTROL_END'
FLAGS_RE = re.compile(r'^\s*crystal\s+([01])\s+([01])\s+([01])\s*$')
BASE_SEEDS = (8457101, 8457202)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def build_macro(raw: str, *, fluo: str, seed: int, events: int) -> str:
    assert fluo in ('OFF', 'ON')
    lines = raw.splitlines()
    stripped = [x.strip() for x in lines]
    for command in (PHYS, INIT, DAQ):
        if stripped.count(command) != 1:
            raise ValueError(f'Expected exactly one {command!r}')
    if not stripped.index(PHYS) < stripped.index(INIT) < stripped.index(DAQ):
        raise ValueError('Invalid physics/init/acquisition ordering')
    if any(x.startswith(('/process/em/fluo ', '/process/em/deexcitation ')) for x in stripped):
        raise ValueError('Source contains competing EM de-excitation commands')
    seed_re = re.compile(r'/gate/random/setEngineSeed\s+\d+')
    events_re = re.compile(r'/gate/application/setTotalNumberOfPrimaries\s+\d+')
    if sum(bool(seed_re.fullmatch(x)) for x in stripped) != 1:
        raise ValueError('Exactly one original seed required')
    if sum(bool(events_re.fullmatch(x)) for x in stripped) != 1:
        raise ValueError('Exactly one original primary count required')
    text = []
    for line, cleaned in zip(lines, stripped):
        if cleaned.startswith('# RADIANTDAQ_PHASE1_2'):
            line = f'# RADIANTDAQ_REGION_FLUO_PAIRED mode={fluo} seed={seed} events={events}'
        elif seed_re.fullmatch(cleaned):
            line = f'/gate/random/setEngineSeed {seed}'
        elif events_re.fullmatch(cleaned):
            line = f'/gate/application/setTotalNumberOfPrimaries {events}'
        text.append(line)
        if cleaned == INIT:
            text.extend([
                f'/control/echo {CONTROL_BEGIN}',
                '/process/em/deexcitation DefaultRegionForTheWorld true true true',
                '/process/em/deexcitation crystal ' + ('false true true' if fluo == 'OFF' else 'true true true'),
                f'/control/echo {CONTROL_END}',
            ])
    result = '\n'.join(text) + '\n'
    if not (result.index(PHYS) < result.index(INIT)
            < result.index('/process/em/deexcitation crystal') < result.index(DAQ)):
        raise ValueError('Unexpected generated macro command order')
    if '/process/em/fluo false' in result:
        raise ValueError('Forbidden global post-init toggle')
    return result


def parse_transport_flags(log: str) -> list[tuple[int, int, int]]:
    lines = log.splitlines()
    found = []
    for i, line in enumerate(lines):
        if 'Deexcitation model' in line and 'activated for' in line:
            for s in lines[i + 1:i + 25]:
                m = FLAGS_RE.fullmatch(s)
                if m:
                    found.append(tuple(map(int, m.groups())))
    return found


def read_dose_total(folder: Path) -> tuple[float, dict]:
    import numpy as np
    mhd_files = list(folder.glob('*Edep.mhd'))
    if len(mhd_files) != 1:
        raise ValueError(f'Expected exactly one DoseActor *Edep.mhd; found {len(mhd_files)}')
    mhd = mhd_files[0]
    meta = {}
    for line in mhd.read_text(errors='replace').splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            meta[k.strip()] = v.strip()
    if meta.get('CompressedData', 'False').lower() in ('true', '1'):
        raise ValueError('Compressed DoseActor data unsupported')
    typ = {'MET_FLOAT': 'f4', 'MET_DOUBLE': 'f8', 'MET_INT': 'i4', 'MET_SHORT': 'i2'}.get(meta.get('ElementType'))
    if typ is None:
        raise ValueError(f'Unexpected DoseActor ElementType: {meta.get("ElementType")}')
    name = meta.get('ElementDataFile', '')
    if not name or Path(name).name != name or name == 'LOCAL':
        raise ValueError('DoseActor data must be a local file')
    raw_path = folder / name
    dims = [int(i) for i in meta['DimSize'].split()]
    endian = '>' if meta.get('BinaryDataByteOrderMSB', 'False').lower() in ('true', '1') else '<'
    data = np.fromfile(raw_path, dtype=endian + typ)
    if data.size != math.prod(dims) or not np.isfinite(data).all() or np.any(data < -1e-8):
        raise ValueError('Corrupt or nonphysical DoseActor values')
    return float(data.sum(dtype=np.float64)), {'mhd_sha256': sha256(mhd), 'raw_sha256': sha256(raw_path)}


def audit_outputs(folder: Path, n: int) -> dict:
    import numpy as np
    import uproot
    root = folder / 'hits.root'
    if not root.is_file():
        raise ValueError('Missing hits.root')
    with uproot.open(root) as f:
        tree = f['Hits']
        event_ids = tree['eventID'].array(library='np')
        energy_mev = tree['edep'].array(library='np')
    if (not len(event_ids) or not np.issubdtype(event_ids.dtype, np.integer)
        or event_ids.min() < 0 or event_ids.max() >= n
        or not np.isfinite(energy_mev).all() or np.any(energy_mev < -1e-8)):
        raise ValueError('Invalid ROOT Hits eventIDs or deposited energies')
    per_keV = np.bincount(event_ids, weights=energy_mev, minlength=n) * 1000.0
    if not np.isfinite(per_keV).all() or np.any(per_keV < -1e-6) or np.any(per_keV > 511.1):
        raise ValueError('Out-of-range event energy deposition')
    total_root_mev = float(per_keV.sum(dtype=np.float64) / 1000.0)
    total_dose_mev, dose_hashes = read_dose_total(folder)
    tolerance_mev = max(0.0005, 1e-6 * abs(total_root_mev))
    if abs(total_root_mev - total_dose_mev) > tolerance_mev:
        raise ValueError(f'ROOT / DoseActor energy total mismatch: {total_root_mev} versus {total_dose_mev}')
    phsp = {}
    for name in ('outgoing.root', 'created.root'):
        path = folder / name
        if not path.is_file():
            raise ValueError(f'Missing {name}')
        with uproot.open(path) as f:
            trees = [t for _, t in f.items() if hasattr(t, 'num_entries')]
            if len(trees) != 1:
                raise ValueError(f'{name} should have 1 phase-space tree; got {len(trees)}')
            phsp[name] = {'rows': int(trees[0].num_entries), 'sha256': sha256(path)}
    # Derived event-level output is strictly within this new experiment directory.
    energy_csv = folder / 'deposited_energy_per_primary_keV.csv'
    if energy_csv.exists():
        raise FileExistsError(f'Refusing overwrite: {energy_csv}')
    with energy_csv.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(('eventID', 'deposited_energy_keV'))
        w.writerows((i, f'{v:.12f}') for i, v in enumerate(per_keV))
    roi = (per_keV >= 400.0) & (per_keV <= 440.0)
    return {
        'histories': n,
        'hit_rows': int(len(event_ids)),
        'interacting_events': int(np.count_nonzero(per_keV > 1e-6)),
        'roi_400_440': int(np.count_nonzero(roi)),
        'nearfull_490_520': int(np.count_nonzero((per_keV >= 490) & (per_keV <= 520))),
        'total_root_edep_MeV': total_root_mev,
        'total_dose_edep_MeV': total_dose_mev,
        'root_dose_abs_diff_MeV': abs(total_root_mev - total_dose_mev),
        'hits_root_sha256': sha256(root),
        'energy_csv_sha256': sha256(energy_csv),
        'dose_hashes': dose_hashes,
        'phase_space': phsp,
    }


def run_case(gate: Path, folder: Path, fluo: str, events: int, timeout: int) -> dict:
    log_path = folder / 'gate.log'
    with log_path.open('wb') as f:
        try:
            cp = subprocess.run([str(gate), 'run.mac'], cwd=folder, stdout=f,
                                stderr=subprocess.STDOUT, timeout=timeout, check=False)
            rc = cp.returncode
        except subprocess.TimeoutExpired:
            rc = 'TIMEOUT'
    log = log_path.read_text(errors='replace')
    expected = (0, 1, 1) if fluo == 'OFF' else (1, 1, 1)
    flags = parse_transport_flags(log)
    errors = [term for term in ('*** Fatal Exception ***', 'G4Exception : de0001',
             'Command not found', 'command not found', 'Illegal application state',
             'illegal application state', '*** Run must be aborted ***') if term in log]
    status = {
        'condition': fluo,
        'gate_exit_code': rc,
        'expected_crystal_flags': list(expected),
        'crystal_flags_at_transport': [list(x) for x in flags],
        'errors': errors,
        'macro_sha256': sha256(folder / 'run.mac'),
        'log_sha256': sha256(log_path),
        'gate_log': str(log_path),
        'status': 'INVALID',
    }
    if rc != 0 or len(flags) < 2 or any(x != expected for x in flags) or errors or \
       CONTROL_END not in log or 'Acquisition starts!' not in log:
        status['validation_error'] = 'GATE flags, output markers or runtime status are invalid'
        return status
    try:
        status.update(audit_outputs(folder, events))
        status['status'] = 'VALIDATED'
    except Exception as ex:
        status['validation_error'] = f'{type(ex).__name__}: {ex}'
    return status


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    denom = 1 + z*z/n
    c = (p + z*z/(2*n))/denom
    d = z/denom*math.sqrt((p*(1-p)+z*z/(4*n))/n)
    return max(0, c-d), min(1, c+d)


def fisher_two_sided(a: int, n1: int, b: int, n2: int) -> float:
    N = n1+n2
    K = a+b
    def log_choose(n,k):
        if k<0 or k>n: return float('-inf')
        return math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)
    def logp(x):
        return log_choose(n1,x) + log_choose(n2,K-x) - log_choose(N,K)
    lo, hi = max(0, K-n2), min(n1, K)
    obs = logp(a)
    return min(1., sum(math.exp(logp(x)) for x in range(lo,hi+1) if logp(x) <= obs + 1e-9))


def write_summary(out: Path, manifest: dict) -> None:
    statuses = manifest['runs']
    rows=[]
    for run in statuses:
        if run['status'] != 'VALIDATED':
            continue
        rows.append({'seed':run['seed'], 'condition':run['condition'],
                     'histories':run['histories'], 'roi_400_440':run['roi_400_440'],
                     'nearfull_490_520':run['nearfull_490_520'],
                     'interacting_events':run['interacting_events'],
                     'root_dose_abs_diff_MeV':run['root_dose_abs_diff_MeV'],
                     'macro_sha256':run['macro_sha256']})
    fn = out / 'run_metrics.csv'
    with fn.open('w',newline='') as f:
        w = csv.DictWriter(f,fieldnames=('seed','condition','histories','roi_400_440',
                         'nearfull_490_520','interacting_events','root_dose_abs_diff_MeV','macro_sha256'))
        w.writeheader()
        w.writerows(rows)
    summary={'status':'INCOMPLETE' if any(r['status']!='VALIDATED' for r in statuses)
             or len(statuses)!=manifest['expected_runs'] else 'VALIDATED',
             'study':'BGO 3x3x20 mm, 511 keV incident gamma, two independently seeded ON/OFF regional controls',
             'source_macro_sha256':manifest['source_macro_sha256'],
             'results':{},
             'note': 'Control tests region-level flags, ROOT-Dose energy closure. Global fluorescence stays ON. No optical light-collection or SiPM digitizer is simulated.'}
    for name in ('OFF','ON'):
        subs=[r for r in statuses if r['status']=='VALIDATED' and r['condition']==name]
        n=sum(r['histories'] for r in subs)
        k=sum(r['roi_400_440'] for r in subs)
        near=sum(r['nearfull_490_520'] for r in subs)
        summary['results'][name]={'runs':len(subs),'histories':n,'roi_400_440':k,
                 'roi_fraction':k/n if n else None,
                 'roi_wilson95':list(wilson(k,n)) if n else None,
                 'nearfull_490_520':near,'nearfull_fraction':near/n if n else None}
    if summary['status']=='VALIDATED':
        off,on=summary['results']['OFF'],summary['results']['ON']
        k0,n0=off['roi_400_440'],off['histories']
        k1,n1=on['roi_400_440'],on['histories']
        summary['comparison']={'roi_absolute_difference_ON_minus_OFF':k1/n1-k0/n0,
                      'roi_rate_ratio_ON_div_OFF':(k1/n1)/(k0/n0) if k0 else None,
                      'two_sided_fisher_exact_p':fisher_two_sided(k0,n0,k1,n1),
                      'warning':'Paired seeds improve matching of input conditions, but pathwise event identity is not guaranteed. The p-value is an event-count comparison; mechanism needs independent secondaries review.'}
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('\nCURRENT SUMMARY:')
    print(json.dumps(summary,indent=2),flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workspace',type=Path,default=Path.home()/'radiantdaq_phase1_2_full_2026')
    ap.add_argument('--output',type=Path,default=Path.home()/'radiantdaq_region_fluo_paired_2026')
    ap.add_argument('--gate',type=Path,default=Path.home()/'gate_build/Gate')
    ap.add_argument('--events',type=int,default=10000)
    ap.add_argument('--timeout',type=int,default=7200,help='seconds per GATE run')
    args=ap.parse_args()
    if not 300<=args.events<=100000:
        ap.error('--events must be 300 to 100000')
    if not 60<=args.timeout<=86400:
        ap.error('--timeout must be 60 to 86400')
    work,output,gate=(x.expanduser().resolve() for x in (args.workspace,args.output,args.gate))
    source=work/'runs'/SOURCE_ID/'run.mac'
    valid=work/'runs'/SOURCE_ID/'validated.json'
    if output.exists() or output == work or work in output.parents:
        raise SystemExit(f'Refusing existing or campaign-contained output path: {output}')
    if not all(p.is_file() for p in (source,valid,gate)):
        raise SystemExit('Missing source macro, validated.json or executable')
    meta=json.loads(valid.read_text())
    if meta.get('macro_sha256') != SOURCE_SHA256 or sha256(source) != SOURCE_SHA256:
        raise SystemExit('Source macro SHA-256 differs from validated known anchor; STOP')
    raw=source.read_text()
    sequence=[]
    for i,seed in enumerate(BASE_SEEDS,1):
        for fluo in ('OFF','ON'):
            mac=build_macro(raw,fluo=fluo,seed=seed,events=args.events)
            sequence.append((i,seed,fluo,mac))
    manifest={
        'project':'RadiantDAQ fluorescence region paired study 2026',
        'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'STARTED',
        'source_macro':str(source),
        'source_macro_sha256':SOURCE_SHA256,
        'gate_executable':str(gate),
        'events_per_run':args.events,
        'independent_seed_count':len(BASE_SEEDS),
        'expected_runs':len(sequence),
        'expected_total_histories':len(sequence)*args.events,
        'seeds':list(BASE_SEEDS),
        'method':'post-initialization region control; global fluorescence ON, world ON, crystal OFF or ON; Auger and PIXE ON',
        'runs':[],
    }
    output.mkdir(parents=True,exist_ok=False)
    (output/'runs').mkdir()
    def save():
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        write_summary(output,manifest)
    save()
    try:
        for i,seed,fluo,macro in sequence:
            folder=output/'runs'/f'BGO_T20_{fluo}_rep{i}_seed{seed}'
            folder.mkdir()
            (folder/'run.mac').write_text(macro)
            print(f'\n[GATE {len(manifest["runs"])+1}/{len(sequence)}] {fluo} seed={seed} histories={args.events}',flush=True)
            result=run_case(gate,folder,fluo,args.events,args.timeout)
            result.update({'seed':seed,'replicate':i,'path':str(folder)})
            manifest['runs'].append(result)
            print(json.dumps({k:v for k,v in result.items()
                    if k in ('seed','condition','status','gate_exit_code','crystal_flags_at_transport',
                             'validation_error','roi_400_440','nearfull_490_520',
                             'root_dose_abs_diff_MeV')},indent=2),flush=True)
            save()
            if result['status']!='VALIDATED':
                manifest['status']='STOPPED_INVALID_RUN'
                save()
                print('STOPPED: Invalid physics or data; no further runs. Do not interpret results as a valid ON/OFF comparison.',flush=True)
                return 2
        manifest['status']='VALIDATED'
        save()
        print('\nALL CONTROL RUNS VALIDATED. Read',output/'SUMMARY.json',flush=True)
        return 0
    finally:
        save()


if __name__=='__main__':
    sys.exit(main())
