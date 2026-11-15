#!/usr/bin/env python3
"""Reproduce RadiantDAQ GATE9 pilot summary from six user-produced event CSVs.

Scientific scope: 511-keV monoenergetic collimated gamma transport ONLY.
Does not infer SiPM resolution, optical PDE, clinical PET sensitivity, CTR, or dose.
Requires numpy, matplotlib. All outputs are data-derived; no model-generated hits.
"""
from pathlib import Path
import csv
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
FIGURES = BASE / 'figures'
N = 5000
ENERGY = 511.0


def wilson(k, n, z=1.95996398454):
    p = k/n
    d = 1+z*z/n
    center = (p+z*z/(2*n))/d
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return center-half, center+half


def validate():
    original = list(csv.DictReader((DATA/'run_metrics_original.csv').open(newline='', encoding='utf-8')))
    assert len(original) == 6, f'Expected 6 runs, found {len(original)}'
    assert {(r['material'],int(r['thickness_mm'])) for r in original} == {(m,t) for m in ('BGO','LSO') for t in (10,20,30)}
    rows=[]
    for r in original:
        key=r['folder']
        p=DATA/f'{key}_energy_per_primary_keV.csv'
        if not p.is_file(): raise FileNotFoundError(p)
        a=np.loadtxt(p,skiprows=1,delimiter=',',ndmin=1)
        assert len(a)==N==int(r['n_primaries']),key
        assert np.isfinite(a).all() and min(a) >= -1e-7 and max(a)< 511.1,key
        interaction=int(np.count_nonzero(a>1e-8))
        near=int(np.count_nonzero((a>=490)&(a<=520)))
        assert interaction==int(r['n_interacting']),(key,'interaction',interaction)
        assert near==int(r['n_near_full_energy']),(key,'near_full',near)
        assert abs(np.sum(a)/1000-float(r['sum_edep_all_events_mev']))<1e-5,key
        assert abs(np.mean(a)-float(r['mean_deposited_energy_per_incident_kev']))<1e-5,key
        low_i,high_i=wilson(interaction,N)
        low_f,high_f=wilson(near,N)
        rows.append(dict(material=r['material'],thickness_mm=int(r['thickness_mm']),seed=int(r['seed']),
                         primaries=N,n_interacting=interaction,n_near_full_energy=near,
                         p_interaction=interaction/N,interaction_ci_low=low_i,interaction_ci_high=high_i,
                         p_full=near/N,full_ci_low=low_f,full_ci_high=high_f,
                         p_full_given_interaction=near/interaction,
                         mean_edep_kev=float(np.mean(a)),sum_edep_mev=float(np.sum(a)/1000),
                         edep_gt_511p1_kev=int(np.sum(a>511.1)),
                         n_400_to_440_keV=int(np.sum((a>=400)&(a<440)))))
    return sorted(rows,key=lambda r:(r['material'],r['thickness_mm']))


def differences(rows):
    out=[]
    for thickness in (10,20,30):
        a=next(x for x in rows if x['material']=='BGO' and x['thickness_mm']==thickness)
        b=next(x for x in rows if x['material']=='LSO' and x['thickness_mm']==thickness)
        for label,key in [('interaction','p_interaction'),('near_full','p_full')]:
            d=a[key]-b[key]
            se=math.sqrt(a[key]*(1-a[key])/N+b[key]*(1-b[key])/N)
            out.append(dict(thickness_mm=thickness,metric=label,bgo=a[key],lso=b[key],
                            difference_pp=d*100,ci95_low_pp=(d-1.95996398454*se)*100,
                            ci95_high_pp=(d+1.95996398454*se)*100,
                            approximation='Unadjusted Wald CI; independent binomial histories; no systematics'))
    return out


def write_csv(file, rows):
    with file.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)


def plotting(rows,diffs):
    FIGURES.mkdir(parents=True,exist_ok=True)
    for label, val, low, high, ytitle, fname in [
        ('Interaction','p_interaction','interaction_ci_low','interaction_ci_high','Fraction of incident gammas with Edep > 0','interaction_fraction_with_95ci.png'),
        ('Near-full deposition','p_full','full_ci_low','full_ci_high','Fraction of incident gammas depositing 490-520 keV','near_full_fraction_with_95ci.png')
    ]:
        fig,ax=plt.subplots(figsize=(8.8,5.2))
        for material in ('BGO','LSO'):
            q=[r for r in rows if r['material']==material]
            x=np.array([r['thickness_mm'] for r in q])
            y=np.array([r[val] for r in q])
            lo=np.array([r[low] for r in q]); hi=np.array([r[high] for r in q])
            ax.errorbar(x,y,yerr=[y-lo,hi-y],label=material,marker='o',capsize=4,linewidth=2)
        ax.set_xlabel('Crystal thickness along incident beam (mm)')
        ax.set_ylabel(ytitle)
        ax.set_title('GATE 9.4 | 511-keV collimated gamma transport | '+label)
        ax.set_xticks([10,20,30]);ax.set_ylim(0,1.03);ax.legend();ax.grid(alpha=0.20)
        fig.tight_layout();fig.savefig(FIGURES/fname,dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.8,5.0))
    for name in ('interaction','near_full'):
        q=[r for r in diffs if r['metric']==name]
        x=np.array([r['thickness_mm'] for r in q])+( -0.35 if name=='interaction' else 0.35)
        y=np.array([r['difference_pp'] for r in q])
        lo=np.array([r['ci95_low_pp'] for r in q]);hi=np.array([r['ci95_high_pp'] for r in q])
        ax.errorbar(x,y,yerr=[y-lo,hi-y],marker='o',capsize=4,linestyle='-',label=name)
    ax.axhline(0,linewidth=1,linestyle='--')
    ax.set_xticks([10,20,30]); ax.set_xlabel('Crystal thickness along incident beam (mm)')
    ax.set_ylabel('BGO minus LSO, percentage points')
    ax.set_title('Difference between materials | Unadjusted 95% CI')
    ax.legend();ax.grid(alpha=.2);fig.tight_layout()
    fig.savefig(FIGURES/'bgo_minus_lso_95ci.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.8,5.0))
    for material in ('BGO','LSO'):
        q=[r for r in rows if r['material']==material]
        ax.plot([r['thickness_mm'] for r in q],[r['mean_edep_kev'] for r in q],marker='o',label=material)
    ax.set_xlabel('Crystal thickness along incident beam (mm)')
    ax.set_ylabel('Mean deposited energy / incident gamma (keV)')
    ax.set_title('GATE 9.4 | Mean energy deposition (including zero events)')
    ax.set_xticks([10,20,30]);ax.grid(alpha=.2);ax.legend();fig.tight_layout()
    fig.savefig(FIGURES/'mean_edep_vs_thickness.png',dpi=180);plt.close(fig)


def main():
    rows=validate();diffs=differences(rows)
    write_csv(DATA/'validated_metrics.csv',rows)
    write_csv(DATA/'material_differences.csv',diffs)
    plotting(rows,diffs)
    meta=dict(origin='User-supplied GATE9.4-derived event CSVs, November 2026',
              exact_original_files='six energy_per_primary_keV CSVs + run_metrics_original.csv',
              checks='each 5000 events; event energy physical range; aggregate totals, counts, means checked',
              uncertainty='Wilson score 95% for individual proportions; unadjusted Wald 95% for pairwise material differences',
              scientific_limits=['ideal collimated gamma geometry','one random seed per parameter combination',
                                 'no optical photons, sensor PDE, readout electronics or measurements',
                                 'no estimates of energy FWHM, CTR, scanner sensitivity or clinical performance'])
    (DATA/'validation_metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Validated', len(rows), 'GATE-derived datasets:',sum(r['primaries'] for r in rows),'primaries')
    for r in rows:print(r['material'],r['thickness_mm'],'n_int',r['n_interacting'],'n_full',r['n_near_full_energy'])
    return rows,diffs

if __name__=='__main__': main()
