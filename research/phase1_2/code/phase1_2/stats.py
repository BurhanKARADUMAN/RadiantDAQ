#!/usr/bin/env python3
"""Descriptive model-sensitivity statistics for *actual* GATE9 primary histories.

No claim of systematic error bars from alternate physics models; run-to-run variation
is separate from conditional Monte Carlo sampling uncertainty.
"""
from __future__ import annotations
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

Z=1.959963984540054


def wilson(k:int,n:int):
    if not 0<=k<=n or n<1:raise ValueError('Invalid binomial numerator/denominator')
    p=k/n
    den=1+Z*Z/n
    midpoint=(p+Z*Z/(2*n))/den
    half=Z/den*math.sqrt(p*(1-p)/n+Z*Z/(4*n*n))
    return (0.0 if k == 0 else max(0.0,midpoint-half)), (1.0 if k == n else min(1.0,midpoint+half))


def aggregate(rows:list[dict]):
    groups=defaultdict(list)
    for r in rows:groups[(r['material'],int(r['thickness_mm']),r['variant'])].append(r)
    totals=[]
    for (m,t,v),group in sorted(groups.items()):
        n=sum(int(r['n_primaries']) for r in group)
        record=dict(material=m,thickness_mm=t,variant=v,n_replicates=len(group),n_primaries=n)
        for metric,col in [('interaction','n_interaction'),('near_full','n_nearfull'),('roi_400_440','n_400_440')]:
            k=sum(int(r[col]) for r in group)
            lo,hi=wilson(k,n)
            record[f'{metric}_count']=k
            record[f'{metric}_fraction']=k/n
            record[f'{metric}_wilson95_low']=lo
            record[f'{metric}_wilson95_high']=hi
            vals=[int(r[col])/int(r['n_primaries']) for r in group]
            record[f'{metric}_between_seed_sample_sd_pp']=100*statistics.stdev(vals) if len(vals)>1 else float('nan')
        totals.append(record)
    return totals


def contrasts(pooled:list[dict]):
    by={(p['material'],p['thickness_mm'],p['variant']):p for p in pooled}
    keys=sorted({(t,v) for m,t,v in by})
    result=[]
    for t,v in keys:
        a,b=by.get(('BGO',t,v)),by.get(('LSO',t,v))
        if a is None or b is None:continue
        for metric in ('interaction','near_full','roi_400_440'):
            p1,p2=a[f'{metric}_fraction'],b[f'{metric}_fraction']
            n1,n2=a['n_primaries'],b['n_primaries']
            se=math.sqrt(p1*(1-p1)/n1+p2*(1-p2)/n2)
            difference=p1-p2
            result.append(dict(thickness_mm=t,variant=v,metric=metric,
                               BGO_minus_LSO_pp=difference*100,
                               approx_unadjusted_wald95_low_pp=(difference-Z*se)*100,
                               approx_unadjusted_wald95_high_pp=(difference+Z*se)*100,
                               note='Conditional sampling CI only; not multiple-testing adjusted or physical systematic uncertainty'))
    return result


CONTRAST_COLUMNS = [
    'thickness_mm', 'variant', 'metric', 'BGO_minus_LSO_pp',
    'approx_unadjusted_wald95_low_pp', 'approx_unadjusted_wald95_high_pp', 'note'
]


def write_records(path:Path,records:list[dict],columns=None):
    if not records and columns is None:
        raise ValueError('No records to write and no explicit header columns')
    fields = list(columns) if columns is not None else list(records[0])
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='raise')
        w.writeheader()
        w.writerows(records)


def make_plots(pooled:list[dict],destination:Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for metric,label in [('interaction','P(any crystal Edep)'),('near_full','P(490–520 keV crystal Edep)'),('roi_400_440','P(400–440 keV crystal Edep)')]:
        fig,ax=plt.subplots(figsize=(8.2,5.0))
        for m in ('BGO','LSO'):
            pts=sorted((p for p in pooled if p['material']==m and p['variant']=='baseline'),key=lambda p:p['thickness_mm'])
            if not pts:continue
            xx=[p['thickness_mm'] for p in pts]; yy=[100*p[f'{metric}_fraction'] for p in pts]
            low=[100*(p[f'{metric}_fraction']-p[f'{metric}_wilson95_low']) for p in pts]
            high=[100*(p[f'{metric}_wilson95_high']-p[f'{metric}_fraction']) for p in pts]
            ax.errorbar(xx,yy,yerr=[low,high],fmt='o-',capsize=4,label=m)
        ax.set_xlabel('Crystal length (mm)');ax.set_ylabel('Fraction of incident primaries (%)')
        ax.set_title(label+' — GATE transport, baseline only')
        ax.legend();ax.grid(alpha=0.2);fig.tight_layout()
        fig.savefig(destination/f'{metric}_baseline_wilson95.png',dpi=220)
        fig.savefig(destination/f'{metric}_baseline_wilson95.pdf')
        plt.close(fig)


def write_analysis(rows:list[dict],output:Path):
    pooled=aggregate(rows);differences=contrasts(pooled)
    write_records(output/'pooled_conditions.csv',pooled)
    write_records(output/'material_differences.csv',differences,columns=CONTRAST_COLUMNS)
    make_plots(pooled,output)
    n_reps = sorted({int(p['n_replicates']) for p in pooled})
    (output/'STATISTICAL_INTERPRETATION.md').write_text(
        '# Phase 1.2 model-sensitivity statistical summary\n\n'
        'This file is generated from **actually completed GATE runs** after validation. '
        f'Observed replicate counts per condition: {n_reps}. A single seed cannot estimate '
        'between-seed variation; even two seeds per condition do not permit a precise variance estimate. Wilson 95% intervals are **conditional primary-sampling intervals**, '
        'not model-form systematic uncertainty. Material contrasts appear only for matched BGO/LSO conditions. If no matched condition exists, material_differences.csv is header-only. Available contrasts use unadjusted Wald intervals and are '
        'not multiplicity-corrected. Geometry tilt modifies beam-incidence conditions; interpret separately. '
        'Optical, SiPM, detector CTR and experimental metrics are not simulated here.\n',encoding='utf-8')
    return pooled,differences
