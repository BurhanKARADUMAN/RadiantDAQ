#!/usr/bin/env python3
"""NIST XCOM attenuation plausibility calculation with mandatory attributed inputs.

NOT a substitute for Geant4 energy deposition: exponential attenuation describes
interactions in an ideal pencil beam; coherent scattering and secondary escape
make P(positive Edep) different from P(any photon interaction).
"""
import argparse
import json
import math
from pathlib import Path


def probability(mu_mass_cm2_g, density_g_cm3, thickness_mm):
    vals=[mu_mass_cm2_g,density_g_cm3,thickness_mm]
    if not all(type(x) in (float,int) and math.isfinite(float(x)) and x>0 for x in vals):
        raise ValueError('Positive finite NIST attenuation coefficient, density, length required')
    return -math.expm1(-mu_mass_cm2_g*density_g_cm3*(thickness_mm/10.0))


def run(data:dict):
    rows=[]
    for name,mat in data['materials'].items():
        source=mat.get('source_url')
        if not isinstance(source,str) or not source.startswith(('https://','http://')):
            raise ValueError('Source URL for NIST/XCOM attenuation inputs required')
        p=probability(mat['mass_attenuation_cm2_g'],mat['density_g_cm3'],mat['thickness_mm'])
        rows.append({'material':name,'estimated_interaction_probability_ideal_beam':p,
                     'not_equivalent_to_crystal_energy_deposition_fraction':True,
                     'source_url':source})
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    result=run(json.loads(a.input.read_text()))
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Computed NIST coefficient-based *attenuation* sanity check (not detector efficiency).')

if __name__=='__main__':main()
