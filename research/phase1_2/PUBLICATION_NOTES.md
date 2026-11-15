# Publication and PR review checklist

- Do not alter `main` directly. Submit this package to branch `research/phase1-2-validated-2026` and review as a pull request.
- Confirm `python3 research/phase1_2/audit_release.py` PASS and SHA256 check.
- If GATE 9.4/Geant4 11.2.2 is unavailable to CI, **do not** imply CI reran physical transport. It only checks software and the committed derived data.
- Never describe the original 36-run `fluo_off` label as a verified negative control. The **subsequent 40k regional study** is the validated comparison.
- Review `LIMITATIONS.md` before merging, especially the 3 `compt` exceptions and absence of native ROOT.
- The source PDFs are included only in this research folder; prior GitHub commit and repositories are untouched.
