"""Configuration of a deliberately simplified PET scintillator + SiPM chain."""
from dataclasses import dataclass, asdict
import math


@dataclass(frozen=True)
class DetectorConfig:
    gamma_energy_kev: float = 511.0
    light_yield_ph_per_mev: float = 30_000.0
    optical_collection: float = 0.65
    photon_detection_efficiency: float = 0.35
    microcells: int = 14_000
    optical_crosstalk_probability: float = 0.04
    dark_count_rate_hz: float = 100_000.0
    integration_window_ns: float = 160.0
    scintillation_decay_ns: float = 40.0
    intrinsic_fwhm_fraction: float = 0.07
    electronic_noise_pe_rms: float = 4.0
    # Timing is based on the k-th detected photon, not a SPICE pulse discriminator.
    trigger_photoelectrons: int = 12
    sipm_sptr_sigma_ns: float = 0.09
    electronics_timing_sigma_ns: float = 0.10
    # Waveform-only illustration settings.
    waveform_rise_ns: float = 0.55
    waveform_fall_ns: float = 8.0
    waveform_single_pe_mv: float = 0.28
    waveform_noise_mv_rms: float = 0.55
    adc_sampling_ns: float = 0.10
    pulse_window_ns: float = 150.0
    waveform_start_ns: float = 12.0
    threshold_mv: float = 12.0

    def validate(self):
        for key in ('gamma_energy_kev', 'light_yield_ph_per_mev', 'integration_window_ns',
                    'scintillation_decay_ns', 'waveform_rise_ns', 'waveform_fall_ns',
                    'waveform_single_pe_mv', 'adc_sampling_ns', 'pulse_window_ns'):
            if not math.isfinite(getattr(self, key)) or getattr(self, key) <= 0:
                raise ValueError(f'{key} must be finite and positive')
        for key in ('optical_collection', 'photon_detection_efficiency', 'optical_crosstalk_probability'):
            v = getattr(self, key)
            if not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError(f'{key} must be in [0, 1]')
        for key in ('sipm_sptr_sigma_ns', 'electronics_timing_sigma_ns',
                    'electronic_noise_pe_rms', 'intrinsic_fwhm_fraction', 'dark_count_rate_hz',
                    'waveform_noise_mv_rms', 'threshold_mv', 'waveform_start_ns'):
            v = getattr(self, key)
            if not math.isfinite(v) or v < 0:
                raise ValueError(f'{key} must be finite and nonnegative')
        if self.microcells < 1 or self.trigger_photoelectrons < 1:
            raise ValueError('microcells and trigger_photoelectrons must be >= 1')
        if self.adc_sampling_ns >= self.pulse_window_ns:
            raise ValueError('sampling period must be smaller than waveform window')
        return self

    def to_dict(self):
        return asdict(self)
