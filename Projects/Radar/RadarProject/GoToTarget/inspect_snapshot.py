"""
inspect_snapshot.py — Load, visualise, and analyse a radar buffer snapshot (.npz).

Usage:
    python inspect_snapshot.py                        # opens latest snapshot in recordings/
    python inspect_snapshot.py recordings/radar_snapshot_20260305_143022.npz
"""
import sys
import os
import glob
from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import mpl_toolkits.mplot3d  # type: ignore[reportUnusedImport]  # registers '3d' projection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pick_file() -> str:
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.isfile(path):
            sys.exit(f"File not found: {path}")
        return path

    recordings_dir = os.path.join(os.path.dirname(__file__), 'recordings')
    files = sorted(glob.glob(os.path.join(recordings_dir, '*.npz')))
    if not files:
        sys.exit(f"No .npz files found in {recordings_dir}")
    return files[-1]          # most recent


def load(path: str) -> dict:
    raw = np.load(path)
    data = {k: raw[k] for k in raw.files}
    print(f"\n{'='*60}")
    print(f"  Snapshot: {os.path.basename(path)}")
    print(f"{'='*60}")
    print(f"  Keys saved: {sorted(data.keys())}\n")
    return data


def _style_ax(ax, is_3d: bool = False) -> None:
    """Apply dark phosphor theme styling to a single axis."""
    ax.set_facecolor('#2b2b2b')
    ax.tick_params(colors='white', labelsize=7)
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('white')
    if not is_3d:
        for spine in ax.spines.values():
            spine.set_edgecolor('#555555')
    else:
        ax.zaxis.label.set_color('white')
        ax.zaxis.line.set_color('white')
        ax.tick_params(axis='z', colors='white', labelsize=6)


def _reshape_rd(flat: np.ndarray,
                candidates: tuple = (256, 128, 64, 32, 16, 12, 8)) -> Optional[np.ndarray]:
    """Reshape a flat 1-D RD map array into 2-D (range_bins × unique_doppler_bins).

    When the firmware packs 8 virtual-antenna Doppler spectra consecutively
    (8 × 32 = 256 columns), the target repeats 8 times.  Average the 8 copies
    to produce 32 unique Doppler bins with improved SNR.
    """
    for d in candidates:
        if flat.size % d == 0:
            rd2d = flat.reshape(-1, d)
            n_range, n_doppler = rd2d.shape
            if n_doppler == 256 and n_range > 0:
                rd2d = rd2d.reshape(n_range, 8, 32).mean(axis=1)
            return rd2d
    return None


# ---------------------------------------------------------------------------
# Text summary
# ---------------------------------------------------------------------------

def print_summary(data: dict) -> None:
    # Detected plots per frame
    plot_keys = sorted(k for k in data if k.startswith('plots_frame'))
    if plot_keys:
        print("  Detected points per frame:")
        for k in plot_keys:
            arr = data[k]
            print(f"    {k}: {arr.shape[0]} points  (cols: x, y, z, velocity, snr)")
            if arr.shape[0]:
                xs, ys, zs = arr[:, 0], arr[:, 1], arr[:, 2]
                print(f"      X [{xs.min():.2f} … {xs.max():.2f}]  "
                      f"Y [{ys.min():.2f} … {ys.max():.2f}]  "
                      f"Z [{zs.min():.2f} … {zs.max():.2f}] m")
        print()

    for key, label in [
        ('range_profiles', 'Range profiles'),
        ('noise_profiles', 'Noise profiles'),
        ('rd_maps',        'Range-Doppler maps'),
    ]:
        if key in data:
            arr = data[key]
            print(f"  {label}: shape={arr.shape}  "
                  f"min={arr.min():.3f}  max={arr.max():.3f}")

    if 'ra_maps_real' in data:
        r = data['ra_maps_real']
        i = data['ra_maps_imag']
        mag = np.sqrt(r**2 + i**2)
        print(f"  Range-Azimuth maps: shape={r.shape}  "
              f"magnitude min={mag.min():.1f}  max={mag.max():.1f}")
    print()


# ---------------------------------------------------------------------------
# Overview plots (original six-panel view)
# ---------------------------------------------------------------------------

def plot_all(data: dict) -> None:
    fig = plt.figure(figsize=(16, 10), facecolor='#1e1e1e')
    fig.suptitle('Radar Snapshot Inspector', color='white', fontsize=13)

    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    ax_rp  = fig.add_subplot(gs[0, 0])
    ax_rd  = fig.add_subplot(gs[0, 1])
    ax_ra  = fig.add_subplot(gs[0, 2])
    ax_pts = fig.add_subplot(gs[1, 0])
    ax_vel = fig.add_subplot(gs[1, 1])
    ax_snr = fig.add_subplot(gs[1, 2])

    for ax in fig.axes:
        _style_ax(ax)

    # --- Range + Noise profiles (all frames) ---
    ax_rp.set_title('Range Profile (all frames)')
    ax_rp.set_xlabel('Range bin')
    ax_rp.set_ylabel('Magnitude (Q9)')
    if 'range_profiles' in data:
        for i, row in enumerate(data['range_profiles']):
            ax_rp.plot(row, linewidth=0.8, alpha=0.8,
                       label=f'F{i}' if i == 0 else '_')
    if 'noise_profiles' in data:
        for i, row in enumerate(data['noise_profiles']):
            ax_rp.plot(row, linewidth=0.8, alpha=0.6, linestyle='--',
                       color='red', label='Noise' if i == 0 else '_')
    ax_rp.legend(fontsize=6, labelcolor='white',
                 facecolor='#3b3b3b', edgecolor='#555555')

    # --- Range-Doppler (last frame) ---
    ax_rd.set_title('Range-Doppler (last frame)')
    ax_rd.set_xlabel('Doppler bin')
    ax_rd.set_ylabel('Range bin')
    if 'rd_maps' in data:
        rd = _reshape_rd(data['rd_maps'][-1])
        if rd is not None:
            rd_shifted = np.fft.fftshift(rd, axes=1)
            im = ax_rd.imshow(rd_shifted, aspect='auto', origin='lower',
                              cmap='jet', interpolation='nearest')
            plt.colorbar(im, ax=ax_rd, fraction=0.046, pad=0.04).ax.tick_params(
                colors='white', labelsize=6)

    # --- Range-Azimuth (last frame, magnitude) ---
    ax_ra.set_title('Range-Azimuth (last frame)')
    ax_ra.set_xlabel('Antenna index')
    ax_ra.set_ylabel('Range bin')
    if 'ra_maps_real' in data:
        ra = data['ra_maps_real'][-1] + 1j * data['ra_maps_imag'][-1]
        ra_mag = np.abs(ra)
        if ra_mag.ndim == 1:
            # Flat 1-D: reshape to 2-D (n_range × n_az).
            # Try common azimuth bin counts until we find an even split.
            for n_az in (64, 32, 16, 12, 8, 4):
                if ra_mag.size % n_az == 0:
                    ra_mag = ra_mag.reshape(-1, n_az)
                    break
            else:
                ra_mag = ra_mag[:, np.newaxis]
        im = ax_ra.imshow(ra_mag, aspect='auto', origin='lower',
                          cmap='jet', interpolation='nearest')
        plt.colorbar(im, ax=ax_ra, fraction=0.046, pad=0.04).ax.tick_params(
            colors='white', labelsize=6)

    # --- Scatter XY (all frames combined) ---
    ax_pts.set_title('Detected points XY (all frames)')
    ax_pts.set_xlabel('X (m)')
    ax_pts.set_ylabel('Y (m)')
    plot_keys = sorted(k for k in data if k.startswith('plots_frame'))
    colors = plt.cm.cool(np.linspace(0, 1, max(len(plot_keys), 1)))
    for idx, k in enumerate(plot_keys):
        pts = data[k]
        if pts.shape[0]:
            ax_pts.scatter(pts[:, 0], pts[:, 1], s=20,
                           color=colors[idx], label=f'F{idx}', alpha=0.8)
    if plot_keys:
        ax_pts.legend(fontsize=6, labelcolor='white',
                      facecolor='#3b3b3b', edgecolor='#555555')

    # --- Velocity histogram ---
    ax_vel.set_title('Velocity distribution (m/s)')
    ax_vel.set_xlabel('Velocity (m/s)')
    ax_vel.set_ylabel('Count')
    all_vels = []
    for k in plot_keys:
        pts = data[k]
        if pts.shape[0]:
            all_vels.extend(pts[:, 3].tolist())
    if all_vels:
        ax_vel.hist(all_vels, bins=20, color='dodgerblue', edgecolor='#1e1e1e')

    # --- SNR histogram ---
    ax_snr.set_title('SNR distribution (dB)')
    ax_snr.set_xlabel('SNR (dB)')
    ax_snr.set_ylabel('Count')
    all_snr = []
    for k in plot_keys:
        pts = data[k]
        if pts.shape[0]:
            all_snr.extend(pts[:, 4].tolist())
    if all_snr:
        ax_snr.hist(all_snr, bins=20, color='lime', edgecolor='#1e1e1e')

    plt.show()


# ---------------------------------------------------------------------------
# Range-Doppler Analysis
# ---------------------------------------------------------------------------

def analyze_rd_map(data: dict) -> None:
    """
    Full Range-Doppler analysis on the last recorded frame:

      1. Detect the peak-power target (range bin, Doppler bin).
      2. Recover the approximate fast-time signal by applying a column-wise
         IFFT (axis=0) to undo the range FFT.
      3. Figure A — signal recovery:
           • IFFT row at peak range bin + mean row + range profile (same axes)
           • Phase vs slow-time for the peak Doppler column
           • Target row (Doppler response) and target column (range response)
      4. Figure B — detection & spectral views:
           • RD heatmap in dB (zero-velocity centred)
           • Doppler spectrum at detected range bin
           • Power histogram
           • 3D RD surface
           • Range profile with noise estimate
           • Phase evolution of target column
    """
    if 'rd_maps' not in data:
        print("  [RD analysis] No rd_maps key found — skipping.\n")
        return

    rd_raw = _reshape_rd(data['rd_maps'][-1])
    if rd_raw is None:
        print("  [RD analysis] Could not reshape RD map — skipping.\n")
        return

    # Ensure complex dtype so IFFT and np.angle work correctly.
    # If the snapshot stores only magnitudes the phase-based plots will be flat
    # (all-zero phase) but all magnitude plots remain valid.
    rd = rd_raw.astype(complex) if not np.iscomplexobj(rd_raw) else rd_raw
    rd_mag = np.abs(rd)
    n_range, n_doppler = rd_mag.shape

    # ── 1. Target detection ─────────────────────────────────────────────────
    peak_range_bin, peak_doppler_bin = np.unravel_index(
        np.argmax(rd_mag), rd_mag.shape)
    peak_power = rd_mag[peak_range_bin, peak_doppler_bin]

    print(f"  [RD analysis] Peak target detected:")
    print(f"    Range  bin : {peak_range_bin}  (row index)")
    print(f"    Doppler bin: {peak_doppler_bin}  (column index)")
    print(f"    Power      : {peak_power:.4f}\n")

    # ── 2. Fast-time signal recovery via column-wise IFFT ───────────────────
    # Rows = range bins  (result of fast-time / range FFT)
    # Cols = Doppler bins (result of slow-time / Doppler FFT)
    # Applying IFFT along axis=0 reverses the range FFT for each Doppler bin,
    # approximately recovering the fast-time (ADC) signal.
    fast_time     = np.fft.ifft(rd, axis=0)        # shape: (n_range, n_doppler)
    fast_time_mag = np.abs(fast_time)

    one_row       = fast_time_mag[peak_range_bin, :]   # row at peak range bin
    avg_row       = fast_time_mag.mean(axis=0)          # mean across all rows
    range_profile = rd_mag.max(axis=1)                  # max magnitude per range bin

    # Phase of the peak Doppler column — evolves as a function of slow-time
    phase_slow_time = np.angle(rd[:, peak_doppler_bin])  # (n_range,) as proxy
    slow_time_idx   = np.arange(n_range)

    # dB map, Doppler-axis fftshifted for zero-velocity centred display
    rd_db         = 20 * np.log10(rd_mag + 1e-12)
    rd_db_shifted = np.fft.fftshift(rd_db, axes=1)
    doppler_cents = np.arange(n_doppler) - n_doppler // 2   # centred Doppler axis

    # ── Figure A: Fast-time signal recovery & target slices ─────────────────
    fig_a = plt.figure(figsize=(14, 9), facecolor='#1e1e1e')
    fig_a.suptitle('RD Analysis — Fast-Time Recovery & Target Slices',
                   color='white', fontsize=12)
    gs_a = gridspec.GridSpec(2, 2, figure=fig_a, hspace=0.50, wspace=0.35)

    ax_ft  = fig_a.add_subplot(gs_a[0, 0])
    ax_rp  = fig_a.add_subplot(gs_a[0, 1])
    ax_slc = fig_a.add_subplot(gs_a[1, 0])
    ax_ph  = fig_a.add_subplot(gs_a[1, 1])

    for ax in (ax_ft, ax_rp, ax_slc, ax_ph):
        _style_ax(ax)

    # A1: IFFT-recovered row, mean row, and range profile on one graph
    ax_ft.set_title('Fast-Time (IFFT on columns) & Range Profile')
    ax_ft.set_xlabel('Doppler bin')
    ax_ft.set_ylabel('Amplitude')
    ax_ft.plot(one_row, color='#00ff41', linewidth=1.0,
               label=f'IFFT row {peak_range_bin} (peak range bin)')
    ax_ft.plot(avg_row, color='dodgerblue', linewidth=1.0, linestyle='--',
               label='Mean of all IFFT rows')
    ax_ft.legend(fontsize=7, facecolor='#3b3b3b', labelcolor='white',
                 edgecolor='#555')

    # A2: Range profile (max magnitude over Doppler) vs range bin
    ax_rp.set_title('Range Profile (max over Doppler bins)')
    ax_rp.set_xlabel('Range bin')
    ax_rp.set_ylabel('Magnitude')
    ax_rp.plot(range_profile, color='#ffb300', linewidth=1.0)
    ax_rp.axvline(peak_range_bin, color='red', linestyle=':', linewidth=1.0,
                  label=f'Peak @ bin {peak_range_bin}')
    ax_rp.legend(fontsize=7, facecolor='#3b3b3b', labelcolor='white',
                 edgecolor='#555')

    # A3: Target row (Doppler response) and target column (range response)
    ax_slc.set_title(
        f'Target Slices  [range={peak_range_bin}, dop={peak_doppler_bin}]')
    ax_slc.set_xlabel('Bin index')
    ax_slc.set_ylabel('Magnitude')
    ax_slc.plot(rd_mag[peak_range_bin, :], color='cyan', linewidth=1.0,
                label=f'Row {peak_range_bin}  (fast-time / Doppler response)')
    ax_slc.plot(rd_mag[:, peak_doppler_bin], color='magenta', linewidth=1.0,
                label=f'Col {peak_doppler_bin}  (slow-time / range response)')
    ax_slc.legend(fontsize=7, facecolor='#3b3b3b', labelcolor='white',
                  edgecolor='#555')

    # A4: Phase vs slow-time for the peak Doppler column
    ax_ph.set_title(f'Phase vs Slow-Time  (Doppler col {peak_doppler_bin})')
    ax_ph.set_xlabel('Slow-time index (range bin proxy)')
    ax_ph.set_ylabel('Phase (rad)')
    ax_ph.plot(slow_time_idx, phase_slow_time, color='#ff6e6e', linewidth=1.0)
    ax_ph.set_ylim(-np.pi, np.pi)
    ax_ph.axhline(0, color='#555', linewidth=0.7)

    # ── Figure B: Detection & spectral views ────────────────────────────────
    fig_b = plt.figure(figsize=(16, 10), facecolor='#1e1e1e')
    fig_b.suptitle('RD Analysis — Detection & Spectral Views',
                   color='white', fontsize=12)
    gs_b = gridspec.GridSpec(2, 3, figure=fig_b, hspace=0.50, wspace=0.40)

    ax_hm   = fig_b.add_subplot(gs_b[0, 0])                      # RD heatmap
    ax_dp   = fig_b.add_subplot(gs_b[0, 1])                      # Doppler spectrum
    ax_hist = fig_b.add_subplot(gs_b[0, 2])                      # Power histogram
    ax_3d   = fig_b.add_subplot(gs_b[1, 0], projection='3d')     # 3D surface
    ax_rp2  = fig_b.add_subplot(gs_b[1, 1])                      # Range profile
    ax_ph2  = fig_b.add_subplot(gs_b[1, 2])                      # Phase evolution

    for ax in (ax_hm, ax_dp, ax_hist, ax_rp2, ax_ph2):
        _style_ax(ax)
    _style_ax(ax_3d, is_3d=True)

    # B1: RD heatmap in dB (Doppler axis zero-velocity centred)
    im = ax_hm.imshow(
        rd_db_shifted, aspect='auto', origin='lower', cmap='inferno',
        interpolation='nearest',
        extent=[-n_doppler // 2, n_doppler // 2, 0, n_range])
    ax_hm.set_title('Range-Doppler Map (dB, zero-vel centred)')
    ax_hm.set_xlabel('Doppler bin  →  velocity')
    ax_hm.set_ylabel('Range bin')
    cbar = plt.colorbar(im, ax=ax_hm, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(colors='white', labelsize=6)
    cbar.set_label('dB', color='white', fontsize=7)
    # Mark peak location on the shifted axes
    ax_hm.plot(peak_doppler_bin - n_doppler // 2, peak_range_bin,
               'r+', markersize=12, markeredgewidth=1.5, label='Peak target')
    ax_hm.legend(fontsize=7, facecolor='#3b3b3b', labelcolor='white',
                 edgecolor='#555')

    # B2: Doppler spectrum at the detected range bin
    doppler_spectrum = np.fft.fftshift(rd_mag[peak_range_bin, :])
    ax_dp.set_title(f'Doppler Spectrum  @ Range bin {peak_range_bin}')
    ax_dp.set_xlabel('Doppler bin (zero-centred)')
    ax_dp.set_ylabel('Magnitude')
    ax_dp.plot(doppler_cents, doppler_spectrum, color='lime', linewidth=1.0)
    ax_dp.axvline(0, color='#555', linewidth=0.7, linestyle='--',
                  label='Zero velocity')
    ax_dp.axvline(peak_doppler_bin - n_doppler // 2, color='red',
                  linewidth=1.0, linestyle=':',
                  label=f'Peak  dop bin {peak_doppler_bin}')
    ax_dp.legend(fontsize=7, facecolor='#3b3b3b', labelcolor='white',
                 edgecolor='#555')

    # B3: Power histogram (log-Y to show noise floor vs target contrast)
    ax_hist.set_title('Power Distribution')
    ax_hist.set_xlabel('Magnitude')
    ax_hist.set_ylabel('Count  (log scale)')
    ax_hist.hist(rd_mag.flatten(), bins=60, color='dodgerblue',
                 edgecolor='#1e1e1e', log=True)
    ax_hist.axvline(peak_power, color='red', linestyle='--', linewidth=1.0,
                    label=f'Peak  ({peak_power:.1f})')
    ax_hist.legend(fontsize=7, facecolor='#3b3b3b', labelcolor='white',
                   edgecolor='#555')

    # B4: 3D surface of RD map in dB (downsampled for rendering speed)
    r_step = max(1, n_range   // 50)
    d_step = max(1, n_doppler // 50)
    R_idx  = np.arange(0, n_range,   r_step)
    D_idx  = np.arange(0, n_doppler, d_step)
    Z_surf = rd_db[np.ix_(R_idx, D_idx)]
    DD, RR = np.meshgrid(D_idx, R_idx)
    ax_3d.plot_surface(DD, RR, Z_surf, cmap='viridis',
                       linewidth=0, antialiased=False, alpha=0.88)
    ax_3d.set_title('RD Surface (dB)', color='white', fontsize=8)
    ax_3d.set_xlabel('Doppler bin', fontsize=7, labelpad=4)
    ax_3d.set_ylabel('Range bin',   fontsize=7, labelpad=4)
    ax_3d.set_zlabel('dB',          fontsize=7, labelpad=4)

    # B5: Range profile with per-bin mean as noise estimate
    noise_est = rd_mag.mean(axis=1)
    ax_rp2.set_title('Range Profile + Noise Estimate')
    ax_rp2.set_xlabel('Range bin')
    ax_rp2.set_ylabel('Magnitude')
    ax_rp2.plot(range_profile, color='#ffb300', linewidth=1.0,
                label='Max over Doppler  (signal)')
    ax_rp2.plot(noise_est, color='#aaaaaa', linewidth=0.8, linestyle='--',
                label='Mean over Doppler  (noise est.)')
    ax_rp2.axvline(peak_range_bin, color='red', linestyle=':', linewidth=0.8)
    ax_rp2.legend(fontsize=7, facecolor='#3b3b3b', labelcolor='white',
                  edgecolor='#555')

    # B6: Phase evolution of the peak Doppler column
    ax_ph2.set_title(f'Phase Evolution  (Doppler col {peak_doppler_bin})')
    ax_ph2.set_xlabel('Slow-time index')
    ax_ph2.set_ylabel('Phase (rad)')
    ax_ph2.plot(slow_time_idx, phase_slow_time, color='#ff6e6e', linewidth=1.0)
    ax_ph2.set_ylim(-np.pi, np.pi)
    ax_ph2.set_yticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
    ax_ph2.set_yticklabels(['-π', '-π/2', '0', 'π/2', 'π'],
                            color='white', fontsize=7)
    ax_ph2.axhline(0, color='#555', linewidth=0.7)

    plt.show()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    path = pick_file()
    data = load(path)
    print_summary(data)
    plot_all(data)       # original six-panel overview
    analyze_rd_map(data) # new RD analysis (two figures)
