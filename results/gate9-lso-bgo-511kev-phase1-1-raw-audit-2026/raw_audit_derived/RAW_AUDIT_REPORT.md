# RadiantDAQ Phase 1.1 — Independent raw-data audit

**Status:** 18 original ROOT Hits and DoseActor RAW files were re-read and checked locally.

**Primaries:** 90,000 in 18 runs; 511-keV gamma, 3 x 3 mm LSO/BGO crystals.

**ROI 400–440 keV:** BGO 726, LSO 4.

**ROOT vs DoseActor:** all runs passed the documented absolute/relative energy-sum tolerance; max absolute discrepancy 9.13076e-05 MeV.

**Material database SHA-256:** `3ad9c0993b48af4bd573be9e976b636fd93c4c33350abf76879542830548b850`. All original ROOT, macro, MHD and RAW hashes agree with the 2026 campaign validation records.

## Interpretation

GATE ROOT `Hits` records are crystal energy-deposition *steps*. `processName`, `parentID` and `trackID` identify step labels and some genealogy *inside the scored volume*, not the definitive origin of a secondary or its crossing out of the crystal. An observed 400–440 keV deposited-energy feature is **compatible with** energy escape, but cannot be classified as characteristic X-ray escape without creator-process, initial secondary energy and boundary-crossing records. The `511 - Edep` deficit is not a detected escaped-photon energy.

## Remaining work

- Enable track/stepping instrumentation, creator process and boundary-crossing scoring in a **new** diagnostic experiment; preserve the 90k campaign.
- Compare relevant material fluorescence energies and Geant4 atomic deexcitation settings.
- Vary cuts and EM physics lists separately from seed uncertainty; no systematic uncertainty is claimed here.
- No optical photons, SiPM response, measured energy resolution or coincidence time resolution are included.

## Output files

- `raw_run_audit.csv`: per-run independent checks
- `roi_400_440_events.csv`: per-event exploratory hit evidence
- `roi_histogram_1kev.csv`: deposited-energy distribution
- `audit_manifest.json`: complete evidence/provenance record
