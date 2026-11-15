# Scope and limitations

1. **Original `fluo_off` Phase 1.2 variation is unverified.** Original 36-run naming is retained for historical provenance, not as valid suppression. Do not pool it with the 40k region-selective study.
2. **No native ROOT `.root` binaries** are committed to this folder; 327 created/outgoing native ROOT track cross-linkage was previously executed in the original WSL workspaces. The independent verification packaged here repeats checks on derived CSV and energy arrays. Native branch contents are not independently reassessed on this copy.
3. **Source and energy:** 511 keV mono-directional incident gamma histories, not an isotropic 511 keV annihilation pair. The `Ekine` native ROOT MeV scaling is strongly consistent with energy closure, but it remains an external simulator-unit assumption.
4. **Simulation ≠ optical detector:** no light generation/collection, PDE, SiPM electronics, gain, noise, thresholding, or experimental energy-resolution convolution in the reported transport result.
5. **Particle IDs:** `CreatorProcess=phot` indicates the Geant4 process label, not a direct chemical-element or shell-transition ID; 3 of 327 selected photons are `compt`-labelled. Bi K-series fluorescence is a strongly supported interpretation, not a line-by-line identification.
6. **ROI-selected denominator:** the 327/327 linkage describes the 327 **selected** 400–440 keV events, not 100% detector efficiency or photon escape probability over all 20k ON primaries.
7. **Uncertainty:** Fisher and Wilson analyses estimate event-count uncertainty conditional on the model, not uncertainties in physics models, production cuts, materials, detector geometry or actor coverage.
8. **Regional override:** the validated control changes crystal-region flags only (`OFF: 0 1 1`, `ON: 1 1 1`), world remains ON, Auger and PIXE remain ON. This is not a global `fluo=false` experiment. It is also specific to the tested Geant4/GATE build and ordering.
9. The per-primary 40k CSV arrays enable independent recounting, but do not replace full GATE ROOT output, trajectories or step histories.
