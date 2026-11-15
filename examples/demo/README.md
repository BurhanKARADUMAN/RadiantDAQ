# Synthetic example results

**Generated, not measured.** These examples were generated from the RadiantDAQ Python model on 15 November 2026 with the documented seeds. They are not PET/SiPM laboratory recordings, nor GATE Monte Carlo transport outputs.

Reproduce them:

```bash
radiantdaq demo --events 1600 --seed 2026 --out examples/demo
radiantdaq sweep --events 1100 --seed 2026 --out examples/demo
```

- `summary.json` stores the event summary and full configuration.
- `event_level_synthetic.csv` contains individual modeled true-pair observables.
- `sample_waveform.csv` is a separate illustrative voltage trace.
- `synthetic_parameter_sweep.csv` stores two parameter sensitivity studies.

Results (and apparent precision) depend on the chosen simplified model; they are not validated instrumentation specifications.
