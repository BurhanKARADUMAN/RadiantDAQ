# Phase 1.1 material-database SHA-256 hash-key correction

The original Phase 1 records use `input.json["material_db_sha256"]` (singular `material`), while the initial Phase 1.1 checker incorrectly requested `materials_db_sha256` (plural). This generated a false hash-mismatch error before any raw-file analysis.

The corrected audit reads the original key and retains the **real SHA-256 equality verification** against the campaign manifest. The source package additionally includes a regression test to reject an actually mismatched hash.

**Current status (2026-11-15):** The author ran the corrected audit on WSL. It completed **18/18** ROOT/DoseActor checks, and the resulting derived tables and audit manifest were published in this folder. This note corrects the obsolete instruction in the original hotfix note saying the audit had not yet been run.

No GATE original `.root`, `.raw`, macros, original pilot datasets, or `main` history were modified by the audit.
