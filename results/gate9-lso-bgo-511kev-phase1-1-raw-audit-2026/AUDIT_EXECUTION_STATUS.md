# Phase 1.1 WSL execution status (2026-11-15)

**Evidence:** Directly supplied terminal output from the author's WSL execution of the fixed read-only audit. The complete generated output directory was not uploaded in the chat at the time of this note. This status is distinguished from independently re-reading every RAW/ROOT byte in the assistant's environment.

| Item | Value reported by WSL |
|---|---:|
| Audit status | `independently_rechecked_raw_files` |
| Runs | 18 of 18 |
| Incident 511-keV gamma primaries | 90,000 |
| 400–440 keV ROI events, BGO | 726 |
| 400–440 keV ROI events, LSO | 4 |
| Maximum absolute ROOT–DoseActor difference | 9.13076e-05 MeV |
| Material database SHA-256 | `3ad9c0993b48af4bd573be9e976b636fd93c4c33350abf76879542830548b850` |
| ROOT/RAW files published | No |

The user's corrected source code passed **9 tests** locally after the `material_db_sha256` key fix. The updated package includes an additional regression test (10 tests passed in the assistant's Python test environment). Both test outcomes are software tests, not Geant4 reruns.

**Interpretation:** ROOT hit-step genealogies do not establish definitive creator-process attribution or actual emission/escape across the crystal boundary. Follow-up instrumentation is needed before describing the ~420 keV feature as a characteristic X-ray escape peak.

**Next verification:** `publish_branch_safe.sh` checks for the actual output artifacts before staging them. Original raw data and historical GitHub results remain unmodified.
