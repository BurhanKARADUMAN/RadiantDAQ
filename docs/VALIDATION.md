# Scientific validation ladder

## Level 0 — Software model, now available

- [x] Parameter validation and repeatable seeds
- [x] SiPM finite occupancy
- [x] Optical collection / PDE parametric study
- [x] Timing order statistics and jitter budget
- [x] Synthetic waveform and sampled threshold crossing
- [x] Metrics for energy and Gaussian-equivalent coincidence timing
- [x] Automated tests and GitHub CI

These tests verify **software consistency**, not experimentally validated detector physics.

## Level 1 — GATE / Geant4 transport and optical photons

- [ ] Build material/geometric model of a pixelated LYSO/SiPM detector using Geant4 or GATE
- [ ] Model 511-keV photon interactions, Compton/photoelectric transport and crystal escape
- [ ] Validate energy deposits and optical photon collection in independent runs
- [ ] Map optical photons at SiPM photosensitive surface into stochastic Geiger avalanches
- [ ] Compare energy distributions of full-energy and Compton events
- [ ] Record the physics list, scintillation yield, Birks treatment, surfaces, optical PDE and seed

## Level 2 — Analog front-end electronics

- [ ] Replace phenomenological impulse with actual SiPM equivalent circuit, validated electronics model (e.g. LTspice)
- [ ] Include bandwidth, termination, bias, noise spectral density, time walk and discriminator delay
- [ ] Benchmark CFD vs leading-edge discrimination on **the same digitized waveforms**
- [ ] Validate pulse amplitude, rise/fall and trigger rates against bench signals

## Level 3 — Physical detector bench

- [ ] Confirm actual manufacturer model, device bias and overvoltage before use
- [ ] Characterize SiPM dark counts, crosstalk and gain versus bias/temperature
- [ ] Measure energy spectra from a suitably regulated and supervised 511-keV source (if available)
- [ ] Measure single-channel SPTR and coincidence CTR with calibrated instrumentation
- [ ] Capture raw waveforms, calibration logs, temperatures, uncertainty budget and provenance

## Level 4 — Imaging performance

- [ ] Model full PET acquisition geometry, scattering, randoms, sensitivity and normalization
- [ ] Implement an image reconstruction pipeline (e.g. list-mode or sinogram-based) with quantitative validation
- [ ] Define objective imaging figures of merit and separate them from single-channel detector metrics

**No radioactive sources or HV assembly procedures are provided here. Laboratory commissioning requires professional supervision and site-specific safety controls.**
