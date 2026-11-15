# RadiantDAQ Phase 1.1 — GATE 9.4 raw audit and multi-seed review

**Status (2026-11-15):** The author reports a successful read-only WSL recheck of all 18 original ROOT `Hits` and DoseActor RAW files (90,000 incident 511-keV gamma histories). The full generated audit artifacts are retained on the author's WSL system until explicitly published via `publish_branch_safe.sh`. The published files are **derived outputs**, not the large original ROOT/RAW files or laboratory measurements.

**Scientific distinction:** An internally consistent audit is not an experimental validation, a Geant4 physics-systematics study, or evidence of a characteristic X-ray escaping the crystal. The 400–440 keV region contains 726 BGO and 4 LSO events in the full 90k campaign; particle creation and boundary-crossing tracking is required to establish the feature's origin.

## Contents

- `raw_audit.py`: re-read and independently compare original GATE ROOT Hits, exported per-primary CSV, DoseActor MetaImage and archived file hashes. Read-only inputs.
- `tests/test_raw_audit.py`: 10 automated tests including material-database hash-key regression and mismatch rejection.
- `review/`: separate scientific review of the uploaded 90k summary ZIP and its per-run CSV tables (not the original raw-level output).
- `AUDIT_EXECUTION_STATUS.md`: provenance of WSL terminal-output observation.
- `publish_branch_safe.sh`: creates **only** a new review branch and a new results folder in a fresh clone. Reads additional raw-audit derived results from the author's WSL output directory.

## WSL: independent raw-audit reproduction

```bash
source "$HOME/bragg_venv/bin/activate"
python -m pip install -r requirements.txt
python -m pytest -q tests/test_raw_audit.py
# Choose a new output folder, never overwrite the archived run:
python raw_audit.py \
  --workspace "$HOME/radiantdaq_phase1_multiseed_2026" \
  --output "$HOME/radiantdaq_phase1_1_raw_audit_recheck_NEW"
```

This requires original 18 ROOT and RAW files, and a matching `GateMaterials.db`. Original campaign files are not modified.

## Publishing (from the author's WSL system)

```bash
source "$HOME/bragg_venv/bin/activate"
bash publish_branch_safe.sh
```

The script requires the prior run's **existing** output folder `~/radiantdaq_phase1_1_raw_audit_2026`, verifies its summaries, then clones GitHub into a **new** directory and pushes exclusively to `research/phase1-raw-audit-2026`. It refuses to overwrite any existing publishing directory or target branch and never pushes to `main`. It includes five small derived audit files, not raw ROOT/RAW.

## Interpretation limits

- ROOT hit-step `processName` and `parentID` are not proof of a escaping secondary from the crystal.
- A `511 keV - deposited energy` deficit is not a directly measured escaped-photon energy.
- Sampling variability, physics model/systematic uncertainty and laboratory measurement error are distinct.
- This campaign does not simulate scintillation optical transport, SiPM signals, energy resolution, CTR or PET scanner sensitivity.

## Base

- Repository: https://github.com/BurhanKARADUMAN/RadiantDAQ
- Original verified pilot commit: `3a10db4d1519cf97e1dad898b0bb21dbad4a1ec5`
- Review folder target: `results/gate9-lso-bgo-511kev-phase1-1-raw-audit-2026/`
