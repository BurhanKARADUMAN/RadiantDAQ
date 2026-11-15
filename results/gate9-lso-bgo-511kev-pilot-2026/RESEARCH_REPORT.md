# RadiantDAQ - GATE 9.4 511-keV Gamma Transport Pilot

**Author:** Burhan Karaduman | Middle East Technical University, Physics  
**Dataset:** 30,000 GATE 9.4 gamma primary histories from user-executed runs (November 2026)  
**Evidence level:** Geant4/GATE **radiation transport**, *not* optical transport, readout simulation, laboratory measurement, or clinical PET performance.  
**Geometry:** Monoenergetic 511-keV gammas aimed along +z at an isolated 3 x 3 mm crystal; length 10, 20 or 30 mm. Materials BGO and LSO, `emstandard_opt3` physics list, 5,000 independent primary events per configuration, one random seed per configuration. Original GATE ROOT records are on the user's WSL computer; this package contains the **derived event-level CSV** supplied by the user, not the original ROOT files.

## Executive findings

1. **Transport chain verified upstream:** Prior 200-gamma smoke test demonstrated that `attachCrystalSDnoSystem` yielded nonempty GATE ROOT `Hits`, with 223 hit-step entries and 59.619392 MeV total energy, agreeing with the crystal DoseActor sum (59.6194 MeV). This is an upstream local-run check reported by the user; the original ROOT file was not uploaded in this batch.
2. **All six pilot CSVs are internally consistent:** every input includes 5,000 per-primary energy deposits, and computed counts, means and sums agree with the uploaded run-metrics file.
3. **BGO has a higher interaction fraction** in all tested crystal lengths. At 30 mm: 92.92% for BGO and 90.74% for LSO, difference +2.18 percentage points (approx. independent-binomial 95% CI +1.11 to +3.25 percentage points).
4. **BGO has more near-full energy-deposition events** under the 490-520 keV event rule. At 30 mm: 55.98% BGO, 47.36% LSO, difference +8.62 percentage points (approx. unadjusted 95% CI +6.67 to +10.57 percentage points).
5. **Diminishing length returns:** Increasing thickness 20 -> 30 mm raises the near-full fraction by +4.02 percentage points for BGO, +3.90 for LSO, much smaller than the 10 -> 20 mm changes (+16.20 and +14.04 percentage points).

## Primary results

All fractions below use **5,000 incident collimated gamma histories as denominator**. Interaction = event total energy deposited in crystal > 0 keV. Near-full = event energy deposited between 490 and 520 keV (effectively 511 keV in this idealized, unbroadened transport model). Conditional near-full = near-full / interacting.

| Material | Crystal length (mm) | Interacting / 5000 | Interaction (%) | Near-full / 5000 | Near-full (%) | Near-full / interacting (%) | Mean Edep / incident gamma (keV) |
|:--|--:|--:|--:|--:|--:|--:|--:|
| BGO | 10 | 2968 | 59.36 | 1788 | 35.76 | 60.24 | 225.57 |
| BGO | 20 | 4181 | 83.62 | 2598 | 51.96 | 62.14 | 321.96 |
| BGO | 30 | 4646 | 92.92 | 2799 | 55.98 | 60.25 | 353.29 |
| LSO | 10 | 2798 | 55.96 | 1471 | 29.42 | 52.57 | 194.75 |
| LSO | 20 | 4056 | 81.12 | 2173 | 43.46 | 53.57 | 287.11 |
| LSO | 30 | 4537 | 90.74 | 2368 | 47.36 | 52.19 | 317.14 |

## Material contrast with approximate 95% confidence intervals

Each row compares independent BGO and LSO binomial proportions with **an unadjusted normal-approximation interval for the difference** (not a systematic uncertainty interval, not corrected for six simultaneous comparisons). Individual proportions use Wilson score intervals in `data/validated_metrics.csv`.

| Length | BGO - LSO interaction (pp) | Approx. 95% CI (pp) | BGO - LSO near-full (pp) | Approx. 95% CI (pp) |
|--:|--:|:--|--:|:--|
| 10 mm | +3.40 | +1.46 to +5.34 | +6.34 | +4.51 to +8.17 |
| 20 mm | +2.50 | +1.01 to +3.99 | +8.50 | +6.55 to +10.45 |
| 30 mm | +2.18 | +1.11 to +3.25 | +8.62 | +6.67 to +10.57 |

### Spectrum interpretation

- The peak exactly at approximately **511 keV** means full physical energy has been deposited in the scored crystal. The strong narrow peak **must not** be described as an SiPM energy-resolution photopeak: no photon-statistical broadening, photosensor/electronics model, or energy calibration was applied to these transport CSVs.
- The prominent **zero-energy** component is expected because the histogram counts all primaries, including those that passed through without any scored crystal deposition. The main spectrum is normalized per incident gamma, *not* per triggered event.
- The BGO runs contain a minor structure near **420 keV** (400-440 keV counts: 71, 94, 90 for 10, 20, 30 mm respectively; LSO: 0, 0, 2). One plausible physical explanation is escape of a characteristic X ray, but this cannot be established from total-energy CSVs alone. Inspect GATE secondaries / emission energies and process names before using that label.
- The 511-keV values differ by a few 1e-5 keV due to floating-point bookkeeping; none of the 30,000 events exceeded 511.1 keV.

## Quality assurance and reproducibility

- Original inputs: six `*_energy_per_primary_keV.csv` files, `run_metrics_original.csv`, `analysis_metadata_original.json`, two original plots.
- `scripts/validate_and_plot.py` reads the files and asserts correct sample counts, physical numerical bounds and equality with the uploaded `run_metrics_original.csv` (to the precision of the exported values).
- Script regenerates `validated_metrics.csv`, `material_differences.csv`, confidence-interval plots and the mean-energy plot. `python scripts/validate_and_plot.py` from **any working directory** is supported.
- Sample size supports comparisons of binomial variability under *this model and beam geometry*. There is **one stochastic GATE execution per configuration**; between-run reproducibility and material/physics systematic effects have not been quantified.
- The GATE source, material database and physics configuration were not independently rerun in this analysis environment. To independently reproduce from first principles, archive original `run.mac`, `run.log`, `metadata.json`, `hits.root`, `scoring-Edep.mhd/.raw`, and GATE/Geant4 version and materials DB hashes.

## Limitations: do not overclaim

- **Not PET sensitivity or detection efficiency:** the mono-directional source is deliberately aligned with the crystal. No angular distribution, patient attenuation, ring geometry, dead time, or electronics threshold is included.
- **Not photopeak energy resolution:** event energy deposition is not equivalent to the measured charge or reconstructed energy, and no broadening has been applied.
- **Not coincidence time resolution (CTR):** no scintillation kinetics, optical transport, SiPM SPTR, discriminator, TDC, or true coincidence pairs are simulated here.
- **Not a calibrated SiPM/PMT sensor study or clinical dose study.**
- Results are specific to the chosen GATE material composition, physics configuration, cuts, 3 x 3 mm cross-section and normal-incidence collimated source. Larger detector arrays and optical models can alter design trade-offs.
- The source and material input files on the user's WSL machine should be preserved before the results are considered independently reproducible.

## Recommended research progression

1. **Reproducibility check:** run the six scenarios again with 2-3 different seeds and report within-condition variance / pooled Wilson intervals, preserving existing outputs.
2. **Geometry and transport checks:** vary crystal cross-section (2 x 2, 3 x 3, 4 x 4 mm), source beam angle, 511-keV energy acceptance definition, and compare simple attenuation trends with independent reference calculations such as NIST XCOM; confirm GATE material DB composition and density.
3. **Event-process audit:** read `processName`, `PDGEncoding`, secondary trajectories and atomic deexcitation records in ROOT for the ~420-keV BGO structure.
4. **Optical simulation:** introduce scintillation emission, optical properties of crystal/wrapping/coupling, interface and photon collection, recording photon arrival times at a defined SiPM plane; verify optical physics is enabled and fully configured. Current `OpticalData` is not a validated optical result.
5. **Sensor & DAQ:** map collected photons to the separate synthetic SiPM model with calibrated PDE, microcell saturation, dark noise, afterpulsing and SPTR. Derive threshold and CFD timestamps from **the same** sensor waveforms, then compare simulated response with measured waveforms.

## External technical sources (context, not calibration)

- GATE 9.4 sensitive detector concepts: https://opengate.readthedocs.io/en/latest/sensitive_detector_concept.html
- GATE 9.4 digitizer and readout: https://opengate.readthedocs.io/en/v9.4/digitizer_and_detector_modeling.html
- Cherenkov Radiation-Based Coincidence Time Resolution Measurements in BGO Scintillators (Frontiers in Physics, 2022): https://doi.org/10.3389/fphy.2022.816384
- BGO/LYSO detector performance comparison (open-access): https://pmc.ncbi.nlm.nih.gov/articles/PMC8665694/

These external studies discuss scintillation and timing properties that the **current transport-only** simulation has not modeled. BGO's higher intrinsic interaction probability does not, by itself, imply it is the optimum TOF-PET material.
