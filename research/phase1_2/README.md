# Phase 1.2 — Scintillator gamma transport and fluorescence-control study

This directory is an **additive, reviewed research archive** for RadiantDAQ's GATE 9.4 / Geant4 11.2.2 work. It does not modify prior Phase 1.1 results or the simulator's top-level package. **Derived data only**: native GATE ROOT files and the complete 180k raw histories are not included in Git.

## Experimental configurations

- Transport sensitivity: **36 × 5,000 = 180,000 incident 511-keV gamma histories**, BGO and LSO 3 × 3 mm crystals at 10/20/30 mm, with model/cut/geometry sensitivity variations. Not an experimental detector measurement.
- Independently checked fluorescence contrast: **BGO 3 × 3 × 20 mm**, same source setup, two independent seeds per condition, 10,000 primaries/seed, **40,000 incident gammas** total. The global and world fluorescence flags remain ON; the *crystal-region* fluorescence flag is ON vs OFF, with Auger and PIXE flags held ON. Deexcitation-region override happens after GATE initialization and before event transport, with region flags checked at transport.
- Event-linked evidence: 327 ROI events in the ON set (400–440 keV deposited) and 327 outgoing 60–110 keV gamma tracks linked by event and track IDs; independent QA on derived CSVs.

## Confirmed comparison (40k fluorescence control)

| Condition | Primaries | Edep 400–440 keV | Fraction | Edep 490–520 keV |
|:--|--:|--:|--:|--:|
| Crystal fluorescence OFF | 20,000 | 0 | 0.000% | 10,433 |
| Crystal fluorescence ON | 20,000 | 327 | 1.635% | 10,216 |

Two-sided Fisher exact test of aggregated event counts: **p ≈ 1.91 × 10⁻⁹⁹** (event-level Bernoulli approximation; paired RNG seeds do not ensure path-by-path matches). ON 400–440 keV Wilson 95% CI: 1.468–1.820%; OFF: 0–0.0192%. These are model-conditional statistical calculations, not estimates of experimental precision or simulation physics systematics.

Within the 327 selected ON ROI events, **327/327 have one event-linked outgoing secondary gamma track** in the 60–110 keV window; 327/327 have matched created-track records in the earlier source-derived results, and event-wise `511 − Edep − Eout` closure has maximum absolute residual **1.50 × 10⁻⁵ keV** assuming GATE ROOT `Ekine` is in MeV. `CreatorProcess` distribution: `phot` = 324, `compt` = 3; neither identifies a Bi atomic transition directly. Energy structure and fluorescence dependence strongly support characteristic X-ray escape as the origin of a substantial part of the 420–424 keV feature, **not** a uniquely proven Bi Kβ line assignment.

## Important control correction

The **earlier Phase 1.2 campaign variant named `fluo_off` was not a valid fluorescence-OFF control**: its *post-init global parameter* was still ON. The 36-run campaign tables are retained transparently as historical sensitivity data but **must not** be used to claim a verified fluorescence contrast. Only the subsequent 40k **region-specific** ON/OFF study is used for that contrast.

## Contents

- `data/transport`: Phase 1.2 36-run derived metrics and review QA.
- `data/fluorescence_control`: validated 40k summary, per-primary energy tables (all four 10k histories), per-run metrics and independent checks.
- `data/track_evidence`: 327 selected ROI events, outgoing tracks, derived event-level audit, 3 `compt`-labeled exceptions.
- `code/`: frozen simulation/QA scripts, original macro templates, post-init fluorescence controls and trace/ROOT cycle handling.
- `methods/macros`: four exact analysis-run GATE macro files; `methods/SCIENTIFIC_PROTOCOL.md`: original transport study protocol.
- `reports`, `figures`: audited PDFs and figures; `audit_release.py`: standard-library recheck of published CSV evidence.

## Quick check (no GATE rerun)

```bash
python3 research/phase1_2/audit_release.py
python3 -m pip install -r research/phase1_2/code/requirements.txt
python3 -m pytest -q research/phase1_2/code/tests
```

See `LIMITATIONS.md` and `DATA_PROVENANCE.md` before citing this dataset. This directory is a **scientific research artifact, not SiPM readout or detector performance validation**.
