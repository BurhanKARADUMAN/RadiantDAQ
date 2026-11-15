"""Command-line demo and parameter sweeps for synthetic PET SiPM readout."""
import argparse
import csv
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
from .config import DetectorConfig
from .metrics import simulate_pet_pair
from .waveforms import simulate_waveform


def save_csv(path, headers, rows):
    with open(path, 'w', newline='', encoding='utf8') as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def plot_demo(out: Path, result, wave):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    def setup_axes():
        fig, ax = plt.subplots(figsize=(9, 5.3), dpi=140)
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(alpha=0.13)
        return fig, ax

    fig, ax = setup_axes()
    ax.plot(wave.time_ns, wave.clean_mv, label='Noiseless shaped signal', linewidth=1.7)
    ax.plot(wave.time_ns, wave.noisy_mv, label='Digitized signal + noise', linewidth=.65, alpha=.75)
    ax.axhline(wave.threshold_mv, label='Example discriminator threshold', linestyle='--', color='gray')
    if wave.crossing_ns is not None:
        ax.axvline(wave.crossing_ns, color='black', alpha=.65, linestyle=':', label='Sampled waveform crossing')
    ax.set(xlabel='Time (ns)', ylabel='Signal (mV, illustrative gain)', title='Synthetic scintillator–SiPM readout waveform')
    ax.legend(loc='upper right', fontsize=9)
    fig.tight_layout()
    fig.savefig(out / '01_sipm_waveform.png')
    plt.close(fig)

    fig, ax = setup_axes()
    ax.hist(result.energy_a_kev, bins=55, color='#227c90', edgecolor='white', alpha=.86)
    ax.set(xlabel='Single-point calibrated energy (keV)', ylabel='Synthetic events',
           title='Full-energy 511 keV events — model-only energy response')
    fig.tight_layout()
    fig.savefig(out / '02_energy_response.png')
    plt.close(fig)

    fig, ax = setup_axes()
    valid_dt = result.delta_t_ns[np.isfinite(result.delta_t_ns)]
    ax.hist(valid_dt * 1000, bins=70, color='#9b6bb4', edgecolor='white', alpha=.85)
    ax.set(xlabel='Detector A − detector B timing (ps)', ylabel='Synthetic true pairs',
           title='Synthetic coincidence timing — order-statistic timing proxy')
    fig.tight_layout()
    fig.savefig(out / '03_timing_difference.png')
    plt.close(fig)


def do_demo(out: Path, events: int, seed: int, cfg: DetectorConfig, window_ns: float):
    out.mkdir(parents=True, exist_ok=True)
    result = simulate_pet_pair(cfg, events, seed, window_ns)
    wave = simulate_waveform(cfg, np.random.default_rng(seed + 111))
    save_csv(out / 'event_level_synthetic.csv',
             ['event', 'energy_a_kev', 'energy_b_kev', 'time_a_ns', 'time_b_ns',
              'delta_t_ns', 'accepted_window'],
             [[i, f'{result.energy_a_kev[i]:.7f}', f'{result.energy_b_kev[i]:.7f}',
               f'{result.time_a_ns[i]:.7f}', f'{result.time_b_ns[i]:.7f}',
               f'{result.delta_t_ns[i]:.7f}', int(result.accepted[i])]
              for i in range(events)])
    save_csv(out / 'sample_waveform.csv', ['time_ns', 'clean_mv', 'noisy_mv'],
             zip(np.round(wave.time_ns, 6), np.round(wave.clean_mv, 6), np.round(wave.noisy_mv, 6)))
    report = {
        'provenance': 'SYNTHETIC computational data; NOT measured, validated, or Geant4/GATE output',
        'timing_model': 'k-th detected photon order statistic plus Gaussian SPTR/electronics jitter',
        'waveform_model': 'independently rendered phenom. pulse kernel; CTR NOT calculated from waveform crossing',
        'energy_model': 'full energy deposition, no scatter, 511-keV single point calibration',
        'seed': seed,
        'config': cfg.to_dict(),
        'summary': result.summary,
        'sample_waveform_first_crossing_ns': wave.crossing_ns,
    }
    (out / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    plot_demo(out, result, wave)
    return report


def plot_sweep(out: Path, rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), dpi=140)
    a = [r for r in rows if r['sweep'] == 'PDE']
    b = [r for r in rows if r['sweep'] == 'electronics_timing_sigma_ns']
    axes[0].plot([r['value'] for r in a], [r['energy_resolution_fwhm_pct'] for r in a], marker='o')
    axes[0].set(xlabel='SiPM photon detection efficiency (fraction)', ylabel='Energy FWHM / mean (%)',
                title='Synthetic PDE sensitivity')
    axes[1].plot([r['value'] for r in b], [r['ctr_fwhm_ps'] for r in b], marker='o')
    axes[1].set(xlabel='Electronics jitter σ (ns)', ylabel='Gaussian-equivalent CTR (ps)',
                title='Synthetic timing jitter sensitivity')
    for ax in axes:
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(alpha=.18)
    fig.tight_layout()
    fig.savefig(out / '04_parameter_sensitivity.png')
    plt.close(fig)


def do_sweep(out: Path, events: int, seed: int, cfg: DetectorConfig):
    if events < 2:
        raise ValueError('events must be >= 2')
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    sweep_values = [
        ('PDE', 'photon_detection_efficiency', [.15, .25, .35, .45]),
        ('electronics_timing_sigma_ns', 'electronics_timing_sigma_ns', [.025, .075, .125, .225]),
    ]
    for i, (name, field, values) in enumerate(sweep_values):
        for j, value in enumerate(values):
            trial = simulate_pet_pair(replace(cfg, **{field: value}), events, seed + 100 * i + j, 1.0)
            rows.append({
                'sweep': name,
                'value': value,
                'events': events,
                'seed': seed + 100 * i + j,
                'energy_resolution_fwhm_pct': trial.summary['energy_resolution_a_fwhm_pct'],
                'ctr_fwhm_ps': trial.summary['gaussian_equivalent_ctr_fwhm_ps'],
                'window_acceptance_given_trigger': trial.summary['window_acceptance_given_trigger'],
            })
    save_csv(out / 'synthetic_parameter_sweep.csv', list(rows[0]), ([r[k] for k in rows[0]] for r in rows))
    plot_sweep(out, rows)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description='RadiantDAQ: illustrative PET scintillator/SiPM research model')
    parser.add_argument('command', choices=['demo', 'sweep'])
    parser.add_argument('--events', type=int, default=1800)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--out', type=Path, default=Path('outputs/demo'))
    parser.add_argument('--coincidence-window-ns', type=float, default=1.0)
    args = parser.parse_args(argv)
    cfg = DetectorConfig()
    if args.command == 'demo':
        data = do_demo(args.out, args.events, args.seed, cfg, args.coincidence_window_ns)
        print(json.dumps(data['summary'], indent=2))
    else:
        data = do_sweep(args.out, args.events, args.seed, cfg)
        print(f'{len(data)} synthetic sweep points generated')
    print(f'Output: {args.out.absolute()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
