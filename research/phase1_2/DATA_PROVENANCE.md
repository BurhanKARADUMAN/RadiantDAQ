# Data provenance, licenses and audit boundaries

Public work is a curated record of simulations and derived checks executed by the original author on a local GATE 9.4 / Geant4 11.2.2 installation (Linux WSL). Main repository Phase 1.1 history remains untouched by this additive folder.

## Source archive checksums (SHA-256)

| Source archive | SHA-256 |
|---|---|
| Phase 1.2 reviewed code and transport analysis | `8e81397bdb1f731e9d6bde2cdba52f623dd2c61f0d97954fe339a12ca7b0d2b4` |
| 40k validated paired-control dataset | `8abb255de462d6d7e4784be12e8a0d240fed5eb83b6c345c5fb9d8cd02a36fd8` |
| 40k independent CSV QA/figures | `fc0947167034649d8589a1c62fc06409ca940a55f8c01f683d763100052f9217` |
| 327-event track evidence | `1e299ed6961b0fcee9d7d29ea33ef2ba78f830eb4ff75264f135a51f86017155` |
| 327-event independent QA/report | `40c402518abcbc202a4a20dde32ed5809a2d68928ad7f36a6e3a0123e8c59f13` |

The complete native ROOT files are retained only on the original WSL machine; no `.root` binaries or full 180k raw data are contained here.

Data exported from a reviewed archive retains its source analytical meaning; manifest fields are **not** a substitute for checking local simulator provenance. Consult `LIMITATIONS.md` and `audit_release.py`.

`SHA256SUMS.txt` at this directory root lists the hash of each distributed payload file and can be verified with `sha256sum -c SHA256SUMS.txt` from within this directory.
