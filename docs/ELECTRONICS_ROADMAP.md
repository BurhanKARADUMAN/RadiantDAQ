# Readout electronics and DAQ engineering roadmap

## Target architectural concept

```text
Gamma 511 keV → Scintillator → SiPM (Geiger avalanches)
                                 ├→ fast analog path → discriminator / CFD → TDC → coincidence timestamps
                                 └→ charge path → shaping / integrator → ADC → energy estimator
                                               ↓
                                       event-builder / DAQ
                                               ↓
                                     calibration and analysis
```

### Phase A — signal-chain simulation

Replace the current impulse model with a validated SiPM current source and equivalent circuit. Incorporate microcell recovery, correlated noise, gain/bias variation, photon transit-time spread and experimentally grounded pulse parameters.

### Phase B — timing + charge frontend

Define separate analog timing and charge paths. Document sampling, analog bandwidth, reference thresholds, saturation/ADC dynamic range, trigger dead time, temperature drift, and safety. Prefer CFD or offline time-walk correction *after* demonstrating and measuring the baseline leading-edge approach.

### Phase C — digital readout

Develop a timestamped event record with a clear schema:

| Field | Description |
|---|---|
| `channel_id` | Detector identity |
| `timestamp_raw` | Counter / TDC units |
| `timestamp_ns` | Calibrated timestamp |
| `integrated_charge` | Baseline-subtracted charge, arbitrary or calibrated units |
| `energy_kev` | Energy only after calibration |
| `quality_flags` | Saturation, pileup, invalid threshold, etc. |
| `run_id / config_hash` | Reproducibility |

**Open hardware choices:** STM32/TDC/FPGA design options are not yet selected. Do not claim sub-nanosecond resolution from MCU timer clock speed alone. Real CTR depends on the entire detector/electronics chain.

### Phase D — PET module integration

Move from two synthetic 511-keV full-energy interactions to Geant4/GATE event transport, optical coupling, position readout, energy windows, scatter and random event modeling. Benchmark CTR, energy FWHM, detection efficiency, dead time and eventually spatial imaging metrics.
