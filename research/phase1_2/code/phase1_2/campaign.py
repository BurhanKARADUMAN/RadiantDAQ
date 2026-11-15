#!/usr/bin/env python3
"""RadiantDAQ Phase 1.2: GATE 9.4 diagnostic and sensitivity campaign.

No fake physics results. Read-only source macros, isolated new workspaces, fail-closed runs.
Requires the author's working GATE 9.4 and material database for execution.
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
from pathlib import Path

PHYS = '/gate/physics/addPhysicsList emstandard_opt3'
SEED_RE = re.compile(r'^/gate/random/setEngineSeed\s+\d+\s*$', re.MULTILINE)
PRIM_RE = re.compile(r'^/gate/application/setTotalNumberOfPrimaries\s+\d+\s*$', re.MULTILINE)
BEAM_X = '/gate/source/gamma511/gps/pos/centre 0. 0. -50. mm'
BEAM_DIRECTION = '/gate/source/gamma511/gps/direction 0. 0. 1.'
ACTOR_MARK = '/gate/actor/addActor DoseActor edepScorer'
PREINIT = '/gate/run/initialize'
ROOTFLAG = '/gate/output/root/enable'
VARIANTS = ('baseline', 'emopt4', 'livermore', 'cut_0p05mm', 'cut_0p5mm', 'fluo_off', 'tilt_2deg')
NO_OVERWRITE_MSG = 'Refusing to overwrite existing workspace or results.'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def replace_unique(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f'{label}: expected exactly one anchor, found {text.count(old)}: {old}')
    return text.replace(old, new, 1)


def create_macro(original: str, variant: str, seed: int, events: int, material_db: str, 
                 outgoing: bool = True) -> str:
    if variant not in VARIANTS:
        raise ValueError(f'Unknown sensitivity variant: {variant}')
    if not (1 <= seed <= 2147483646) or events < 1:
        raise ValueError('Invalid seed or event count')
    text = original
    if len(SEED_RE.findall(text)) != 1 or len(PRIM_RE.findall(text)) != 1:
        raise ValueError('Original macro has unexpected random seed or primaries configuration')
    text = SEED_RE.sub(f'/gate/random/setEngineSeed {seed}', text)
    # Keep generated comment metadata consistent; the original reference macro remains byte-identical.
    text = re.sub(r'^(#\s*(?:BGO|LSO)\s+\d+\s+mm thickness,\s+)\d+(\s+gamma histories, independent seed\s+)\d+\s*$',
                  lambda m: m.group(1)+str(events)+m.group(2)+str(seed), text, flags=re.MULTILINE)
    text = PRIM_RE.sub(f'/gate/application/setTotalNumberOfPrimaries {events}', text)
    mat_re = re.compile(r'^/gate/geometry/setMaterialDatabase\s+\S+\s*$', re.MULTILINE)
    if len(mat_re.findall(text)) != 1:
        raise ValueError('Exactly one GATE material DB command required')
    text = mat_re.sub(f'/gate/geometry/setMaterialDatabase {material_db}', text)
    if variant == 'emopt4':
        text = replace_unique(text, PHYS, '/gate/physics/addPhysicsList emstandard_opt4', 'physics')
    elif variant == 'livermore':
        text = replace_unique(text, PHYS, '/gate/physics/addPhysicsList emlivermore', 'physics')
    elif variant in ('cut_0p05mm', 'cut_0p5mm'):
        cut = '0.05' if variant == 'cut_0p05mm' else '0.5'
        insertion = ('/gate/physics/Gamma/SetCutInRegion crystal '+cut+' mm\n'
                     '/gate/physics/Electron/SetCutInRegion crystal '+cut+' mm\n'
                     '/gate/physics/Positron/SetCutInRegion crystal '+cut+' mm\n')
        text = replace_unique(text, PREINIT, insertion + PREINIT, 'production cuts')
    elif variant == 'fluo_off':
        text = replace_unique(text, PREINIT, '/process/em/fluo false\n' + PREINIT, 'fluorescence')
    elif variant == 'tilt_2deg':
        # A beam at theta=2 deg must start at x=-50*tan(theta) mm to cross crystal center at z=0.
        theta = math.radians(2.0)
        x0 = -50.0 * math.tan(theta)
        text = replace_unique(text, BEAM_X,
                              f'/gate/source/gamma511/gps/pos/centre {x0:.10f} 0. -50. mm', 'beam position')
        text = replace_unique(text, BEAM_DIRECTION,
                              f'/gate/source/gamma511/gps/direction {math.sin(theta):.12f} 0. {math.cos(theta):.12f}', 'beam direction')
    if outgoing:
        # GATE9 PhaseSpaceActor commands, documented in the GATE 9.4 actor manual.
        block = '''# Phase 1.2 diagnostic phase spaces; no PET digitizer, no optical photons.
/gate/actor/addActor PhaseSpaceActor Outgoing
/gate/actor/Outgoing/attachTo crystal
/gate/actor/Outgoing/save outgoing.root
/gate/actor/Outgoing/storeOutgoingParticles true
/gate/actor/Outgoing/enableProductionProcess true
/gate/actor/Outgoing/enableProductionVolume true
/gate/actor/Outgoing/enableParticleName true
/gate/actor/Outgoing/enableEkine true

/gate/actor/addActor PhaseSpaceActor Created
/gate/actor/Created/attachTo crystal
/gate/actor/Created/save created.root
/gate/actor/Created/storeSecondaries true
/gate/actor/Created/enableProductionProcess true
/gate/actor/Created/enableProductionVolume true
/gate/actor/Created/enableParticleName true
/gate/actor/Created/enableEkine true

'''
        text = replace_unique(text, ACTOR_MARK, block + ACTOR_MARK, 'actor position')
    text = f'# RADIANTDAQ_PHASE1_2 variant={variant} seed={seed} events={events}\n' + text
    return text


def cases_for(mode: str, n: int) -> list[dict]:
    if mode == 'smoke':
        rows = [('BGO', 20, 'baseline', 0), ('BGO', 20, 'fluo_off', 1)]
    elif mode == 'full':
        rows = [(m, t, 'baseline', 0) for m in ('BGO', 'LSO') for t in (10, 20, 30)]
        rows += [(m, 20, v, 0) for m in ('BGO', 'LSO') for v in VARIANTS if v != 'baseline']
    else:
        raise ValueError(mode)
    out = []
    for idx, (m, t, variant, _) in enumerate(rows):
        # Two independently seeded repetitions for the full campaign.
        for rep in range(1 if mode == 'smoke' else 2):
            seed = 8300000 + idx * 1109 + rep * 101
            out.append(dict(id=f'{m}_T{t}_{variant}_R{rep+1}_S{seed}', material=m,
                            thickness_mm=t, variant=variant, seed=seed, n_primaries=n, replicate=rep+1))
    assert len({x['seed'] for x in out}) == len(out)
    return out


def prepare(base: Path, workspace: Path, db: Path, gate: Path, mode: str, events: int):
    base = base.expanduser().resolve(); workspace = workspace.expanduser().resolve()
    db = db.expanduser().resolve(); gate = gate.expanduser().resolve()
    if workspace.exists():
        raise FileExistsError(NO_OVERWRITE_MSG + f' {workspace}')
    if not db.is_file() or not gate.is_file():
        raise FileNotFoundError(f'Missing actual GateMaterials.db or GATE executable: {db} | {gate}')
    if not base.is_dir():
        raise FileNotFoundError(base)
    cases = cases_for(mode, events)
    # Preflight all macros BEFORE touching workspace; fail if any baseline anchor changed.
    generated = []
    for c in cases:
        ref = base / f"{c['material']}_T{c['thickness_mm']}_pilot_original.mac"
        original = ref.read_text(encoding='utf-8')
        macro = create_macro(original, c['variant'], c['seed'], events, str(db))
        generated.append((c, ref, macro))
    workspace.mkdir(parents=True, exist_ok=False)
    (workspace / 'runs').mkdir()
    manifest = dict(project='RadiantDAQ Phase 1.2', status='PREPARED_NOT_EXECUTED',mode=mode,
                    note='All generated macros are unexecuted until run is called; ACTOR fields must be smoke-tested on GATE9.4.',
                    material_db=str(db), material_db_sha256=sha256(db), gate=str(gate), 
                    base_macros={p.name:sha256(p) for _,p,_ in generated}, cases=cases)
    for c, ref, macro in generated:
        work = workspace/'runs'/c['id']
        work.mkdir()
        (work/'run.mac').write_text(macro,encoding='utf-8')
        (work/'input.json').write_text(json.dumps({**c,'reference_macro_sha256':sha256(ref),
                  'run_macro_sha256':sha256(work/'run.mac'), 'materials_sha256':sha256(db)},indent=2)+'\n')
    (workspace/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'status':'prepared','mode':mode,'runs':len(cases),'histories':len(cases)*events,
                      'workspace':str(workspace)}, indent=2))



def read_doseactor_total(work: Path) -> tuple[float, dict]:
    """Read GATE DoseActor MetaImage score without assuming voxel size/dimensions."""
    import numpy as np
    paths = list(work.glob('*Edep.mhd'))
    if len(paths) != 1:
        raise ValueError(f'{work}: expected one DoseActor *Edep.mhd, found {len(paths)}')
    mhd = paths[0]
    lines = [line.strip() for line in mhd.read_text(errors='replace').splitlines() if '=' in line]
    metadata = {a.strip(): b.strip() for a, b in (line.split('=', 1) for line in lines)}
    if metadata.get('CompressedData', 'False').lower() in ('true', '1'):
        raise ValueError('Compressed DoseActor RAW unsupported')
    dtype_name = {'MET_FLOAT': 'f4', 'MET_DOUBLE': 'f8', 'MET_INT': 'i4', 'MET_SHORT': 'i2'}.get(metadata.get('ElementType'))
    if dtype_name is None: raise ValueError('Unsupported DoseActor element type')
    payload_name = metadata.get('ElementDataFile', '')
    if Path(payload_name).name != payload_name or not payload_name or payload_name == 'LOCAL':
        raise ValueError('DoseActor payload must be local uncompressed .raw file')
    raw = work / payload_name
    dims = [int(d) for d in metadata['DimSize'].split()]
    endian = '>' if metadata.get('BinaryDataByteOrderMSB', 'False').lower() in ('true', '1') else '<'
    a = np.fromfile(raw, dtype=endian+dtype_name)
    if a.size != math.prod(dims) or not np.all(np.isfinite(a)) or np.any(a < -1e-8):
        raise ValueError('Malformed or unphysical DoseActor RAW data')
    return float(a.sum(dtype=np.float64)), {mhd.name:sha256(mhd), raw.name:sha256(raw)}


def verify_run(work: Path, expected_events: int) -> dict:
    import numpy as np
    import uproot
    root = work/'hits.root'
    if not root.exists():
        raise FileNotFoundError(f'{work}: no ROOT Hits; GATE output incomplete')
    with uproot.open(root) as f:
        if 'Hits' not in f:
            raise ValueError(f'{root}: ROOT Hits tree absent')
        t = f['Hits']
        events = t['eventID'].array(library='np')
        edep = t['edep'].array(library='np')
    if len(events) == 0 or np.min(events) < 0 or np.max(events) >= expected_events:
        raise ValueError(f'{work}: invalid eventID or empty Hits')
    if not np.all(np.isfinite(edep)) or np.any(edep < -1e-8):
        raise ValueError('Invalid ROOT edep')
    energies = np.bincount(events,weights=edep,minlength=expected_events)*1000.0
    if np.any(energies < -1e-6) or np.any(energies > 511.1):
        raise ValueError('Unphysical crystal deposition')
    dose_mev, dose_hashes = read_doseactor_total(work)
    root_mev = float(energies.sum(dtype=np.float64) / 1000.0)
    tolerance_mev = max(0.0005, 1e-6 * abs(root_mev))
    if abs(root_mev - dose_mev) > tolerance_mev:
        raise ValueError(f'{work}: ROOT/DoseActor total mismatch: {root_mev} vs {dose_mev} MeV')
    # PhaseSpaceActor output filename / tree layout must be established empirically.
    for name in ('outgoing.root','created.root'):
        if not (work/name).exists():
            raise FileNotFoundError(f'{work}: expected GATE9 PhaseSpaceActor output {name} missing')
        with uproot.open(work/name) as f:
            trees=[(k.split(';')[0],v) for k,v in f.items() if hasattr(v,'num_entries')]
            if not trees:
                raise ValueError(f'{work}/{name}: no ROOT tree')
    csv_path = work / 'energy_per_primary_keV.csv'
    if csv_path.exists():
        raise FileExistsError(f'Refusing to replace existing derived event CSV: {csv_path}')
    np.savetxt(csv_path, energies, fmt='%.15e', header='deposited_energy_keV', comments='')
    return {'n_events':expected_events,'n_interaction':int(np.count_nonzero(energies>1e-6)),
            'n_nearfull':int(np.count_nonzero((energies>=490)&(energies<=520))),
            'n_400_440':int(np.count_nonzero((energies>=400)&(energies<=440))),
            'sum_edep_MeV':root_mev,'dose_edep_MeV':dose_mev,
            'abs_root_dose_diff_MeV':abs(root_mev-dose_mev),
            'dose_file_hashes':dose_hashes,'energy_csv_sha256':sha256(csv_path),'root_sha256':sha256(root)}


def execute(workspace: Path, limit: int=0):
    workspace = workspace.expanduser().resolve()
    manifest = json.loads((workspace/'manifest.json').read_text())
    db=Path(manifest['material_db']); gate=Path(manifest['gate'])
    if not db.is_file() or sha256(db)!=manifest['material_db_sha256']:
        raise ValueError('Material database changed or missing; aborting')
    if not gate.is_file():
        raise FileNotFoundError(gate)
    cases=manifest['cases'][:limit or None]
    for i,case in enumerate(cases,1):
        w=workspace/'runs'/case['id']; validated=w/'validated.json'; log=w/'gate.log'
        if validated.exists():
            check=json.loads(validated.read_text())
            if check.get('macro_sha256')!=sha256(w/'run.mac'):
                raise ValueError('Unexpected macro change in completed run: '+case['id'])
            print(f'[SKIP {i}/{len(cases)}] verified {case["id"]}', flush=True)
            continue
        if log.exists() or (w/'hits.root').exists():
            raise FileExistsError(f'Partial run preserved; investigate before retrying: {w}')
        print(f'[RUN {i}/{len(cases)}] {case["id"]}',flush=True)
        with log.open('wb') as f:
            cp=subprocess.run([str(gate),'run.mac'],cwd=w,stdout=f,stderr=subprocess.STDOUT)
        if cp.returncode:
            raise RuntimeError(f'GATE returned {cp.returncode}; inspect {log}')
        status=verify_run(w,case['n_primaries'])
        status.update(gate_return_code=cp.returncode,macro_sha256=sha256(w/'run.mac'),
                      material_db_sha256=sha256(db), case=case)
        validated.write_text(json.dumps(status,indent=2)+'\n')
    print('Run command finished; check validations and run summarize.')


def extract_phase_space(path: Path) -> dict:
    import uproot
    with uproot.open(path) as f:
        trees=[(k.split(';')[0],v) for k,v in f.items() if hasattr(v,'num_entries')]
        if not trees:
            raise ValueError('No tree in '+str(path))
        name,tree=trees[0]
        keys=list(tree.keys())
        ans={'tree':name,'entries':int(tree.num_entries),'branches':keys}
        # GATE 9.4 phase-space files vary in available naming; DO NOT infer the kinetic energy unit.
        for term in ['ekine','kineticenergy','particle','productionprocess','productionvolume','eventid','trackid','parentid']:
            matches=[k for k in keys if term in k.lower().replace('_','')]
            ans['match_'+term]=matches
        return ans


def summarize(workspace: Path, output: Path | None = None):
    workspace=workspace.expanduser().resolve(); manifest=json.loads((workspace/'manifest.json').read_text())
    out=output.expanduser().resolve() if output is not None else workspace/'analysis'
    if out.exists():
        raise FileExistsError(f'Analysis exists, refusing to overwrite: {out}')
    rows=[]; detailed=[]
    for case in manifest['cases']:
        w=workspace/'runs'/case['id']; v=w/'validated.json'
        if not v.is_file():
            raise FileNotFoundError(f'Missing successful run: {case["id"]}')
        status=json.loads(v.read_text()); row={**case,**{k:status[k] for k in
                          ('n_interaction','n_nearfull','n_400_440','sum_edep_MeV','dose_edep_MeV','abs_root_dose_diff_MeV')}}
        row['interaction_fraction']=row['n_interaction']/row['n_primaries']
        row['near_full_fraction']=row['n_nearfull']/row['n_primaries']
        row['roi_fraction']=row['n_400_440']/row['n_primaries']
        rows.append(row)
        detailed.append({'case':case,'phsp_outgoing':extract_phase_space(w/'outgoing.root'),
                         'phsp_created':extract_phase_space(w/'created.root')})
    out.mkdir()
    with (out/'case_metrics.csv').open('w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
    (out/'phsp_schema_audit.json').write_text(json.dumps(detailed,indent=2)+'\n')
    from stats import write_analysis
    write_analysis(rows,out)
    (out/'RESEARCH_STATUS.md').write_text(
        '# Phase 1.2 diagnostic and sensitivity campaign\n\n'
        f'**Actual locally completed runs:** {len(rows)}. **Primaries:** {sum(x["n_primaries"] for x in rows)}.\n\n'
        'ROOT Hits event totals and independent DoseActor summation have passed a numerical cross-check. Outgoing/created phase-space schema audit is recorded separately.\n\n'
        '**No proof of characteristic X-ray escape without validated event-level boundary/creator linkage.** '
        'A PhaseSpaceActor schema lacking event/track IDs allows only marginal outgoing distributions. '
        'Do not compare material effects across changing geometry without explicitly stating the changed model.\n')
    print(json.dumps({'status':'analyzed','runs':len(rows),'output':str(out)},indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='cmd',required=True)
    for n in ('prepare','run','summarize'):
        s=sub.add_parser(n)
        s.add_argument('--workspace',type=Path,required=True)
        if n=='prepare':
            s.add_argument('--reference-macros',type=Path,default=Path(__file__).resolve().parents[1]/'pilot_macros')
            s.add_argument('--db',type=Path,default=Path.home()/'Gate-9.4/GateMaterials.db')
            s.add_argument('--gate',type=Path,default=Path.home()/'gate_build/Gate')
            s.add_argument('--mode',choices=('smoke','full'),default='smoke')
            s.add_argument('--events',type=int,default=None)
        if n=='run':s.add_argument('--limit',type=int,default=0)
        if n=='summarize':s.add_argument('--output',type=Path,default=None,help='Fresh analysis directory; never overwrites existing results')
    a=p.parse_args()
    if a.cmd=='prepare':prepare(a.reference_macros,a.workspace,a.db,a.gate,a.mode,a.events if a.events is not None else (200 if a.mode=='smoke' else 5000))
    elif a.cmd=='run':execute(a.workspace,a.limit)
    elif a.cmd=='summarize':summarize(a.workspace,a.output)

if __name__=='__main__':main()
