# RadiantDAQ: GATE 9.4 transport diagnosis, sensitivity study and optical readiness

**Research status (15 November 2026):** Phase 1 pilot and Phase 1.1 multi-seed RAW audit were executed by the author. **Phase 1.2 and Phase 2 included in this package are code and preflight plans only, not simulated results.**

## Baseline and scientific question

- Radiation: normally incident, collimated 511-keV gamma from z = -50 mm to a single 3 × 3 × (10/20/30) mm BGO or LSO crystal.
- Transport baseline: GATE 9.4 / Geant4 11.2.2, `emstandard_opt3`, a single-crystal `DoseActor`, and a ROOT `Hits` tree with `attachCrystalSDnoSystem`.
- Existing data: 30,000 gamma pilot + 90,000 independent-seed Phase 1 = 120,000 historical primaries, without claiming that the original pilot's binary artifacts have been reverified in the new environment.
- Observed ROI: 726 of 45,000 new BGO primaries vs 4 of 45,000 LSO primaries have crystal Edep in 400–440 keV. This remains a **spectral structure, not a proven fluorescence escape peak**.

## Phase 1.2 questions and experimental design

The six baseline crystal configurations are retained. Six additional one-factor-at-a-time variants are evaluated for **20-mm** BGO and LSO only. All seeds are distinct. The default full campaign is 36 runs × 5,000 primaries = **180,000 NEW gamma histories**, with two independently seeded runs per configuration. More histories may be needed to resolve rare spectral features precisely.

| Variant | Change from pilot-like gamma baseline | Scientific role |
|---|---|---|
| `baseline` | Added outgoing and created-particle phase-space recording only | Actor sanity check and fixed reference |
| `emopt4` | `emstandard_opt4` instead of `opt3` | Geant4 EM model dependence |
| `livermore` | `emlivermore` instead of `opt3` | Low-energy EM physics dependence |
| `cut_0p05mm` | Gamma/electron/positron crystal range cuts 0.05 mm | Secondary production threshold dependence |
| `cut_0p5mm` | Gamma/electron/positron crystal range cuts 0.5 mm | Cut sensitivity to a larger threshold |
| `fluo_off` | Explicit `/process/em/fluo false` before initialization | Fluorescence model causal sensitivity, **not proof alone** |
| `tilt_2deg` | Collimated ray rotated by 2° about y, with source shifted to hit crystal center | Beam incidence geometry sensitivity |

### Recording escaped-particle evidence

Two GATE9 `PhaseSpaceActor`s are attached to `crystal`:

1. **Outgoing:** `storeOutgoingParticles true` → `outgoing.root`. This should collect particles exiting the crystal boundary (subject to GATE9 actor semantics, to be verified in the smoke run).
2. **Created:** `storeSecondaries true` → `created.root`, intended to collect secondaries originating inside the crystal.

The 400–440 keV deposited-energy event IDs come from ROOT `Hits`. The phase-space schema inspection explicitly checks which identifiers GATE9 records. Linking outgoing gammas to the same event requires available event ID. Definitive characteristic X-ray attribution further requires production process, particle initial kinetic energy, outgoing kinetic energy, and boundary transition. **If required identifiers are unavailable, the result must remain unclassified.** Any `Ekine` values are reported in native GATE branches until units are independently confirmed.

Potential actor availability differences or command failures are caught by a *real* two-run smoke test. This package cannot emulate GATE 9.4.

### Statistical plan

Analyze P(any Edep), P(490–520 keV), P(400–440 keV) per incident primary. Use Wilson 95% intervals for each proportion, and report unadjusted two-sample differences with explicit caveats. Multiple comparisons and two-seed run-to-run variation must not be conflated with systematic uncertainty. For comparably configured conditions, treat physics-list/cut variation as **model sensitivity**, not an uncertainty distribution unless justified by a formal model of alternative physics assumptions. Pairwise results from two different beam geometries cannot be interpreted solely as scintillator material effects.

### Quality gates

- Preserve historical 120k results and hashes without editing.
- Preflight GATE version, exact materials database SHA, production cut settings and macro diff.
- Run 200-primary smoke for baseline and fluorescence-off variants **before full campaign**.
- Confirm nonempty ROOT `Hits` and usable `outgoing.root` / `created.root` branch schema.
- Verify generated per-event ROOT Edep is at most 511.1 keV. The new validator re-sums the DoseActor MetaImage `.raw` file and compares its deposited-energy total against the new ROOT Hits sum using an explicit tolerance; errors abort execution.
- Archive raw ROOT, MHD/RAW, seeds and GATE logs on WSL; provide a small derived analysis ZIP for review.

## Independent attenuation plausibility (NIST XCOM)

`phase1_2/xcom_sanity.py` provides the ideal-pencil-beam first-interaction attenuation estimate `1 - exp[-(mu/rho) * rho * thickness]`, requiring the author's *actual material density/composition* and a cited NIST XCOM 511-keV mass attenuation coefficient. No numerical coefficients are invented. This estimate is not equal to the crystal's `P(Edep>0)` or 490–520 keV deposition probability; coherent scattering, secondary transport and boundary effects require explicit interpretation. Input template: `phase1_2/xcom_input_TEMPLATE.json`. Source: https://www.nist.gov/pml/xcom-photon-cross-sections-database

## Phase 2 optical readiness (NOT a completed optical simulation)

GATE 9.4 requires compilation with `GATE_USE_OPTICAL=ON` and a populated `Materials.xml`. The source-supported material parameters include `SCINTILLATIONYIELD`, decay constants, emission spectrum, refractive index and absorption length. The property-validator intentionally fails on placeholders and requires a specific citation for **every** supplied optical parameter. See `phase2/optical_parameters_TEMPLATE.json`. This establishes input data provenance; actual crystal surface finishes, reflectors, coupling grease, optical sensor packaging, photon arrival-time distributions and SiPM-PDE must be developed and experimentally cross-checked independently. The optical smoke macro records outgoing photons, not a SiPM response.

Optical photons are not gamma rays; GATE Geant4 10.7 or newer uses PDG encoding -22 for optical photons. Check the actual local build's optical flag, available output branches and run-time log.

## Phase 3 SiPM and electronics milestones

Reuse the existing RadiantDAQ Python SiPM MVP **only as an illustrative model** until: optical arrival time/energy distributions are validated, vendor wavelength-dependent PDE and microcell count are documented, SPTR and correlated noise/crosstalk model is chosen, sensor bias and temperature are specified, and hardware waveforms/calibration exist. Only then derive charge distributions, time walk, leading-edge/CFD timestamps, FWHM and CTR. No PET clinical sensitivity claims from this isolated crystal setup.

## External, versioned references

- GATE 9.4 PhaseSpaceActor `storeOutgoingParticles` / `storeSecondaries`: https://opengate.readthedocs.io/en/v9.4/tools_to_interact_with_the_simulation_actors.html
- GATE 9.4 production cuts: https://opengate.readthedocs.io/en/v9.4/cut_and_variance_reduction_technics.html
- GATE 9.4 physics lists: https://opengate.readthedocs.io/en/v9.4/setting_up_the_physics.html
- Geant4 atomic deexcitation and fluorescence commands: https://geant4.web.cern.ch/documentation/pipelines/master/bfad_html/ForApplicationDevelopers/TrackingAndPhysics/physicsProcess.html
- GATE 9.4.1 optical photon transport and `Materials.xml`: https://opengate.readthedocs.io/en/v9.4.1/generating_and_tracking_optical_photons.html
