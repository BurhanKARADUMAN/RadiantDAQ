# Phase 1.1 material database hash-key hotfix

**Cause:** `analyze_run()` expected `inputs.get('materials_db_sha256')`, but Phase 1 campaign stores `material_db_sha256` (singular) in every `input.json`. Thus a missing key produced `None`, which was falsely reported as a material DB mismatch.

**Fix:** use the original campaign's `material_db_sha256` key; keep the actual SHA-256 comparison and the external manifest vs on-disk material database verification enabled. Correct the corresponding test fixture and add a mismatch rejection test.

**Evidence:** all 18 `input.json` records in the previously shared `RadiantDAQ_Phase1_Results_2026.zip` have the singular key, and each stored hash matches the manifest's `materials_sha256` (as checked by the assistant).

**Safe scope:** only `raw_audit.py` and `tests/test_raw_audit.py` change. No input data, GATE macros, ROOT/RAW files, results folders or GitHub content is changed.

**Run from this folder:** `python -m pytest -q tests/test_raw_audit.py`, then `python raw_audit.py --workspace "$HOME/radiantdaq_phase1_multiseed_2026" --output "$HOME/radiantdaq_phase1_1_raw_audit_2026"`.

**Scientific status:** the WSL RAW/ROOT audit is still to be run; none of the test fixtures are scientific validation.
