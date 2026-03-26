"""
IWR6843ISK Radar + Drone Control Dashboard

Integrated design: green-phosphor UI from radar_dashboard + real hardware pipeline
from the original main_window.

Layout:
  Header  : Logo | Status dots | Clock | FPS | [⏺ Record]
  Body    : [Left: Radar Config] [Center: 4 plots] [Right: Tracks + Drone]
  StatusBar: connection status + CPU stats
"""
from __future__ import annotations

import os
import time
import datetime
from typing import List, Optional
from unittest import case

import numpy as np
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QGroupBox, QLabel, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QLineEdit,
    QSizePolicy, QAbstractItemView, QStatusBar, QMessageBox,
)

import pyqtgraph as pg
from pyqtgraph import ColorMap

from radar.connection import RadarConnection, ConfigError
from radar.reader import RadarReader
from radar.frame_buffer import FrameBuffer
from radar.data_types import RadarFrame, PlotPoint, Target, RadarInput, Plot
from processing.detector import TLVDetector, PlotDetector
from processing.tracker import FirstPlotTracker, Tracker
from drone.px4_commander import PX4Commander

CONFIGS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'configs'))

# ─────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────
BG        = "#060a06"
BG2       = "#0b110b"
BG3       = "#0f180f"
GREEN     = "#00ff41"
GREEN_DIM = "#00a828"
AMBER     = "#ffb300"
RED       = "#ff3333"
CYAN      = "#00e5ff"
WHITE     = "#c8ffc8"
BORDER    = "#1a3a1a"

STYLE = f"""
QMainWindow, QWidget {{
    background-color: {BG};
    color: {GREEN};
    font-family: 'Courier New', monospace;
    font-size: 11px;
}}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 0px;
    margin-top: 8px;
    padding: 6px;
    font-family: 'Courier New';
    font-size: 10px;
    color: {GREEN_DIM};
    text-transform: uppercase;
    letter-spacing: 2px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    color: {GREEN_DIM};
    letter-spacing: 2px;
}}
QLabel {{
    color: {GREEN};
    background: transparent;
}}
QPushButton {{
    background-color: rgba(0,40,10,180);
    color: {GREEN};
    border: 1px solid {GREEN_DIM};
    border-radius: 0px;
    padding: 5px 12px;
    font-family: 'Courier New';
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QPushButton:hover {{
    background-color: {GREEN};
    color: {BG};
}}
QPushButton:pressed {{
    background-color: {GREEN_DIM};
}}
QPushButton:disabled {{
    color: #334433;
    border-color: #223322;
    background: rgba(0,20,5,100);
}}
QPushButton#amberBtn {{
    color: {AMBER};
    border-color: {AMBER};
    background: rgba(40,28,0,180);
}}
QPushButton#amberBtn:hover {{
    background: {AMBER};
    color: {BG};
}}
QPushButton#redBtn {{
    color: {RED};
    border-color: {RED};
    background: rgba(40,0,0,180);
    font-weight: bold;
}}
QPushButton#redBtn:hover {{
    background: {RED};
    color: white;
}}
QPushButton#connectedBtn {{
    color: {BG};
    background: {GREEN};
    border-color: {GREEN};
}}
QPushButton#recordingBtn {{
    color: {BG};
    background: #aa44aa;
    border-color: #cc66cc;
}}
QComboBox {{
    background: {BG2};
    color: {GREEN};
    border: 1px solid {BORDER};
    border-radius: 0px;
    padding: 4px 8px;
    font-family: 'Courier New';
}}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background: {BG2};
    color: {GREEN};
    selection-background-color: rgba(0,255,65,0.2);
    border: 1px solid {BORDER};
}}
QLineEdit {{
    background: {BG2};
    color: {GREEN};
    border: 1px solid {BORDER};
    border-radius: 0px;
    padding: 4px 8px;
    font-family: 'Courier New';
}}
QLineEdit:focus {{
    border-color: {GREEN};
}}
QTableWidget {{
    background: {BG};
    color: {WHITE};
    border: 1px solid {BORDER};
    gridline-color: {BG3};
    font-family: 'Courier New';
    font-size: 11px;
    selection-background-color: rgba(0,255,65,0.15);
    selection-color: {GREEN};
}}
QTableWidget::item {{
    padding: 4px 6px;
    border-bottom: 1px solid {BG3};
}}
QTableWidget::item:selected {{
    background: rgba(0,255,65,0.15);
    color: {GREEN};
}}
QHeaderView::section {{
    background: {BG2};
    color: {GREEN_DIM};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 4px 6px;
    font-family: 'Courier New';
    font-size: 9px;
    letter-spacing: 2px;
    text-transform: uppercase;
}}
QTextEdit {{
    background: {BG};
    color: {WHITE};
    border: 1px solid {BORDER};
    font-family: 'Courier New';
    font-size: 10px;
}}
QScrollBar:vertical {{
    background: {BG2};
    width: 6px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
}}
QStatusBar {{
    background: {BG2};
    color: {GREEN_DIM};
    border-top: 1px solid {BORDER};
    font-family: 'Courier New';
    font-size: 10px;
}}
"""

# ─────────────────────────────────────────────
# RADAR CONFIG PROFILES
# ─────────────────────────────────────────────
WAVEFORMS = {
    "WF1 — Short Range (0–5m)": {
        "cfg_file":     "WF1.cfg",
    },
    "WF2 — Medium Range (0–10m)": {
        "cfg_file":     "WF2.cfg",
    },
    "WF3 — Long Range (0–20m)": {
        "cfg_file":     "WF3.cfg",
    },
    "WF4 — High Velocity": {
        "cfg_file":     "WF4.cfg",
    },
}

DETECTORS = {
    "TLV Detector (Phase 1)": TLVDetector,
}

# Speed of light (m/s)
_C = 299792458


def _parse_radar_profile(cfg_path: str):
    """Parse profileCfg from a .cfg file.

    Returns (slope_MHz_per_us, rate_ksps) extracted from the profileCfg line.
    The fields are (0-indexed after 'profileCfg' keyword):
      idx 7 = freqSlopeConst (MHz/µs)   idx 10 = digOutSampleRate (ksps)
    """
    try:
        with open(cfg_path, 'r') as f:
            for line in f:
                parts = line.split()
                if parts and parts[0] == 'profileCfg' and len(parts) >= 12:
                    slope = float(parts[8]) * 1e12    # freqSlopeConst  (MHz/µs) --> Hz/s
                    rate  = float(parts[11]) * 1e3   # digOutSampleRate (ksps) --> sps
                    lambda_m = _C / (float(parts[2]) * 1e9)  # wavelength (m)
                    pri = float(parts[5])*1e-6 + float(parts[3])*1e-6   # pulse repetition interval (s)
                    n_samples = float(parts[10])  # numAdcSamples
                    return slope, rate, lambda_m, pri, n_samples
    except (OSError, ValueError, IndexError):
        pass
    return None, None, None, None, None

def _calculate_virtual_array_length(cfg_path: str):
    try:
        with open(cfg_path, 'r') as f:
            for line in f:
                parts = line.split()
                if parts and parts[0] == 'channelCfg':
                    nrx = bin(int(parts[1])).count('1')    # Parse the number of active Rx and Tx antennas based on the bitmask
                    ntx = bin(int(parts[2])).count('1')   # Count the number of '1' bits in RxEn and TxEn
                    return nrx, ntx, nrx * ntx
    except (OSError, ValueError, IndexError):
        pass
    return None

def _find_1d_cfars(rp, guard_len=2, noise_len=8):
    """Simple 1D CFAR implementation for demonstration purposes."""
    rp_linear_scaled = 10 ** (rp / 10)  # Convert to linear scale  
    num_cells = len(rp)
    cfar = np.zeros(num_cells)
    for i in range(num_cells):
        start_noiseA = max(0, i - guard_len - noise_len)
        end_noiseA = max(0, i - guard_len)
        start_noiseB = min(num_cells, i + guard_len + 1)
        end_noiseB = min(num_cells, i + guard_len + noise_len + 1)
        noise_cells = np.concatenate((rp_linear_scaled[start_noiseA:end_noiseA], rp_linear_scaled[start_noiseB:end_noiseB]))
        noise_level = np.mean(noise_cells) if len(noise_cells) > 0 else 0
        cfar[i] = noise_level
    return 10 * np.log10(cfar)  # Convert back to dB

def compress_to_middle(vec, rp):
    result = []
    group = [vec[0]]

    for i in range(1, len(vec)):
        if ((i == 1) and (vec[i] == vec[i-1] + 1)):
            group.append(vec[i])
        elif ((i > 1) and ((vec[i] == vec[i-1] + 1) or (vec[i] == vec[i-2] + 2))):
            group.append(vec[i])
        else:
            # take middle of current group
            mid = np.argmax(rp[group]) 
            result.append(group[mid])
            group = [vec[i]]

    # last group
    mid = np.argmax(rp[group]) #[len(group)//2]
    result.append(group[mid])
    return result

def _find_scatters(x, rp, cfar_line, cfar_parameter_1d_db=12):  
    """Find scatter points where the range profile exceeds the CFAR threshold."""
    cfar_th = cfar_line + cfar_parameter_1d_db
    p = np.where(rp > cfar_th)[0]
    p = compress_to_middle(p, rp)
    return x[p], rp[p]

def _parse_frame_profile(cfg_path: str):
    try:
        with open(cfg_path, 'r') as f:
            for line in f:
                parts = line.split()
                if parts and parts[0] == 'frameCfg':
                    n_Pri = int(parts[3])  # number of chirp in frame
                    return n_Pri
    except (OSError, ValueError, IndexError):
        pass
    return None

def _compute_max_range(cfg_path: str) -> float:
    """Max unambiguous range from radar profile parameters.

    Formula (FMCW): max_range = (B / S) × (c / 2)
    where B = Nyquist beat BW = rate_sps / 2  and  S = slope_hz_per_s.
    Simplifies to: max_range = rate_sps × c / (4 × slope_hz_per_s).
    """
    slope, rate_sample, lambda_m, pri, n_samples = _parse_radar_profile(cfg_path)
    return rate_sample * _C / (2.0 * slope)  # TODO : check in factor 2 is missing

def _compute_range_resolution(cfg_path: str) -> float:

    slope, rate_sample, lambda_m, pri, n_samples = _parse_radar_profile(cfg_path)
    bandwidth = slope * n_samples / rate_sample
    return _C / (2.0 * bandwidth) 

def _compute_max_velocity(cfg_path: str) -> float:
    """Max unambiguous velocity from radar profile parameters.

    Formula (FMCW): max_velocity = (λ / (2 × T × N_tx))
    where λ = wavelength, T = pulse repetition interval, N_tx = number of transmit antennas.
    """
    slope, rate, lambda_m, pri, n_samples= _parse_radar_profile(cfg_path)
    nrx, ntx, nva = _calculate_virtual_array_length(cfg_path)
    return lambda_m / (2.0 * pri * ntx)  # λ / (2 × T × N_tx)

def _compute_velocity_resolution(cfg_path: str) -> float:

    max_velocity = _compute_max_velocity(cfg_path)
    num_of_loops = _parse_frame_profile(cfg_path)
    return max_velocity / num_of_loops  

# ─────────────────────────────────────────────
# COLORMAPS
# ─────────────────────────────────────────────
def make_radar_colormap() -> ColorMap:
    """Green-phosphor: black → dark green → bright green → amber → white."""
    positions = [0.0, 0.3, 0.6, 0.85, 1.0]
    colors = [
        (6,   10,  6,  255),
        (0,   60,  15, 255),
        (0,  200,  50, 255),
        (255, 179,  0, 255),
        (255, 255, 220, 255),
    ]
    #return ColorMap(pos=np.array(positions), color=np.array(colors))
    return pg.colormap.get('viridis')  # Alternative: use a built-in perceptually uniform colormap


# ─────────────────────────────────────────────
# SIMULATED DATA  (demo mode — no hardware)
# ─────────────────────────────────────────────
class RadarDataSimulator:
    def __init__(self):
        self.n_range   = 256
        self.n_doppler = 64
        self.n_az      = 64
        self.targets = [
            {"range": 0.25, "doppler": 0.45, "az": 0.55, "amp": 1.0,  "vel": -0.42, "az_deg":  12},
            {"range": 0.54, "doppler": 0.35, "az": 0.32, "amp": 0.6,  "vel": +1.15, "az_deg": -24},
            {"range": 0.78, "doppler": 0.52, "az": 0.60, "amp": 0.35, "vel": +0.03, "az_deg":  +5},
        ]

    def generate_range_profile(self, max_range_m: float):
        x      = np.linspace(0, 1, self.n_range)
        signal = np.random.randn(self.n_range) * 0.03 + 0.05
        for t in self.targets:
            signal += t["amp"] * 0.8 * np.exp(-((x - t["range"]) ** 2) / 0.0008)
        for t in self.targets:
            t["range"] = float(np.clip(t["range"] + np.random.randn() * 0.001, 0.05, 0.95))
        return np.clip(signal, 0, 1), np.linspace(0, max_range_m, self.n_range)

    def generate_range_doppler(self):
        img = np.random.rand(self.n_doppler, self.n_range) * 0.05
        for t in self.targets:
            ri = int(t["range"]  * self.n_range)
            di = int(t["doppler"] * self.n_doppler)
            for dr in range(-6, 7):
                for dc in range(-6, 7):
                    val = t["amp"] * np.exp(-(dr**2 + dc**2) / 12)
                    if 0 <= ri + dc < self.n_range and 0 <= di + dr < self.n_doppler:
                        img[di + dr, ri + dc] += val
        return np.clip(img, 0, 1)

    def generate_range_azimuth(self):
        img = np.random.rand(self.n_az, self.n_range) * 0.04
        for t in self.targets:
            ri = int(t["range"] * self.n_range)
            ai = int(t["az"]    * self.n_az)
            for dr in range(-5, 6):
                for dc in range(-5, 6):
                    val = t["amp"] * np.exp(-(dr**2 + dc**2) / 8)
                    if 0 <= ri + dc < self.n_range and 0 <= ai + dr < self.n_az:
                        img[ai + dr, ri + dc] += val
        return np.clip(img, 0, 1)

    def generate_tracks(self, max_range_m: float) -> List[dict]:
        tracks = []
        for i, t in enumerate(self.targets):
            r   = t["range"]  * max_range_m + np.random.randn() * 0.01
            vel = t["vel"]    + np.random.randn() * 0.02
            az  = t["az_deg"] + np.random.randn() * 0.15
            tracks.append({
                "tid":   f"T-{i+1:02d}",
                "range": round(float(r),   2),
                "vel":   round(float(vel), 3),
                "az":    round(float(az),  1),
                "snr":   round(18.0 - i * 4 + float(np.random.randn()), 1),
                "x":     round(float(r * np.sin(np.deg2rad(az))), 2),
                "y":     round(float(r * np.cos(np.deg2rad(az))), 2),
            })
        return tracks


# ─────────────────────────────────────────────
# PARAM ROW HELPER
# ─────────────────────────────────────────────
def make_param_row(key: str, value: str, val_color: str = WHITE):
    row = QWidget()
    row.setStyleSheet("background: transparent;")
    hl = QHBoxLayout(row)
    hl.setContentsMargins(2, 1, 2, 1)
    k_lbl = QLabel(key)
    k_lbl.setStyleSheet(f"color: {GREEN_DIM}; font-size: 10px;")
    v_lbl = QLabel(value)
    v_lbl.setStyleSheet(f"color: {val_color}; font-size: 10px;")
    v_lbl.setAlignment(Qt.AlignRight)
    hl.addWidget(k_lbl)
    hl.addStretch()
    hl.addWidget(v_lbl)
    return row, v_lbl


# ─────────────────────────────────────────────
# LEFT PANEL — Radar Config
# ─────────────────────────────────────────────
class RadarConfigPanel(QWidget):
    radar_connect_requested    = pyqtSignal(str, str, str)  # cfg_port, data_port, cfg_file
    radar_disconnect_requested = pyqtSignal()
    radar_send_config_requested = pyqtSignal(str, str, str) # cfg_port, data_port, cfg_file
    radar_start_requested      = pyqtSignal()
    waveform_changed           = pyqtSignal(dict)
    detector_changed           = pyqtSignal(str)            # detector label

    def __init__(self):
        super().__init__()
        self.connected = False
        self._build()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(6, 6, 6, 6)
        vl.setSpacing(6)

        title = QLabel("● RADAR CONFIG")
        title.setStyleSheet(
            f"color:{GREEN}; font-size:11px; letter-spacing:3px; "
            f"border-bottom:1px solid {BORDER}; padding-bottom:6px;"
        )
        vl.addWidget(title)

        # ── Waveform selector
        wf_grp = QGroupBox("Waveform Profile")
        wf_vl  = QVBoxLayout(wf_grp)
        self.wf_combo = QComboBox()
        for name in WAVEFORMS:
            self.wf_combo.addItem(name)
        self.wf_combo.currentIndexChanged.connect(self._on_wf_changed)
        wf_vl.addWidget(self.wf_combo)
        vl.addWidget(wf_grp)

        # ── Parameters display
        params_grp = QGroupBox("Parameters")
        params_vl  = QVBoxLayout(params_grp)
        params_vl.setSpacing(2)
        self._param_labels: dict = {}
        param_keys = [
            ("start_freq",   "Start Freq"),
            ("range_res",    "Range Res"),
            ("max_range",    "Max Range"),
            ("vel_res",      "Vel Res"),
            ("max_velocity", "Max Velocity"),
            ("az_res",       "Az Res"),
            ("cfg_file",     "Config File"),
        ]
        wf = WAVEFORMS[self.wf_combo.currentText()]
        cfg_path = os.path.normpath(os.path.join(CONFIGS_DIR, wf['cfg_file']))
        max_range_m = _compute_max_range(cfg_path)
        range_resolution_m: float = _compute_range_resolution(cfg_path)
        max_velocity_m_s: float = _compute_max_velocity(cfg_path)
        velocity_resolution_m_s: float = _compute_velocity_resolution(cfg_path)
        nrx, ntx, nva = _calculate_virtual_array_length(cfg_path)

        
        for key, label in param_keys:
            if key == "start_freq":
                wf_val = '60GHz'
            if key == "max_range":
                wf_val = f"{max_range_m:.3f} m"
            if key == "max_velocity":
                wf_val = f"{max_velocity_m_s:.3f} m/s"
            if key == "range_res":
                wf_val = f"{range_resolution_m:.3f} m"
            if key == "vel_res":
                wf_val = f"{velocity_resolution_m_s:.3f} m/s"
            if key == "az_res":
                if ntx == 1:
                    wf_val = "30 deg"
                elif ntx == 2:
                    wf_val =  "15 deg"
                elif ntx == 3:
                    wf_val =  "15 deg + elevation"
            if key == "cfg_file":
                wf_val = wf['cfg_file']
            row_w, val_lbl = make_param_row(label, wf_val,
                                            AMBER if key == "cfg_file" else WHITE)
            self._param_labels[key] = val_lbl
            params_vl.addWidget(row_w)
        vl.addWidget(params_grp)

        # ── Connection
        conn_grp = QGroupBox("Connection")
        conn_vl  = QVBoxLayout(conn_grp)
        conn_vl.setSpacing(4)

        for label, attr, default in [
            ("CFG Port", "cfg_port_edit", "/dev/ttyUSB0"),
            ("DAT Port", "dat_port_edit", "/dev/ttyUSB1"),
        ]:
            row = QWidget()
            hl  = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(QLabel(label + ":"))
            edit = QLineEdit(default)
            edit.setMaximumWidth(110)
            hl.addStretch()
            hl.addWidget(edit)
            setattr(self, attr, edit)
            conn_vl.addWidget(row)

        self.connect_btn = QPushButton("Connect Radar")
        self.connect_btn.clicked.connect(self._on_connect_toggle)
        conn_vl.addWidget(self.connect_btn)

        self.send_cfg_btn = QPushButton("Send Config")
        self.send_cfg_btn.setObjectName("amberBtn")
        self.send_cfg_btn.setEnabled(False)
        self.send_cfg_btn.clicked.connect(self._on_send_cfg_clicked)
        conn_vl.addWidget(self.send_cfg_btn)

        self.start_btn = QPushButton("▶ Start Sensor")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.radar_start_requested)
        conn_vl.addWidget(self.start_btn)

        vl.addWidget(conn_grp)
        vl.addStretch()

    def _on_wf_changed(self):
        wf = WAVEFORMS[self.wf_combo.currentText()]
        for key, lbl in self._param_labels.items():
            lbl.setText(wf[key])
        self.waveform_changed.emit(wf)

    def _on_connect_toggle(self):
        if not self.connected:
            self.connected = True
            self.connect_btn.setText("Disconnect Radar")
            self.connect_btn.setObjectName("connectedBtn")
            self.connect_btn.setStyle(self.connect_btn.style())
            self.send_cfg_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
            wf = WAVEFORMS[self.wf_combo.currentText()]
            self.radar_connect_requested.emit(
                self.cfg_port_edit.text(),
                self.dat_port_edit.text(),
                wf["cfg_file"],
            )
        else:
            self.connected = False
            self.connect_btn.setText("Connect Radar")
            self.connect_btn.setObjectName("")
            self.connect_btn.setStyle(self.connect_btn.style())
            self.send_cfg_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            self.radar_disconnect_requested.emit()

    def _on_send_cfg_clicked(self):
        wf = WAVEFORMS[self.wf_combo.currentText()]
        self.radar_send_config_requested.emit(
            self.cfg_port_edit.text(),
            self.dat_port_edit.text(),
            wf["cfg_file"],
        )

    def current_params(self) -> dict:
        return WAVEFORMS[self.wf_combo.currentText()]


# ─────────────────────────────────────────────
# RIGHT PANEL — Tracks + Drone
# ─────────────────────────────────────────────
class TrackDronePanel(QWidget):
    target_selected            = pyqtSignal(dict)
    drone_connect_requested    = pyqtSignal(str)
    drone_disconnect_requested = pyqtSignal()
    goto_requested             = pyqtSignal(dict)
    estop_requested            = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.drone_connected = False
        self.selected_track: Optional[dict] = None
        self._tracks: List[dict] = []
        self._build()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(6, 6, 6, 6)
        vl.setSpacing(6)

        title = QLabel("● TRACK & DRONE")
        title.setStyleSheet(
            f"color:{GREEN}; font-size:11px; letter-spacing:3px; "
            f"border-bottom:1px solid {BORDER}; padding-bottom:6px;"
        )
        vl.addWidget(title)

        # ── Track list
        track_grp = QGroupBox("Track List")
        track_vl  = QVBoxLayout(track_grp)
        track_vl.setSpacing(4)

        self.track_table = QTableWidget(0, 5)
        self.track_table.setHorizontalHeaderLabels(["TID", "Range", "Vel", "Az", "SNR"])
        self.track_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.track_table.verticalHeader().setVisible(False)
        self.track_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.track_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.track_table.setMinimumHeight(200)
        self.track_table.itemSelectionChanged.connect(self._on_track_selected)
        track_vl.addWidget(self.track_table)

        track_btn_row = QHBoxLayout()
        self.auto_select_btn = QPushButton("Auto Select")
        self.lock_btn        = QPushButton("Lock Target")
        self.lock_btn.setObjectName("amberBtn")
        self.lock_btn.setEnabled(False)
        track_btn_row.addWidget(self.auto_select_btn)
        track_btn_row.addWidget(self.lock_btn)
        track_vl.addLayout(track_btn_row)
        vl.addWidget(track_grp)

        self.sel_target_lbl = QLabel("No target selected")
        self.sel_target_lbl.setStyleSheet(
            f"color:{AMBER}; font-size:10px; border:1px solid {BORDER}; padding:4px;"
        )
        vl.addWidget(self.sel_target_lbl)

        # ── Drone interface
        drone_grp = QGroupBox("Drone Interface")
        drone_vl  = QVBoxLayout(drone_grp)
        drone_vl.setSpacing(4)

        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("IP:"))
        self.drone_ip_edit = QLineEdit("192.168.4.1")
        self.drone_ip_edit.setMaximumWidth(110)
        ip_row.addWidget(self.drone_ip_edit)
        ip_row.addStretch()
        drone_vl.addLayout(ip_row)

        telem_keys = [
            ("status",  "Status",   "DISCONNECTED", RED),
            ("battery", "Battery",  "—",            AMBER),
            ("alt",     "Altitude", "—",            WHITE),
            ("yaw",     "Yaw",      "—",            WHITE),
        ]
        self._telem_labels: dict = {}
        for key, label, default, color in telem_keys:
            row_w, val_lbl = make_param_row(label, default, color)
            self._telem_labels[key] = val_lbl
            drone_vl.addWidget(row_w)

        from PyQt5.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(4)
        self.drone_conn_btn = QPushButton("Connect")
        self.takeoff_btn    = QPushButton("Takeoff")
        self.goto_btn       = QPushButton("Go-To Target")
        self.land_btn       = QPushButton("Land")
        self.goto_btn.setObjectName("amberBtn")
        self.takeoff_btn.setEnabled(False)
        self.goto_btn.setEnabled(False)
        self.land_btn.setEnabled(False)
        grid.addWidget(self.drone_conn_btn, 0, 0)
        grid.addWidget(self.takeoff_btn,    0, 1)
        grid.addWidget(self.goto_btn,       1, 0)
        grid.addWidget(self.land_btn,       1, 1)
        drone_vl.addLayout(grid)

        self.estop_btn = QPushButton("⚠  EMERGENCY STOP")
        self.estop_btn.setObjectName("redBtn")
        self.estop_btn.setEnabled(False)
        drone_vl.addWidget(self.estop_btn)

        vl.addWidget(drone_grp)

        # Signals
        self.drone_conn_btn.clicked.connect(self._on_drone_connect_toggle)
        self.goto_btn.clicked.connect(self._on_goto)
        self.estop_btn.clicked.connect(self.estop_requested)
        self.auto_select_btn.clicked.connect(self._auto_select)

    def update_tracks(self, tracks: List[dict]) -> None:
        sel_tid = None
        sel_row = self.track_table.currentRow()
        if sel_row >= 0 and sel_row < len(self._tracks):
            item = self.track_table.item(sel_row, 0)
            if item:
                sel_tid = item.text()

        self._tracks = tracks
        self.track_table.setRowCount(len(tracks))
        for i, t in enumerate(tracks):
            vals   = [t["tid"], f"{t['range']:.2f}m",
                      f"{t['vel']:+.2f}", f"{t['az']:+.1f}°", f"{t['snr']:.1f}dB"]
            colors = [CYAN, WHITE, AMBER if abs(t["vel"]) > 1 else WHITE, WHITE, WHITE]
            for j, (v, c) in enumerate(zip(vals, colors)):
                item = QTableWidgetItem(v)
                item.setForeground(QColor(c))
                item.setTextAlignment(Qt.AlignCenter)
                self.track_table.setItem(i, j, item)
            if t["tid"] == sel_tid:
                self.track_table.selectRow(i)

    def _on_track_selected(self):
        row = self.track_table.currentRow()
        if row < 0 or row >= len(self._tracks):
            return
        t = self._tracks[row]
        self.selected_track = t
        self.lock_btn.setEnabled(True)
        self.sel_target_lbl.setText(
            f"TARGET: {t['tid']}  |  {t['range']:.2f}m  |  {t['vel']:+.2f}m/s  |  Az {t['az']:+.1f}°"
        )
        if self.drone_connected:
            self.goto_btn.setEnabled(True)
        self.target_selected.emit(t)

    def _auto_select(self):
        if not self._tracks:
            return
        closest = min(self._tracks, key=lambda t: t["range"])
        for i, t in enumerate(self._tracks):
            if t["tid"] == closest["tid"]:
                self.track_table.selectRow(i)
                break

    def _on_drone_connect_toggle(self):
        if not self.drone_connected:
            self.drone_connected = True
            self.drone_conn_btn.setText("Disconnect Drone")
            self.drone_conn_btn.setObjectName("connectedBtn")
            self.drone_conn_btn.setStyle(self.drone_conn_btn.style())
            self._telem_labels["status"].setText("LINKED")
            self._telem_labels["status"].setStyleSheet(f"color:{GREEN};")
            self.takeoff_btn.setEnabled(True)
            self.land_btn.setEnabled(True)
            self.estop_btn.setEnabled(True)
            if self.selected_track:
                self.goto_btn.setEnabled(True)
            self.drone_connect_requested.emit(self.drone_ip_edit.text())
        else:
            self.drone_connected = False
            self.drone_conn_btn.setText("Connect Drone")
            self.drone_conn_btn.setObjectName("")
            self.drone_conn_btn.setStyle(self.drone_conn_btn.style())
            self._telem_labels["status"].setText("DISCONNECTED")
            self._telem_labels["status"].setStyleSheet(f"color:{RED};")
            self.takeoff_btn.setEnabled(False)
            self.goto_btn.setEnabled(False)
            self.land_btn.setEnabled(False)
            self.estop_btn.setEnabled(False)
            self.drone_disconnect_requested.emit()

    def update_telemetry(self, batt: float, alt: float, yaw: float) -> None:
        self._telem_labels["battery"].setText(f"{batt:.0f}%")
        self._telem_labels["alt"].setText(f"{alt:.2f} m")
        self._telem_labels["yaw"].setText(f"{yaw:+.1f}°")

    def _on_goto(self):
        if self.selected_track:
            self.goto_requested.emit(self.selected_track)


# ─────────────────────────────────────────────
# SYSTEM LOG
# ─────────────────────────────────────────────
class SystemLog(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumHeight(180)

    def log(self, msg: str, level: str = "INFO") -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:12]
        colors = {"INFO": WHITE, "OK": GREEN, "WARN": AMBER, "ERR": RED}
        c        = colors.get(level, WHITE)
        ts_html  = f'<span style="color:{GREEN_DIM}">{ts}</span>'
        msg_html = f'<span style="color:{c}">{msg}</span>'
        self.append(f'{ts_html} &nbsp; {msg_html}')
        self.moveCursor(QTextCursor.End)


# ─────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IWR6843ISK — Radar Control Dashboard")
        self.resize(1600, 900)
        self.setStyleSheet(STYLE)

        pg.setConfigOptions(antialias=True, background=BG, foreground=GREEN)

        # Core hardware objects
        self._conn      = RadarConnection()
        self._reader: Optional[RadarReader] = None
        self._buffer    = FrameBuffer()
        self._detector: PlotDetector = TLVDetector()
        self._tracker:  Tracker      = FirstPlotTracker()
        self._commander = PX4Commander()

        # Demo mode
        self._sim       = RadarDataSimulator()
        self._cmap      = make_radar_colormap()
        self._cur_wf    = WAVEFORMS[list(WAVEFORMS.keys())[0]]
        self._frame_no  = 0
        self._connected = False

        # Computed max range from cfg (updated when waveform changes)
        _cfg0 = os.path.normpath(os.path.join(CONFIGS_DIR, self._cur_wf['cfg_file']))
        self._max_range_m: float = _compute_max_range(_cfg0)
        self._max_velocity_m_s: float = _compute_max_velocity(_cfg0)

        # FPS tracking
        self._frame_times: List[float] = []
        self._last_targets: List[dict] = []      # track dicts for the panel
        self._last_real_targets: List[Target] = []  # Target objects for commander

        self._build_ui()
        self._connect_signals()

        # Demo timer — 20 Hz, runs only when not connected to real hardware
        self._demo_timer = QTimer()
        self._demo_timer.timeout.connect(self._update_frame_demo)
        self._demo_timer.start(50)

        # Clock timer
        self._clock_timer = QTimer()
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        self.log.log("Dashboard initialised — IWR6843ISK", "OK")
        self.log.log("Running in demo mode (simulated data)", "WARN")

    # ─── BUILD UI ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())

        body = QHBoxLayout()
        body.setContentsMargins(4, 4, 4, 4)
        body.setSpacing(4)

        self.cfg_panel = RadarConfigPanel()
        self.cfg_panel.setFixedWidth(240)
        body.addWidget(self.cfg_panel)

        body.addLayout(self._make_plots(), stretch=1)

        self.track_panel = TrackDronePanel()

        right_widget = QWidget()
        right_widget.setFixedWidth(280)
        right_vl = QVBoxLayout(right_widget)
        right_vl.setSpacing(4)
        right_vl.setContentsMargins(0, 0, 0, 0)
        right_vl.addWidget(self.track_panel, stretch=3)
        right_vl.addWidget(self._make_log_panel(), stretch=1)
        body.addWidget(right_widget)

        root.addLayout(body, stretch=1)

        # Status bar
        self._status_bar   = QStatusBar()
        self._status_label = QLabel("● Demo Mode")
        self._status_label.setStyleSheet(f"color:{AMBER};")
        self._stats_label  = QLabel("")
        self._stats_label.setStyleSheet(f"color:{GREEN_DIM}; margin-left:16px;")
        self._status_bar.addWidget(self._status_label)
        self._status_bar.addWidget(self._stats_label)
        self.setStatusBar(self._status_bar)

    def _make_header(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(38)
        bar.setStyleSheet(f"background:{BG2}; border-bottom:1px solid {BORDER};")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(14, 0, 14, 0)

        logo = QLabel("RADAR<span style='color:%s'>OPS</span> // IWR6843ISK" % AMBER)
        logo.setTextFormat(Qt.RichText)
        logo.setStyleSheet(
            f"font-size:15px; letter-spacing:4px; color:{GREEN}; "
            f"font-weight:bold; background:transparent;"
        )
        hl.addWidget(logo)
        hl.addStretch()

        for dot_color, label in [(GREEN, "RADAR ACTIVE"), (AMBER, "DRONE LINKED"), (RED, "TARGETS")]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{dot_color}; font-size:10px; background:transparent;")
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"color:{dot_color}; font-size:10px; letter-spacing:2px; "
                f"background:transparent; margin-right:16px;"
            )
            hl.addWidget(dot)
            hl.addWidget(lbl)

        # FPS counter
        self._fps_label = QLabel("FPS: --")
        self._fps_label.setStyleSheet(f"color:{GREEN_DIM}; margin-right:12px; background:transparent;")
        hl.addWidget(self._fps_label)

        # Record button
        self._btn_record = QPushButton("⏺ Record")
        self._btn_record.setToolTip(
            "Save buffer snapshot (plots, range profiles, RD maps, RA maps) to .npz"
        )
        self._btn_record.setStyleSheet(
            "background:rgba(90,42,122,180); color:#cc88ff; "
            "border:1px solid #cc88ff; padding:4px 10px; font-size:10px;"
        )
        self._btn_record.clicked.connect(self._on_record)
        hl.addWidget(self._btn_record)

        self.clock_lbl = QLabel("00:00:00")
        self.clock_lbl.setStyleSheet(
            f"color:{AMBER}; font-size:14px; letter-spacing:2px; "
            f"background:transparent; margin-left:12px;"
        )
        hl.addWidget(self.clock_lbl)
        return bar

    def _make_plots(self) -> QVBoxLayout:
        vl = QVBoxLayout()
        vl.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(4)
        top.addWidget(self._make_range_profile_panel(), stretch=1)
        top.addWidget(self._make_doppler_panel(),       stretch=1)
        vl.addLayout(top, stretch=1)

        bot = QHBoxLayout()
        bot.setSpacing(4)
        bot.addWidget(self._make_azimuth_panel(),  stretch=1)
        bot.addWidget(self._make_cloud_panel(),    stretch=1)
        vl.addLayout(bot, stretch=1)

        return vl

    def _make_range_profile_panel(self) -> QGroupBox:
        grp = QGroupBox("Range Profile  —  FFT Magnitude")
        vl  = QVBoxLayout(grp)
        self.range_plot  = pg.PlotWidget()
        self.range_plot.setLabel('bottom', 'Range (m)', color=GREEN_DIM, size='9pt')
        self.range_plot.setLabel('left',   'Magnitude', color=GREEN_DIM, size='9pt')
        self.range_plot.showGrid(x=True, y=True, alpha=0.15)
        self.range_plot.enableAutoRange(axis='y')
        self.range_curve = self.range_plot.plot(pen=pg.mkPen(color=GREEN, width=1.5))
        self.noise_curve = self.range_plot.plot(pen=pg.mkPen(color=RED,   width=1))
        self.cfar_line = self.range_plot.plot(pen=pg.mkPen(color=AMBER,   width=1, style=Qt.DashLine, pos=0.25, label='CFAR', labelOpts={'color': AMBER, 'position': 0.95}))
        self.range_plot.addItem(self.cfar_line)
        # Target markers
        self.range_markers = pg.ScatterPlotItem(
            size=10, pen=pg.mkPen(CYAN), brush=pg.mkBrush(CYAN + "88")
        )
        self.range_plot.addItem(self.range_markers)

        # ── Crosshair cursor (dotted vertical + horizontal lines + coordinate label)
        _ch_pen = pg.mkPen(color='#ffffff', width=1, style=Qt.DotLine)
        self._rp_vline = pg.InfiniteLine(angle=90, movable=False, pen=_ch_pen)
        self._rp_hline = pg.InfiniteLine(angle=0,  movable=False, pen=_ch_pen)
        self._rp_coord = pg.TextItem(color=AMBER, anchor=(0, 1),
                                     fill=pg.mkBrush(BG + 'cc'))
        self.range_plot.addItem(self._rp_vline, ignoreBounds=True)
        self.range_plot.addItem(self._rp_hline, ignoreBounds=True)
        self.range_plot.addItem(self._rp_coord)
        self.range_plot.scene().sigMouseMoved.connect(self._on_rp_mouse)

        vl.addWidget(self.range_plot)
        return grp

    def _make_doppler_panel(self) -> QGroupBox:
        grp = QGroupBox("Range–Doppler Map  —  2D FFT")
        vl  = QVBoxLayout(grp)
        self.doppler_img = pg.ImageView(view=pg.PlotItem())
        self.doppler_img.ui.histogram.hide()
        self.doppler_img.ui.roiBtn.hide()
        self.doppler_img.ui.menuBtn.hide()
        pli = self.doppler_img.getView()
        pli.setLabel('bottom', 'Range (m)',      color=GREEN_DIM, size='9pt')
        pli.setLabel('left',   'Velocity (m/s)', color=GREEN_DIM, size='9pt')
        pli.setAspectLocked(False)
        pli.enableAutoRange(True)
        self.doppler_img.setColorMap(self._cmap)
        vl.addWidget(self.doppler_img)
        return grp

    def _make_azimuth_panel(self) -> QGroupBox:
        grp = QGroupBox("Range–Azimuth Map  —  Beamforming")
        vl  = QVBoxLayout(grp)
        self.azimuth_img = pg.ImageView(view=pg.PlotItem())
        self.azimuth_img.ui.histogram.hide()
        self.azimuth_img.ui.roiBtn.hide()
        self.azimuth_img.ui.menuBtn.hide()
        pli = self.azimuth_img.getView()
        pli.setLabel('bottom', 'Range (m)',   color=GREEN_DIM, size='9pt')
        pli.setLabel('left',   'Azimuth (°)', color=GREEN_DIM, size='9pt')
        pli.setAspectLocked(False)
        pli.enableAutoRange(True)
        self.azimuth_img.setColorMap(self._cmap)
        vl.addWidget(self.azimuth_img)
        return grp

    def _make_cloud_panel(self) -> QGroupBox:
        """Top-down X-Y scatter: green dots = raw detections, cyan triangles = tracked targets."""
        grp = QGroupBox("Point Cloud  —  Top-Down View")
        vl  = QVBoxLayout(grp)
        self.cloud_plot = pg.PlotWidget()
        self.cloud_plot.setLabel('bottom', 'X (m)', color=GREEN_DIM, size='9pt')
        self.cloud_plot.setLabel('left',   'Y (m)', color=GREEN_DIM, size='9pt')
        self.cloud_plot.showGrid(x=True, y=True, alpha=0.15)
        self.cloud_plot.setAspectLocked(True)
        # Raw plot detections
        self.cloud_plots_scatter = pg.ScatterPlotItem(
            size=7, pen=pg.mkPen(None), brush=pg.mkBrush(GREEN + "cc")
        )
        # Tracked targets
        self.cloud_tracks_scatter = pg.ScatterPlotItem(
            size=12, symbol='t', pen=pg.mkPen(CYAN, width=1.5),
            brush=pg.mkBrush(CYAN + "44")
        )
        self.cloud_plot.addItem(self.cloud_plots_scatter)
        self.cloud_plot.addItem(self.cloud_tracks_scatter)
        # Radar origin cross
        self.cloud_plot.addItem(pg.InfiniteLine(pos=0, angle=90,
            pen=pg.mkPen(color=BORDER, width=1)))
        self.cloud_plot.addItem(pg.InfiniteLine(pos=0, angle=0,
            pen=pg.mkPen(color=BORDER, width=1)))
        vl.addWidget(self.cloud_plot)
        return grp

    def _make_log_panel(self) -> QGroupBox:
        grp = QGroupBox("System Log")
        vl  = QVBoxLayout(grp)
        self.log = SystemLog()
        vl.addWidget(self.log)
        return grp

    # ─── SIGNALS ──────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self.cfg_panel.radar_connect_requested.connect(self._on_radar_connect)
        self.cfg_panel.radar_disconnect_requested.connect(self._on_radar_disconnect)
        self.cfg_panel.radar_send_config_requested.connect(self._on_radar_send_config)
        self.cfg_panel.radar_start_requested.connect(self._on_radar_start)
        self.cfg_panel.waveform_changed.connect(self._on_wf_changed)
        self.cfg_panel.detector_changed.connect(self._on_detector_changed)

        self.track_panel.drone_connect_requested.connect(self._on_drone_connect)
        self.track_panel.drone_disconnect_requested.connect(self._on_drone_disconnect)
        self.track_panel.goto_requested.connect(self._on_goto)
        self.track_panel.estop_requested.connect(self._on_estop)
        self.track_panel.target_selected.connect(self._on_target_selected)

    # ─── RADAR CONNECT / DISCONNECT ───────────────────────────────────

    def _on_radar_connect(self, cfg_port: str, dat_port: str, cfg_file: str) -> None:
        self.log.log(f"Connecting → CFG:{cfg_port}  DAT:{dat_port}", "INFO")
        cfg_path = os.path.normpath(os.path.join(CONFIGS_DIR, cfg_file))
        try:
            self._conn.connect(cfg_port, dat_port)
            self._conn.send_config(cfg_path)
        except (ConnectionError, ConfigError, FileNotFoundError) as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self._conn.disconnect()
            self.cfg_panel._on_connect_toggle()  # revert button state
            return

        self._reader = RadarReader(self._conn.get_data_serial())
        self._reader.frame_received.connect(self._on_frame)
        self._reader.error_occurred.connect(self._on_reader_error)
        self._reader.start()

        self._buffer.clear()
        self._connected = True
        self._demo_timer.stop()

        self._set_status(f"● Connected — {cfg_file}", GREEN)
        self.log.log(f"Radar connected — streaming: {cfg_file}", "OK")

    def _on_radar_disconnect(self) -> None:
        if self._reader:
            self._reader.stop()
            self._reader = None
        self._conn.disconnect()
        self._connected = False
        self._demo_timer.start(50)
        self._set_status("● Demo Mode", AMBER)
        self.log.log("Radar disconnected — demo mode resumed", "WARN")

    def _on_radar_send_config(self, cfg_port: str, dat_port: str, cfg_file: str) -> None:
        """Re-send the config file to an already-connected radar."""
        if not self._conn.is_connected:
            self.log.log("Send Config: not connected", "WARN")
            return
        cfg_path = os.path.normpath(os.path.join(CONFIGS_DIR, cfg_file))
        self.log.log(f"Re-sending config: {cfg_file}", "INFO")
        try:
            self._conn.send_config(cfg_path)
            self.log.log(f"Config sent: {cfg_file}", "OK")
        except (ConfigError, FileNotFoundError) as e:
            QMessageBox.critical(self, "Config Error", str(e))

    def _on_radar_start(self) -> None:
        """Start (or restart) the radar reader thread on an already-connected radar."""
        if not self._conn.is_connected:
            self.log.log("Start Sensor: not connected", "WARN")
            return
        self._demo_timer.stop()
        if self._reader:
            self._reader.stop()
            self._reader = None
        self._reader = RadarReader(self._conn.get_data_serial())
        self._reader.frame_received.connect(self._on_frame)
        self._reader.error_occurred.connect(self._on_reader_error)
        self._reader.start()
        self._buffer.clear()
        self.log.log("Sensor (re)started — streaming", "OK")

    def _on_wf_changed(self, wf: dict) -> None:
        self._cur_wf = wf
        cfg_path = os.path.normpath(os.path.join(CONFIGS_DIR, wf['cfg_file']))
        self._max_range_m = _compute_max_range(cfg_path)
        self._max_velocity_m_s: float = _compute_max_velocity(cfg_path)
        
        self.log.log(
            f"Waveform → {wf['cfg_file']}  max_range={self._max_range_m:.2f} m", "INFO"
        )
        max_r = self._max_range_m
        self.range_plot.setXRange(0, max_r)
        self.cloud_plot.setXRange(-max_r, max_r)
        self.cloud_plot.setYRange(0, max_r)

    def _on_detector_changed(self, label: str) -> None:
        cls = DETECTORS.get(label)
        if cls:
            self._detector = cls()
            self.log.log(f"Detector → {label}", "INFO")

    # ─── REAL FRAME PROCESSING ────────────────────────────────────────

    def _on_frame(self, frame: RadarFrame) -> None:
        # 1. Buffer
        self._buffer.push(frame)
        current_radar_input = RadarInput()

        # Log first 3 frames so the user can verify data is arriving
        if len(self._buffer) <= 3:
            rp_info = f"rp={len(frame.range_profile)} bins" if frame.range_profile is not None else "rp=None"
            rd_info = "rd=yes" if frame.range_doppler is not None else "rd=None"
            self.log.log(
                f"Frame #{frame.frame_number}: {len(frame.detected_points)} pts  {rp_info}  {rd_info}",
                "INFO",
            )

        # 3. Range profile + noise floor
        rp = self._buffer.latest_range_profile
        np_ = self._buffer.latest_noise_profile
        if rp is not None and rp.size > 0:
            x = np.linspace(0, self._max_range_m, len(rp))
            self.range_curve.setData(x, np.abs(rp))
            cfar_line = _find_1d_cfars(rp, guard_len=2, noise_len=8)
            self.cfar_line.setData(x, cfar_line)
            px, py = _find_scatters(x, rp, cfar_line, cfar_parameter_1d_db=1.3)
            current_radar_input.range_detected_targets = px
            self.range_markers.setData(px, py)
            if np_ is not None and np_.size > 0:
                self.noise_curve.setData(x[:len(np_)], np.abs(np_))

        # 4. Range-Doppler heatmap
        rd = self._buffer.latest_rd_map
        cfg_path = os.path.normpath(os.path.join(CONFIGS_DIR, self._cur_wf['cfg_file']))
        
        if rd is not None:
            if rd.ndim == 1:
                rd = self._reshape_rd(rd, cfg_path)
            rd = np.fft.fftshift(rd, axes=1)  # center Doppler at 0
            rd_db = 20 * np.log10(np.abs(rd) + 1e-6)  # convert to dB
            current_radar_input.range_doppler_map = rd_db
            rd_scale = (rd_db - rd_db.min())/(rd_db.max() - rd_db.min() + 1e-6) * 255  # normalize to [0, 255]
            range_res    = self._max_range_m    / rd.shape[0]
            velocity_res = 2*self._max_velocity_m_s / rd.shape[1]  # adjust if centered at 0
            rd_cut = rd_scale[0:(rd.shape[0]//2),:]  # show only up to max range (ignore wrap-around)
            start_y_rd = -self._max_velocity_m_s - (0.5 * velocity_res)
            current_radar_input.range_axis_rd = np.linspace(0, self._max_range_m, rd.shape[0])  
            current_radar_input.velocity_axis = np.linspace(start_y_rd, self._max_velocity_m_s - (0.5 * velocity_res), rd.shape[1])
            self.doppler_img.setImage(rd_cut, pos=(0,start_y_rd) ,scale=(range_res, velocity_res), levels=(0, 255))

        # 5. Range-Azimuth heatmap
        ra = self._buffer.latest_ra_map
        nrx, ntx, nva = _calculate_virtual_array_length(cfg_path)
        if (ra is not None) & (ra.ndim == 1):
            ra=ra.reshape(-1,nva)
            ra = np.fft.fftshift(np.fft.fft(ra,axis=1),axes=1)
            ra_dB = 20 * np.log10(np.abs(ra) + 1e-6)  # convert to dB
            current_radar_input.range_azimuth_map = ra_dB
            ra_scale = (ra_dB - ra_dB.min())/(ra_dB.max() - ra_dB.min() + 1e-6) * 255  # normalize to [0, 255]
            current_radar_input.azimuth_axis = np.rad2deg(np.arcsin(2*np.fft.fftshift(np.fft.fftfreq(nva,1))))
            current_radar_input.range_axis_ra = np.linspace(0, self._max_range_m, ra.shape[0])  
            range_res    = self._max_range_m    / ra.shape[0]
            match nva:
                case 4:
                    azimuth_res = 30
                case 8,12:
                    azimuth_res = 15
                case _:
                    azimuth_res = 15
            start_y_ra = -60 + (0.5 * azimuth_res)
            self.azimuth_img.setImage(ra_scale, pos=(0, start_y_ra), scale=(range_res, azimuth_res), levels=(0, 255))

        # 2. Detect + Track
        plots:   List[Plot] = self._detector.detect(current_radar_input)
        targets: List[Target] = self._tracker.update(plots, self._last_real_targets, azimuth_res, velocity_res, range_res)

        # 6. Point cloud (top-down X-Y)
        #if plots:
        #    self.cloud_plots_scatter.setData(
        #        [p.x for p in plots], [p.y for p in plots]
        #    )
        if targets:
            self.cloud_tracks_scatter.setData(
                [t.x for t in targets], [t.y for t in targets]
            )

        # 7. Track table
        self._last_real_targets = targets
        track_dicts = self._targets_to_track_dicts(targets)
        self._last_targets = track_dicts
        self.track_panel.update_tracks(track_dicts)

        # 8. CPU stats (TLV6)
        if frame.statistics:
            s = frame.statistics
            self._stats_label.setText(
                f"CPU active: {s.get('activeFrameCPULoad_pct', 0)}%  "
                f"inter: {s.get('interFrameCPULoad_pct', 0)}%  "
                f"margin: {s.get('interFrameProcessingMargin_us', 0)} µs"
            )

        # 9. FPS
        now = time.monotonic()
        self._frame_times.append(now)
        self._frame_times = [t for t in self._frame_times if now - t < 2.0]
        self._fps_label.setText(f"FPS: {len(self._frame_times) / 2.0:.1f}")

    def _on_rp_mouse(self, pos) -> None:
        """Update crosshair lines and coordinate label as the mouse moves over the range plot."""
        if self.range_plot.sceneBoundingRect().contains(pos):
            mp = self.range_plot.getPlotItem().vb.mapSceneToView(pos)
            x, y = mp.x(), mp.y()
            self._rp_vline.setPos(x)
            self._rp_hline.setPos(y)
            self._rp_coord.setPos(x, y)
            self._rp_coord.setText(f"R = {x:.3f} m\nMag = {y:.4f}")

    @staticmethod
    def _reshape_rd(rd: np.ndarray, cfg_path: str) -> np.ndarray:
        """Reshape flat RD vector to 2-D (n_range × n_doppler).

        If the firmware packs multiple virtual-antenna Doppler spectra consecutively
        (e.g. 8 virtual antennas × 32 Doppler bins = 256 columns), the target
        repeats n_repeats times.  We average those repetitions so the displayed
        map has 32 unique Doppler bins.
        """
        total = rd.size
        nrx, ntx, nva = _calculate_virtual_array_length(cfg_path)
        n_pri = _parse_frame_profile(cfg_path) 
        if total % n_pri == 0:
            rd2d = rd.reshape(-1, n_pri)
            n_range, n_doppler = rd2d.shape
            if n_doppler == 256 and n_range > 0:
                rd2d = rd2d.reshape(n_range, nva, int(n_doppler/nva)).mean(axis=1)
            return rd2d
        return rd[:, np.newaxis]

    @staticmethod
    def _targets_to_track_dicts(targets: List[Target]) -> List[dict]:
        """Convert Target objects to the dict format TrackDronePanel expects."""
        tracks = []
        for t in targets:
            r  = float(np.sqrt(t.x**2 + t.y**2))
            az = float(np.degrees(np.arctan2(t.x, t.y)))
            tracks.append({
                "tid":   str(t.target_id),
                "range": round(r,          2),
                "vel":   round(t.velocity, 3),
                "az":    round(az,         1),
                "snr":   round(t.score,    1),
                "x":     round(t.x,        2),
                "y":     round(t.y,        2),
            })
        return tracks

    def _on_reader_error(self, msg: str) -> None:
        self._set_status(f"● Error: {msg}", AMBER)
        self.log.log(f"Reader error: {msg}", "ERR")

    # ─── DEMO MODE (timer-based simulation) ───────────────────────────

    def _update_frame_demo(self) -> None:
        max_r = self._max_range_m

        # Range profile
        sig, r_axis = self._sim.generate_range_profile(max_r)
        self.range_curve.setData(r_axis, sig)
        tracks = self._sim.generate_tracks(max_r)
        # Markers at target peaks
        mx = [t["range"] for t in tracks]
        my = [min(sig[max(0, int(t["range"] / max_r * len(sig)) - 1)], 1.0) for t in tracks]
        self.range_markers.setData(mx, my)

        # Range-Doppler
        dmap = self._sim.generate_range_doppler()
        self.doppler_img.setImage(
            dmap.T, autoLevels=False, levels=(0, 1),
            xvals=np.linspace(0, max_r, dmap.shape[1]),
        )

        # Range-Azimuth
        amap = self._sim.generate_range_azimuth()
        self.azimuth_img.setImage(
            amap.T, autoLevels=False, levels=(0, 1),
            xvals=np.linspace(0, max_r, amap.shape[1]),
        )

        # Point cloud (top-down)
        xs = [t["x"] for t in tracks]
        ys = [t["y"] for t in tracks]
        self.cloud_plots_scatter.setData(xs, ys)

        # Track panel
        self.track_panel.update_tracks(tracks)

        self._frame_no += 1

    # ─── RECORD ───────────────────────────────────────────────────────

    def _on_record(self) -> None:
        """Save a snapshot of the current buffer to a .npz file."""
        save_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'recordings'))
        os.makedirs(save_dir, exist_ok=True)

        ts   = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(save_dir, f'radar_snapshot_{ts}.npz')

        arrays: dict = {}

        # Per-frame plot detections: (N_points, 5) → [x, y, z, velocity, snr]
        for i, frame_pts in enumerate(self._buffer.all_plots()):
            if frame_pts:
                arrays[f'plots_frame{i}'] = np.array(
                    [[p.x, p.y, p.z, p.velocity, p.snr] for p in frame_pts],
                    dtype=np.float32,
                )
            else:
                arrays[f'plots_frame{i}'] = np.empty((0, 5), dtype=np.float32)

        rp_list = self._buffer.all_range_profiles()
        if rp_list:
            arrays['range_profiles'] = np.stack(rp_list).astype(np.float32)

        np_list = self._buffer.all_noise_profiles()
        if np_list:
            arrays['noise_profiles'] = np.stack(np_list).astype(np.float32)

        rd_list = self._buffer.all_rd_maps()
        if rd_list:
            arrays['rd_maps'] = np.stack(rd_list).astype(np.float32)

        ra_list = self._buffer.all_ra_maps()
        if ra_list:
            ra_stack = np.stack(ra_list)
            arrays['ra_maps_real'] = ra_stack.real.astype(np.float32)
            arrays['ra_maps_imag'] = ra_stack.imag.astype(np.float32)

        if not arrays:
            QMessageBox.information(self, 'Record', 'Buffer is empty — no real data to save.')
            return

        np.savez(path, **arrays)
        self._set_status(f"● Saved: {os.path.basename(path)}", CYAN)
        self.log.log(f"Snapshot saved → {os.path.basename(path)}", "OK")

        # Flash button
        self._btn_record.setStyleSheet(
            "background:#22aa22; color:white; border:1px solid #44cc44; padding:4px 10px; font-size:10px;"
        )
        QTimer.singleShot(1500, lambda: self._btn_record.setStyleSheet(
            "background:rgba(90,42,122,180); color:#cc88ff; "
            "border:1px solid #cc88ff; padding:4px 10px; font-size:10px;"
        ))

    # ─── DRONE HANDLERS ───────────────────────────────────────────────

    def _on_drone_connect(self, ip: str) -> None:
        self.log.log(f"Drone connecting → {ip}", "INFO")
        self._commander.start()
        self._commander.connect_async()
        poll = QTimer(self)
        poll.timeout.connect(lambda: self._check_drone_connected(poll))
        poll.start(500)

    def _check_drone_connected(self, timer: QTimer) -> None:
        if self._commander.is_connected:
            timer.stop()
            self.track_panel._telem_labels["status"].setText("LINKED")
            self.log.log("Drone linked", "OK")

    def _on_drone_disconnect(self) -> None:
        self._commander.stop()
        self.log.log("Drone disconnected", "WARN")

    def _on_goto(self, t: dict) -> None:
        self.log.log(
            f"Go-To → {t['tid']}  [{t['range']:.2f}m, {t['az']:+.1f}°]", "WARN"
        )
        # Find the matching Target object by ID for PX4Commander
        real_targets = [tgt for tgt in self._last_real_targets
                        if str(tgt.target_id) == t["tid"]]
        if real_targets:
            self._commander.send_highest_score(real_targets)
        elif self._last_real_targets:
            # Fall back to sending all available targets
            self._commander.send_highest_score(self._last_real_targets)

    def _on_estop(self) -> None:
        self.log.log("⚠ EMERGENCY STOP TRIGGERED", "ERR")
        # Halt the asyncio loop — stops any in-progress fly_to coroutine
        self._commander.stop()

    def _on_target_selected(self, t: dict) -> None:
        self.log.log(
            f"Target: {t['tid']}  range={t['range']:.2f}m  "
            f"vel={t['vel']:+.2f}m/s  az={t['az']:+.1f}°",
            "OK",
        )

    # ─── CLOCK ────────────────────────────────────────────────────────

    def _update_clock(self) -> None:
        self.clock_lbl.setText(datetime.datetime.now().strftime("%H:%M:%S"))

    # ─── HELPERS ──────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str) -> None:
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color:{color};")

    # ─── CLOSE ────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._demo_timer.stop()
        self._on_radar_disconnect()
        self._commander.stop()
        super().closeEvent(event)
