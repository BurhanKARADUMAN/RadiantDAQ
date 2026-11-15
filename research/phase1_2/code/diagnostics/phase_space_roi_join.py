#!/usr/bin/env python3
"""Read-only Phase 1.2 GATE 9.4 event-linked photon evidence extractor.

Requires local native created.root, outgoing.root and per-primary energy CSV
for each completed Phase 1.2 run. Exports only small derived CSVs.

CRITICAL: Observing an outgoing photon of a certain energy is not a full
energy-conservation proof or definitive attribution of the whole ROI feature.
Choose --ekine-unit explicitly after checking local GATE output conventions.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

REQ=('RunID','EventID','TrackID','ParentID','ParticleName','CreatorProcess','ProductionVolume','Ekine')


def textval(x):
    if isinstance(x,(bytes,np.bytes_)):
        return bytes(x).decode('utf-8',errors='replace').rstrip('\x00').strip()
    return str(x).rstrip('\x00').strip()


def photon(x):
    return textval(x).lower() in ('gamma','photon')


def decode_length_prefixed_char_basket(data, byte_offsets, header_bytes=0, length_bytes='1-5'):
    """Decode ROOT char* basket entries without dereferencing end-of-buffer offsets.

    Returns (values, encoded_mask). ROOT may store zero-byte entries for
    unavailable process labels. Those become *unavailable*, not inferred names.
    Rejects malformed nonempty entries rather than silently assigning processes.
    """
    raw=np.asarray(data,dtype=np.uint8)
    offs=np.asarray(byte_offsets,dtype=np.int64)
    if offs.ndim!=1 or len(offs)<1 or offs[0]!=0 or np.any(np.diff(offs)<0) or offs[-1]>len(raw):
        raise ValueError('Invalid ROOT char* basket offsets')
    if not isinstance(header_bytes,(int,np.integer)) or header_bytes<0:
        raise ValueError('Invalid ROOT char* header length')
    if length_bytes not in ('1-5','4'):
        raise ValueError('Unsupported ROOT string size encoding')
    strings=[];encoded=[]
    for lo,hi in zip(offs[:-1],offs[1:]):
        lo,hi=int(lo),int(hi)
        if lo==hi:
            strings.append('');encoded.append(False)
            continue
        pos=lo+header_bytes
        if pos>=hi:
            raise ValueError('Truncated ROOT char* entry header')
        if length_bytes=='1-5':
            count=int(raw[pos]);pos+=1
            if count==255:
                if pos+4>hi:raise ValueError('Truncated ROOT extended char* length')
                count=int.from_bytes(raw[pos:pos+4].tobytes(),'big');pos+=4
        else:
            if pos+4>hi:raise ValueError('Truncated ROOT 4-byte char* length')
            count=int.from_bytes(raw[pos:pos+4].tobytes(),'big');pos+=4
        if count!=(hi-pos):
            raise ValueError(f'ROOT char* encoded length mismatch: {count} vs {hi-pos}')
        try:
            name=raw[pos:hi].tobytes().decode('utf-8','strict').rstrip('\x00')
        except UnicodeDecodeError as e:
            raise ValueError('Invalid UTF-8 ROOT char* value') from e
        strings.append(name);encoded.append(True)
    return np.asarray(strings,dtype=object),np.asarray(encoded,dtype=bool)


def read_creator_process(branch,expected):
    """Read CreatorProcess entry-by-entry at ROOT basket boundaries, preserving gaps."""
    interp=branch.interpretation
    if branch.typename != 'char*' or not hasattr(interp,'header_bytes'):
        raise ValueError('CreatorProcess is not the expected char* string branch')
    names=[];available=[]
    for basket_idx in range(branch.num_baskets):
        b=branch.basket(basket_idx)
        if b.byte_offsets is None:
            raise ValueError(f'CreatorProcess basket {basket_idx} lacks entry offsets')
        vals,mask=decode_length_prefixed_char_basket(
            b.data,b.byte_offsets,interp.header_bytes,interp.length_bytes)
        names.extend(vals.tolist());available.extend(mask.tolist())
    if len(names)!=expected:
        raise ValueError(f'CreatorProcess entry mismatch: {len(names)} vs {expected}')
    return np.asarray(names,dtype=object),np.asarray(available,dtype=bool)


def read_tree(path:Path):
    import uproot
    with uproot.open(path) as root:
        if 'PhaseSpace' not in root:
            raise ValueError(f'{path}: expected PhaseSpace tree')
        tree=root['PhaseSpace']
        missing=set(REQ)-set(tree.keys())
        if missing:
            raise ValueError(f'{path}: missing required branches {sorted(missing)}')
        a={k:tree[k].array(library='np') for k in REQ if k!='CreatorProcess'}
        size=len(a['EventID'])
        names,available=read_creator_process(tree['CreatorProcess'],size)
        a['CreatorProcess']=names
        a['_creator_process_recorded']=available
        if any(len(x)!=size for x in a.values()):
            raise ValueError(f'{path}: inconsistent branch lengths')
        if not np.all(np.isfinite(a['Ekine'])) or np.any(a['Ekine']<0):
            raise ValueError(f'{path}: nonfinite / negative outgoing energy')
        return a


def unique_track_key(a,idx):
    return int(a['RunID'][idx]),int(a['EventID'][idx]),int(a['TrackID'][idx])


def analyze_case(c,run:Path,conv:float,emin:float,emax:float):
    n=int(c['n_primaries'])
    efile=run/'energy_per_primary_keV.csv'
    energies=np.loadtxt(efile,delimiter=',',skiprows=1)
    if energies.shape!=(n,) or not np.all(np.isfinite(energies)):
        raise ValueError(f'{run}: invalid per-primary Edep CSV')
    roi_ids=set(np.flatnonzero((energies>=400)&(energies<=440)).tolist())
    outgoing=read_tree(run/'outgoing.root');created=read_tree(run/'created.root')
    for label,arr in [('outgoing',outgoing),('created',created)]:
        ids=arr['EventID']
        if np.any(ids<0) or np.any(ids>=n):
            raise ValueError(f'{run}: {label} EventID exceeds primaries')
    created_tracks=set()
    for i in range(len(created['EventID'])):
        if photon(created['ParticleName'][i]):
            created_tracks.add(unique_track_key(created,i))
    rows=[]; events=defaultdict(list)
    for i in range(len(outgoing['EventID'])):
        ev=int(outgoing['EventID'][i]);
        if ev not in roi_ids or not photon(outgoing['ParticleName'][i]):continue
        parent=int(outgoing['ParentID'][i]);kinetic=float(outgoing['Ekine'][i])*conv
        key=unique_track_key(outgoing,i)
        candidate=(parent>0 and emin<=kinetic<=emax)
        row=dict(case_id=c['id'],material=c['material'],thickness_mm=c['thickness_mm'],variant=c['variant'],
                 seed=c['seed'],run_id=key[0],event_id=ev,track_id=key[2],parent_id=parent,
                 deposited_keV=float(energies[ev]),outgoing_gamma_energy_keV=kinetic,
                 photon_creator_process=textval(outgoing['CreatorProcess'][i]),
                 photon_creator_process_recorded=int(outgoing['_creator_process_recorded'][i]),
                 production_volume=textval(outgoing['ProductionVolume'][i]),
                 secondary_gamma=int(parent>0),candidate_60_110keV=int(candidate),
                 linked_to_created_track=int(key in created_tracks))
        rows.append(row);events[ev].append(row)
    one_per_event=[]
    for ev in sorted(roi_ids):
        rs=events.get(ev,[])
        sec=[x for x in rs if x['secondary_gamma']]
        cands=[x for x in rs if x['candidate_60_110keV']]
        one_per_event.append(dict(case_id=c['id'],material=c['material'],thickness_mm=c['thickness_mm'],variant=c['variant'],
          seed=c['seed'],event_id=ev,deposited_keV=float(energies[ev]),
          n_outgoing_gamma_rows=len(rs),n_unique_outgoing_secondary_gamma_tracks=len(set((x['run_id'],x['track_id']) for x in sec)),
          n_candidate_energy_rows=len(cands),n_matched_created_candidate_tracks=len(set((x['run_id'],x['track_id']) for x in cands if x['linked_to_created_track'])),
          creator_labels=';'.join(sorted(set(x['photon_creator_process'] for x in cands if x['photon_creator_process_recorded']))),
          candidate_creator_process_unrecorded=sum(not x['photon_creator_process_recorded'] for x in cands)))
    summary=dict(case_id=c['id'],material=c['material'],thickness_mm=c['thickness_mm'],variant=c['variant'],seed=c['seed'],
         primaries=n,roi_events=len(roi_ids),outgoing_gamma_rows_from_roi=len(rows),
         outgoing_creator_process_unrecorded=int(np.count_nonzero(~outgoing['_creator_process_recorded'])),
         created_creator_process_unrecorded=int(np.count_nonzero(~created['_creator_process_recorded'])),
         roi_outgoing_gamma_creator_process_unrecorded=sum(not x['photon_creator_process_recorded'] for x in rows),
         roi_events_with_outgoing_gamma=sum(bool(events.get(ev)) for ev in roi_ids),
         roi_events_with_secondary_outgoing_gamma=sum(any(x['secondary_gamma'] for x in events.get(ev,[])) for ev in roi_ids),
         roi_events_with_60_110keV_secondary_outgoing_gamma=sum(any(x['candidate_60_110keV'] for x in events.get(ev,[])) for ev in roi_ids),
         roi_events_with_matched_created_candidate=sum(any(x['candidate_60_110keV'] and x['linked_to_created_track'] for x in events.get(ev,[])) for ev in roi_ids))
    return summary,rows,one_per_event


def csvwrite(path,rows,cols):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)


def run(workspace:Path,output:Path,unit:str,lo:float,hi:float):
    workspace=workspace.expanduser().resolve();output=output.expanduser().resolve()
    if output==workspace or workspace in output.parents:raise ValueError('Output must be outside the original workspace')
    if output.exists():raise FileExistsError(f'Refusing to overwrite existing result: {output}')
    manifest=json.loads((workspace/'manifest.json').read_text(encoding='utf-8'))
    if len(manifest.get('cases',[]))!=36:raise ValueError('Expected complete 36-run Phase 1.2 campaign')
    conv={'MeV':1000.0,'keV':1.0}[unit]
    summaries=[];particles=[];roi_events=[]
    for j,c in enumerate(manifest['cases'],1):
        path=workspace/'runs'/c['id']
        if not (path/'validated.json').exists():raise FileNotFoundError(f'Missing completed validated.json: {path}')
        print(f'[LINK {j}/36] {c["id"]}',flush=True)
        s,part,ev=analyze_case(c,path,conv,lo,hi)
        summaries.append(s);particles.extend(part);roi_events.extend(ev)
    output.mkdir(parents=True,exist_ok=False)
    sum_cols=list(summaries[0]);evt_cols=list(roi_events[0]) if roi_events else [
       'case_id','material','thickness_mm','variant','seed','event_id','deposited_keV','n_outgoing_gamma_rows',
       'n_unique_outgoing_secondary_gamma_tracks','n_candidate_energy_rows','n_matched_created_candidate_tracks','creator_labels','candidate_creator_process_unrecorded']
    particle_cols=['case_id','material','thickness_mm','variant','seed','run_id','event_id','track_id','parent_id',
       'deposited_keV','outgoing_gamma_energy_keV','photon_creator_process','production_volume','secondary_gamma',
       'candidate_60_110keV','linked_to_created_track','photon_creator_process_recorded']
    csvwrite(output/'case_summary.csv',summaries,sum_cols)
    csvwrite(output/'roi_events.csv',roi_events,evt_cols)
    csvwrite(output/'roi_outgoing_photons.csv',particles,particle_cols)
    metrics=dict(status='candidate_track_evidence_only',cases=len(summaries),roi_events=len(roi_events),
          outgoing_gamma_rows_from_roi=len(particles),events_with_candidate_60_110keV_secondary_outgoing_gamma=sum(s['roi_events_with_60_110keV_secondary_outgoing_gamma'] for s in summaries),
          ekine_unit_assumed=unit,photon_energy_window_keV=[lo,hi],
          outgoing_creator_process_unrecorded=sum(s['outgoing_creator_process_unrecorded'] for s in summaries),
          created_creator_process_unrecorded=sum(s['created_creator_process_unrecorded'] for s in summaries),
          roi_outgoing_gamma_creator_process_unrecorded=sum(s['roi_outgoing_gamma_creator_process_unrecorded'] for s in summaries),
          caution='Outward actor records + creator-process labels support event-linked candidate analysis, but full event energy accounting and secondary tracking validation remain necessary.')
    (output/'SUMMARY.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
    (output/'README.md').write_text('# Phase 1.2 event-linked secondary gamma screen\n\n'+
         'Results are derived from locally held ROOT PhaseSpaceActor trees and per-event energy CSVs; original files were not modified. '+
         'Zero-length ROOT CreatorProcess char* entries are treated as unavailable, not inferred; see *_unrecorded columns and photon_creator_process_recorded. '+
         'Event and track linkage, energy-unit convention, creator-process identity and crystal boundary classification must be independently checked. '+
         'These are candidate track associations, not proof of atomic X-ray escape.\n',encoding='utf-8')
    print(json.dumps(metrics,indent=2))
    print(f'Output: {output}')
    return metrics


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workspace',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--ekine-unit',choices=['MeV','keV'],required=True,help='Set only after checking local GATE phase-space native unit (GATE usually MeV).')
    ap.add_argument('--candidate-min-keV',type=float,default=60.0)
    ap.add_argument('--candidate-max-keV',type=float,default=110.0)
    a=ap.parse_args()
    if not (0<a.candidate_min_keV<a.candidate_max_keV):raise ValueError('Invalid candidate interval')
    run(a.workspace,a.output,a.ekine_unit,a.candidate_min_keV,a.candidate_max_keV)

if __name__=='__main__':main()
