# Model equations and event generation

**Scope:** Synthetic research-education model for two identical scintillator–SiPM channels observing idealized 511-keV *fully deposited* events. No radiation transport, Compton scatter, attenuation, optical ray tracing, scintillator surface physics, ASIC analog response, or clinical imaging is simulated.

## 1. Photon generation and PDE

At fixed deposited energy `E=511 keV` and illustrative scintillation yield `Y`, the expected number of *detected* primary photoelectrons is

```
mu_pe = (E / 1000 keV per MeV) * Y * collection_fraction * PDE
```

An event-dependent Gaussian multiplier (standard deviation `intrinsic_fwhm_fraction / 2.35482`, truncated to >= 0.2) emulates aggregate light-yield variations. This is a **phenomenological term**, not a first-principles LYSO nonproportionality calculation.

```
N_primary ~ Poisson(mu_pe * event_multiplier)
```

This is consistent with the result of Poisson photon generation followed by independent optical collection and PDE thinning; correlations between photons are not modeled.

## 2. SiPM occupancy and charge response

Using `M` finite, one-shot cells:

```
p_hit = 1 - exp(-N_primary / M)
N_fired ~ Binomial(M, p_hit)
N_prompt_xt ~ min[ Binomial(N_fired, p_xt), M - N_fired ]
N_dark ~ Poisson(DCR * integration_window_s)
Q_apparent = N_fired + N_prompt_xt + N_dark + Normal(0, sigma_noise_pe)
```

The occupancy model is approximate, permits only one initial firing per microcell, ignores recharge/afterpulsing, and uses an intentionally simplified one-generation crosstalk term. The mean-field calibration reference is computed from expected occupancy, crosstalk, and dark counts; the reported energy is

```
E_hat = 511 keV * Q_apparent / Q_reference
```

**Important:** this is a *single-point calibration at 511 keV*, not a test of energy linearity or absolute dose. `Q_reference` is model-internal, not measured.

## 3. Timing estimator

The model assumes `N_primary` independently emitted scintillation photons with exponential time distribution (`tau_decay=40 ns`). The waiting times between the 1st, 2nd, ..., k-th observed photons are distributed as exponentials with rate `(N_primary-i)/tau_decay`. Thus:

```
T_k = sum_{i=0}^{k-1} Exponential(scale=tau_decay / (N_primary-i))
T_detector = T_k + Normal(0, sqrt(sigma_SPTR^2 + sigma_electronics^2))
Delta_T = T_detector_A - T_detector_B
```

This is a **proxy for a prompt-photon discriminator**, *not* a threshold crossing derived from an analog front-end circuit. Events with fewer than `k` detected primary photons are untriggered.

Coincidence timing is reported as a **Gaussian-equivalent CTR** computed from `2.35482 * sample_sd(Delta_T)`. The accepted true-pair fraction uses `abs(Delta_T) < full_window_ns / 2`. This synthetic acceptance is conditional on all events already being ideal fully deposited true pairs, not a PET system sensitivity metric.

In a real experiment, CTR is normally determined from the FWHM of the detector time-difference distribution, which is not necessarily Gaussian. The mean timing offset, time walk, time calibration, optical transport, and electronics response require physical measurements.

## 4. Analog waveform illustration

For a separate example event, primary photoelectrons arrive with exponential delay. They are placed in sampling bins and convolved with a simple pulse shape:

```
h(t) = [1 - exp(-t / tau_rise)] exp(-t / tau_fall),  t >= 0
V(t) = gain_per_PE * sum_j h(t - t_j) + Gaussian sample noise
```

The first upward threshold crossing is linearly interpolated between adjacent digital samples. **CTR is not calculated from this waveform output**. The `single_pe_gain_mv` parameter is illustrative and has not been derived from a validated equivalent circuit or sensor impedance.

## 5. Metrics and caveats

- Energy resolution: `100 * 2.35482 * SD(E_hat) / mean(E_hat)` in percent, Gaussian-equivalent.
- CTR: `1000 * 2.35482 * SD(Delta_T)` in picoseconds, Gaussian-equivalent.
- Window acceptance: accepted simulated true events / triggered true pairs.
- Random coincidences: approximation `R_A R_B W` when `W` denotes **full** coincidence window (not half width), valid in a low-occupancy regime.
- The illustrative parameters are neither calibrated to a particular commercial SiPM nor to a manufactured scintillator crystal.

## 6. Reproducibility

All Monte Carlo random variables are generated through NumPy's seeded `default_rng`. The two channels use independent child seed sequences. CSV and JSON outputs include events, seed, configurations, and explicit provenance text. Parameter sweeps use distinct seeds (not common random numbers), which means neighboring points show some Monte Carlo variation.
