# RadiantDAQ Phase 1.1 — validated ROOT/DoseActor audit

**Status: locally executed and published as derived evidence (2026-11-15).**

The 18-run, 90,000-primary GATE 9.4 / Geant4 11.2.2 multi-seed gamma-transport campaign was audited from the *author's local original ROOT Hits and DoseActor MetaImage data*, preserving the original simulation inputs. All 18 checks completed successfully in the author's WSL session, and the small derived reports were published in this research folder. This does **not** constitute measured detector performance or an independent rerun on a separate machine.

## Included

- `raw_audit.py` and `tests/test_raw_audit.py`: 10 software tests (including material-db SHA-256 regression checks).
- `raw_audit_derived/RAW_AUDIT_REPORT.md`: locally generated report after re-reading original GATE ROOT and DoseActor data.
- `raw_audit_derived/raw_run_audit.csv`: per-run recomputed metrics.
- `raw_audit_derived/roi_400_440_events.csv`: event-level exploratory hit evidence, 730 entries.
- `raw_audit_derived/roi_histogram_1kev.csv`: counts by 1-keV deposited-energy bin.
- `raw_audit_derived/audit_manifest.json`: per-run hash and actor-output evidence.
- `review/INDEPENDENT_SCIENTIFIC_REVIEW.md`: CSV-level review of the author's summary ZIP (performed separately from the local RAW audit).
- `AUDIT_EXECUTION_STATUS.md`, `FIX_NOTES.md`: status and corrected hash-key provenance.

The original raw `.root` and `.raw` files, full GATE build, Geant4 physics data and full `GateMaterials.db` remain with the author; they are not part of this repository folder. Downloaded derived CSV data cannot substitute for them when reproducing the GATE-level raw check.

## Verified observed audit result

| Quantity | Result |
|---|---:|
| Separate 511-keV gamma transport runs | 18 |
| Incident primaries | 90,000 |
| 400–440 keV deposited-energy ROI, BGO | 726 |
| 400–440 keV deposited-energy ROI, LSO | 4 |
| Largest absolute ROOT–DoseActor sum discrepancy | 0.0000913076 MeV |
| SHA-256 of local material database | `3ad9c0993b48af4bd573be9e976b636fd93c4c33350abf76879542830548b850` |

**Scientific interpretation:** a 511-keV primary depositing 400–440 keV in the crystal is not directly proof of characteristic X-ray escape. Hit-step `processName` labels and `parentID`/`trackID` do not yet establish created-particle energies and actual crystal-boundary crossings. Additional diagnostic GATE runs are needed.

## Re-run tests from the repository root

```bash
cd results/gate9-lso-bgo-511kev-phase1-1-raw-audit-2026
python -m pip install -r requirements.txt
python -m pytest -q tests/test_raw_audit.py
```

## Re-check the author's existing RAW data (read-only input)

```bash
python raw_audit.py \
  --workspace "$HOME/radiantdaq_phase1_multiseed_2026" \
  --output "$HOME/radiantdaq_phase1_1_raw_audit_RECHECK_NEW"
```

The re-check refuses an existing output directory. Original runs must stay untouched.

The local-only Git publishing helper used for the original upload is intentionally not tracked here because it creates a one-time branch and should not be rerun on the existing remote branch. Later releases should use a new branch and a separately reviewed PR.

## Scope

The results are conditional radiation transport for an aligned, monoenergetic 511-keV gamma source and ideal 3×3 mm crystals. No optical simulation, PDE, SiPM current, energy-resolution FWHM, CTR, scatter/random PET coincidence model, detector-array sensitivity or experimental measurement is claimed.
