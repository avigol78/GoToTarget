"""
IWR6843ISK Radar + Drone Control Dashboard
PyQt5 — Production GUI
"""

import sys
import numpy as np
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QFrame, QSplitter,
    QGroupBox, QLineEdit, QSizePolicy, QAbstractItemView
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCursor

import pyqtgraph as pg
from pyqtgraph import ColorMap
import pyqtgraph.exporters

# ─────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────
BG       = "#060a06"
BG2      = "#0b110b"
BG3      = "#0f180f"
GREEN    = "#00ff41"
GREEN_DIM= "#00a828"
AMBER    = "#ffb300"
RED      = "#ff3333"
CYAN     = "#00e5ff"
WHITE    = "#c8ffc8"
BORDER   = "#1a3a1a"

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
QLabel.dim {{
    color: {GREEN_DIM};
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
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {BORDER};
}}
"""

# ─────────────────────────────────────────────
# RADAR CONFIG PROFILES
# ─────────────────────────────────────────────
WAVEFORMS = {
    "WF1 — Short Range (0–5m)": {
        "start_freq":    "60.25 GHz",
        "bandwidth":     "3.996 GHz",
        "ramp_end":      "40 µs",
        "chirps_frame":  "128",
        "frame_period":  "50 ms",
        "range_res":     "0.044 m",
        "max_range":     "5.0 m",
        "vel_res":       "0.095 m/s",
        "max_velocity":  "±2.42 m/s",
        "az_res":        "15°",
        "cfg_file":      "profile_WF1.cfg",
    },
    "WF2 — Medium Range (0–10m)": {
        "start_freq":    "60.25 GHz",
        "bandwidth":     "2.0 GHz",
        "ramp_end":      "60 µs",
        "chirps_frame":  "128",
        "frame_period":  "50 ms",
        "range_res":     "0.075 m",
        "max_range":     "10.0 m",
        "vel_res":       "0.095 m/s",
        "max_velocity":  "±4.84 m/s",
        "az_res":        "15°",
        "cfg_file":      "profile_WF2.cfg",
    },
    "WF3 — Long Range (0–20m)": {
        "start_freq":    "60.25 GHz",
        "bandwidth":     "1.0 GHz",
        "ramp_end":      "80 µs",
        "chirps_frame":  "256",
        "frame_period":  "100 ms",
        "range_res":     "0.150 m",
        "max_range":     "20.0 m",
        "vel_res":       "0.048 m/s",
        "max_velocity":  "±6.10 m/s",
        "az_res":        "15°",
        "cfg_file":      "profile_WF3.cfg",
    },
    "WF4 — High Velocity": {
        "start_freq":    "60.25 GHz",
        "bandwidth":     "1.5 GHz",
        "ramp_end":      "20 µs",
        "chirps_frame":  "256",
        "frame_period":  "33 ms",
        "range_res":     "0.100 m",
        "max_range":     "8.0 m",
        "vel_res":       "0.048 m/s",
        "max_velocity":  "±12.0 m/s",
        "az_res":        "15°",
        "cfg_file":      "profile_WF4.cfg",
    },
}

# ─────────────────────────────────────────────
# COLORMAPS for heatmaps
# ─────────────────────────────────────────────
def make_radar_colormap():
    """Green-phosphor heatmap: black → dark green → bright green → amber → white"""
    positions = [0.0, 0.3, 0.6, 0.85, 1.0]
    colors = [
        (6,  10,  6,  255),
        (0,  60,  15, 255),
        (0,  200, 50, 255),
        (255,179, 0,  255),
        (255,255,220,255),
    ]
    return ColorMap(pos=np.array(positions), color=np.array(colors))


# ─────────────────────────────────────────────
# SIMULATED DATA GENERATOR  (replace with real serial data)
# ─────────────────────────────────────────────
class RadarDataSimulator:
    """
    Replace the generate_* methods with your actual TI DCA1000 / UART parser.
    """
    def __init__(self):
        self.frame = 0
        self.n_range = 256
        self.n_doppler = 64
        self.n_az = 64
        # Simulated targets: (range_bin, doppler_bin, az_bin, amplitude)
        self.targets = [
            {"range": 0.25, "doppler": 0.45, "az": 0.55, "amp": 1.0,  "vel": -0.42, "az_deg": 12},
            {"range": 0.54, "doppler": 0.35, "az": 0.32, "amp": 0.6,  "vel": +1.15, "az_deg": -24},
            {"range": 0.78, "doppler": 0.52, "az": 0.60, "amp": 0.35, "vel": +0.03, "az_deg": +5},
        ]

    def generate_range_profile(self, max_range_m):
        x = np.linspace(0, 1, self.n_range)
        noise = np.random.randn(self.n_range) * 0.03
        signal = noise + 0.05
        for t in self.targets:
            signal += t["amp"] * 0.8 * np.exp(-((x - t["range"]) ** 2) / (0.0008))
        # drift targets slightly
        for t in self.targets:
            t["range"] += np.random.randn() * 0.001
            t["range"] = np.clip(t["range"], 0.05, 0.95)
        return np.clip(signal, 0, 1), np.linspace(0, max_range_m, self.n_range)

    def generate_range_doppler(self, max_range_m, max_vel):
        img = np.random.rand(self.n_doppler, self.n_range) * 0.05
        for t in self.targets:
            ri, di = int(t["range"] * self.n_range), int(t["doppler"] * self.n_doppler)
            for dr in range(-6, 7):
                for dc in range(-6, 7):
                    val = t["amp"] * np.exp(-(dr**2 + dc**2) / 12)
                    if 0 <= ri+dc < self.n_range and 0 <= di+dr < self.n_doppler:
                        img[di+dr, ri+dc] += val
        return np.clip(img, 0, 1)

    def generate_range_azimuth(self, max_range_m):
        img = np.random.rand(self.n_az, self.n_range) * 0.04
        for t in self.targets:
            ri, ai = int(t["range"] * self.n_range), int(t["az"] * self.n_az)
            for dr in range(-5, 6):
                for dc in range(-5, 6):
                    val = t["amp"] * np.exp(-(dr**2 + dc**2) / 8)
                    if 0 <= ri+dc < self.n_range and 0 <= ai+dr < self.n_az:
                        img[ai+dr, ri+dc] += val
        return np.clip(img, 0, 1)

    def generate_plot_list(self, max_range_m, max_vel):
        plots = []
        for t in self.targets:
            r   = t["range"] * max_range_m + np.random.randn() * 0.02
            vel = t["vel"]   + np.random.randn() * 0.05
            az  = t["az_deg"]+ np.random.randn() * 0.3
            snr = -10 * np.log10(1 - t["amp"] * 0.9 + 1e-3) + np.random.randn() * 0.5
            plots.append({"range": round(r, 2), "vel": round(vel, 2),
                          "az": round(az, 1),   "snr": round(snr, 1)})
        self.frame += 1
        return plots

    def generate_track_list(self, max_range_m):
        tracks = []
        for i, t in enumerate(self.targets):
            r   = t["range"] * max_range_m + np.random.randn() * 0.01
            vel = t["vel"]   + np.random.randn() * 0.02
            az  = t["az_deg"]+ np.random.randn() * 0.15
            tracks.append({
                "tid": f"T-{i+1:02d}",
                "range": round(r, 2),
                "vel":   round(vel, 3),
                "az":    round(az, 1),
                "snr":   round(18 - i * 4 + np.random.randn(), 1),
            })
        return tracks


# ─────────────────────────────────────────────
# PARAM ROW WIDGET
# ─────────────────────────────────────────────
def make_param_row(key, value, val_color=WHITE):
    row = QWidget()
    row.setStyleSheet(f"background: transparent;")
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
    return row, v_lbl  # return value label so we can update it


# ─────────────────────────────────────────────
# LEFT PANEL  — Radar Config
# ─────────────────────────────────────────────
class RadarConfigPanel(QWidget):
    radar_connect_requested    = pyqtSignal(str, str, str)  # cfg_port, data_port, cfg_file
    radar_disconnect_requested = pyqtSignal()
    waveform_changed           = pyqtSignal(dict)           # new waveform params

    def __init__(self):
        super().__init__()
        self.connected = False
        self._build()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(6, 6, 6, 6)
        vl.setSpacing(6)

        # ── Header label
        title = QLabel("● RADAR CONFIG")
        title.setStyleSheet(f"color:{GREEN}; font-size:11px; letter-spacing:3px; "
                            f"border-bottom:1px solid {BORDER}; padding-bottom:6px;")
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

        # ── Radar parameters display
        params_grp = QGroupBox("Parameters")
        params_vl  = QVBoxLayout(params_grp)
        params_vl.setSpacing(2)
        self._param_labels = {}
        param_keys = [
            ("start_freq",   "Start Freq"),
            ("bandwidth",    "Bandwidth"),
            ("ramp_end",     "Ramp End"),
            ("chirps_frame", "Chirps/Frame"),
            ("frame_period", "Frame Period"),
            ("range_res",    "Range Res"),
            ("max_range",    "Max Range"),
            ("vel_res",      "Vel Res"),
            ("max_velocity", "Max Velocity"),
            ("az_res",       "Az Res"),
            ("cfg_file",     "Config File"),
        ]
        wf = WAVEFORMS[self.wf_combo.currentText()]
        for key, label in param_keys:
            row_w, val_lbl = make_param_row(label, wf[key],
                                             AMBER if key == "cfg_file" else WHITE)
            self._param_labels[key] = val_lbl
            params_vl.addWidget(row_w)
        vl.addWidget(params_grp)

        # ── Serial ports
        conn_grp = QGroupBox("Connection")
        conn_vl  = QVBoxLayout(conn_grp)
        conn_vl.setSpacing(4)

        for label, attr, default in [("CFG Port", "cfg_port_edit", "COM3"),
                                      ("DAT Port", "dat_port_edit", "COM4")]:
            row = QWidget()
            hl  = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(QLabel(label + ":"))
            edit = QLineEdit(default)
            edit.setMaximumWidth(80)
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
        conn_vl.addWidget(self.send_cfg_btn)

        self.start_btn = QPushButton("▶ Start Sensor")
        self.start_btn.setEnabled(False)
        conn_vl.addWidget(self.start_btn)

        vl.addWidget(conn_grp)
        vl.addStretch()

    def _on_wf_changed(self):
        name = self.wf_combo.currentText()
        wf   = WAVEFORMS[name]
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

    def current_params(self):
        return WAVEFORMS[self.wf_combo.currentText()]


# ─────────────────────────────────────────────
# RIGHT PANEL  — Tracks + Drone
# ─────────────────────────────────────────────
class TrackDronePanel(QWidget):
    target_selected            = pyqtSignal(dict)   # selected track
    drone_connect_requested    = pyqtSignal(str)    # ip
    drone_disconnect_requested = pyqtSignal()
    goto_requested             = pyqtSignal(dict)   # target track
    estop_requested            = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.drone_connected  = False
        self.selected_track   = None
        self._build()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(6, 6, 6, 6)
        vl.setSpacing(6)

        title = QLabel("● TRACK & DRONE")
        title.setStyleSheet(f"color:{GREEN}; font-size:11px; letter-spacing:3px; "
                            f"border-bottom:1px solid {BORDER}; padding-bottom:6px;")
        vl.addWidget(title)

        # ── Track List
        track_grp = QGroupBox("Track List")
        track_vl  = QVBoxLayout(track_grp)
        track_vl.setSpacing(4)

        self.track_table = QTableWidget(0, 5)
        self.track_table.setHorizontalHeaderLabels(["TID", "Range", "Vel", "Az", "SNR"])
        self.track_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.track_table.verticalHeader().setVisible(False)
        self.track_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.track_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.track_table.setMaximumHeight(160)
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

        # Selected target info
        self.sel_target_lbl = QLabel("No target selected")
        self.sel_target_lbl.setStyleSheet(f"color:{AMBER}; font-size:10px; "
                                           f"border:1px solid {BORDER}; padding:4px;")
        vl.addWidget(self.sel_target_lbl)

        # ── Drone
        drone_grp = QGroupBox("Drone Interface")
        drone_vl  = QVBoxLayout(drone_grp)
        drone_vl.setSpacing(4)

        # IP row
        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("IP:"))
        self.drone_ip_edit = QLineEdit("192.168.4.1")
        self.drone_ip_edit.setMaximumWidth(110)
        ip_row.addWidget(self.drone_ip_edit)
        ip_row.addStretch()
        drone_vl.addLayout(ip_row)

        # Telemetry
        telem_keys = [
            ("status",  "Status",  "DISCONNECTED", RED),
            ("battery", "Battery", "—",            AMBER),
            ("alt",     "Altitude","—",            WHITE),
            ("yaw",     "Yaw",     "—",            WHITE),
        ]
        self._telem_labels = {}
        for key, label, default, color in telem_keys:
            row_w, val_lbl = make_param_row(label, default, color)
            self._telem_labels[key] = val_lbl
            drone_vl.addWidget(row_w)

        # Buttons grid
        grid = QGridLayout()
        grid.setSpacing(4)
        self.drone_conn_btn  = QPushButton("Connect")
        self.takeoff_btn     = QPushButton("Takeoff")
        self.goto_btn        = QPushButton("Go-To Target")
        self.land_btn        = QPushButton("Land")
        self.goto_btn.setObjectName("amberBtn")
        self.takeoff_btn.setEnabled(False)
        self.goto_btn.setEnabled(False)
        self.land_btn.setEnabled(False)
        grid.addWidget(self.drone_conn_btn, 0, 0)
        grid.addWidget(self.takeoff_btn,   0, 1)
        grid.addWidget(self.goto_btn,      1, 0)
        grid.addWidget(self.land_btn,      1, 1)
        drone_vl.addLayout(grid)

        self.estop_btn = QPushButton("⚠  EMERGENCY STOP")
        self.estop_btn.setObjectName("redBtn")
        self.estop_btn.setEnabled(False)
        drone_vl.addWidget(self.estop_btn)

        vl.addWidget(drone_grp)
        vl.addStretch()

        # ── Signals
        self.drone_conn_btn.clicked.connect(self._on_drone_connect_toggle)
        self.goto_btn.clicked.connect(self._on_goto)
        self.estop_btn.clicked.connect(self.estop_requested)
        self.auto_select_btn.clicked.connect(self._auto_select)

    # ── Track updates from main window
    def update_tracks(self, tracks: list):
        sel_tid = None
        sel_row = self.track_table.currentRow()
        if sel_row >= 0:
            item = self.track_table.item(sel_row, 0)
            if item:
                sel_tid = item.text()

        self.track_table.setRowCount(len(tracks))
        for i, t in enumerate(tracks):
            vals = [t["tid"], f"{t['range']:.2f}m",
                    f"{t['vel']:+.2f}", f"{t['az']:+.1f}°", f"{t['snr']:.1f}dB"]
            colors = [CYAN, WHITE, AMBER if abs(t['vel']) > 1 else WHITE, WHITE, WHITE]
            for j, (v, c) in enumerate(zip(vals, colors)):
                item = QTableWidgetItem(v)
                item.setForeground(QColor(c))
                item.setTextAlignment(Qt.AlignCenter)
                self.track_table.setItem(i, j, item)
            if t["tid"] == sel_tid:
                self.track_table.selectRow(i)

        self._tracks = tracks

    def _on_track_selected(self):
        row = self.track_table.currentRow()
        if row < 0 or not hasattr(self, '_tracks') or row >= len(self._tracks):
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
        """Select closest target automatically."""
        if not hasattr(self, '_tracks') or not self._tracks:
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

    def update_telemetry(self, batt, alt, yaw):
        self._telem_labels["battery"].setText(f"{batt}%")
        self._telem_labels["alt"].setText(f"{alt:.2f} m")
        self._telem_labels["yaw"].setText(f"{yaw:+.1f}°")

    def _on_goto(self):
        if self.selected_track:
            self.goto_requested.emit(self.selected_track)


# ─────────────────────────────────────────────
# SYSTEM LOG WIDGET
# ─────────────────────────────────────────────
class SystemLog(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumHeight(180)

    def log(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:12]
        colors = {"INFO": WHITE, "OK": GREEN, "WARN": AMBER, "ERR": RED}
        c = colors.get(level, WHITE)
        ts_html  = f'<span style="color:{GREEN_DIM}">{ts}</span>'
        msg_html = f'<span style="color:{c}">{msg}</span>'
        self.append(f'{ts_html} &nbsp; {msg_html}')
        self.moveCursor(QTextCursor.End)


# ─────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────
class RadarDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IWR6843ISK — Radar Control Dashboard")
        self.resize(1600, 900)
        self.setStyleSheet(STYLE)

        pg.setConfigOptions(antialias=True, background=BG, foreground=GREEN)

        self.sim       = RadarDataSimulator()
        self.cmap      = make_radar_colormap()
        self._cur_wf   = WAVEFORMS[list(WAVEFORMS.keys())[0]]
        self._frame_no = 0

        self._build_ui()
        self._connect_signals()

        # Update timer — 20 Hz
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(50)

        # Clock timer
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        self.log.log("Dashboard initialised — IWR6843ISK", "OK")

    # ─── BUILD UI ─────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        root.addWidget(self._make_header())

        # Main content
        body = QHBoxLayout()
        body.setContentsMargins(4, 4, 4, 4)
        body.setSpacing(4)

        # Left panel
        self.cfg_panel = RadarConfigPanel()
        self.cfg_panel.setFixedWidth(240)
        body.addWidget(self.cfg_panel)

        # Centre plots
        body.addLayout(self._make_plots(), stretch=1)

        # Right panel
        self.track_panel = TrackDronePanel()
        self.track_panel.setFixedWidth(260)
        body.addWidget(self.track_panel)

        root.addLayout(body, stretch=1)

    def _make_header(self):
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
            lbl.setStyleSheet(f"color:{dot_color}; font-size:10px; letter-spacing:2px; "
                              f"background:transparent; margin-right:16px;")
            hl.addWidget(dot)
            hl.addWidget(lbl)

        self.clock_lbl = QLabel("00:00:00")
        self.clock_lbl.setStyleSheet(
            f"color:{AMBER}; font-size:14px; letter-spacing:2px; background:transparent;"
        )
        hl.addWidget(self.clock_lbl)
        return bar

    def _make_plots(self):
        vl = QVBoxLayout()
        vl.setSpacing(4)

        # Top row: Range Profile | Range-Doppler
        top = QHBoxLayout()
        top.setSpacing(4)
        top.addWidget(self._make_range_profile_panel(), stretch=1)
        top.addWidget(self._make_doppler_panel(), stretch=1)
        vl.addLayout(top, stretch=1)

        # Bottom row: Range-Azimuth | Point Cloud | Log
        bot = QHBoxLayout()
        bot.setSpacing(4)
        bot.addWidget(self._make_azimuth_panel(), stretch=1)
        bot.addWidget(self._make_point_cloud_panel(), stretch=1)
        bot.addWidget(self._make_log_panel(), stretch=1)
        vl.addLayout(bot, stretch=1)

        return vl

    # ─ Range Profile
    def _make_range_profile_panel(self):
        grp = QGroupBox("Range Profile  —  FFT Magnitude")
        vl  = QVBoxLayout(grp)
        self.range_plot = pg.PlotWidget()
        self.range_plot.setLabel('bottom', 'Range (m)', color=GREEN_DIM, size='9pt')
        self.range_plot.setLabel('left',   'Magnitude', color=GREEN_DIM, size='9pt')
        self.range_plot.showGrid(x=True, y=True, alpha=0.15)
        self.range_plot.setYRange(0, 1.1)
        self.range_curve = self.range_plot.plot(pen=pg.mkPen(color=GREEN, width=1.5))
        # CFAR threshold line
        self.cfar_line = pg.InfiniteLine(
            pos=0.25, angle=0,
            pen=pg.mkPen(color=AMBER, width=1, style=Qt.DashLine), label='CFAR',
            labelOpts={'color': AMBER, 'position': 0.95}
        )
        self.range_plot.addItem(self.cfar_line)
        # Target markers
        self.range_markers = pg.ScatterPlotItem(
            size=10, pen=pg.mkPen(CYAN), brush=pg.mkBrush(CYAN + "88")
        )
        self.range_plot.addItem(self.range_markers)
        vl.addWidget(self.range_plot)
        return grp

    # ─ Range-Doppler
    def _make_doppler_panel(self):
        grp = QGroupBox("Range–Doppler Map  —  2D FFT")
        vl  = QVBoxLayout(grp)
        self.doppler_img = pg.ImageView(view=pg.PlotItem())
        self.doppler_img.ui.histogram.hide()
        self.doppler_img.ui.roiBtn.hide()
        self.doppler_img.ui.menuBtn.hide()
        pli = self.doppler_img.getView()
        pli.setLabel('bottom', 'Range (m)', color=GREEN_DIM, size='9pt')
        pli.setLabel('left',   'Velocity (m/s)', color=GREEN_DIM, size='9pt')
        self.doppler_img.setColorMap(self.cmap)
        vl.addWidget(self.doppler_img)
        return grp

    # ─ Range-Azimuth
    def _make_azimuth_panel(self):
        grp = QGroupBox("Range–Azimuth Map  —  Beamforming")
        vl  = QVBoxLayout(grp)
        self.azimuth_img = pg.ImageView(view=pg.PlotItem())
        self.azimuth_img.ui.histogram.hide()
        self.azimuth_img.ui.roiBtn.hide()
        self.azimuth_img.ui.menuBtn.hide()
        pli = self.azimuth_img.getView()
        pli.setLabel('bottom', 'Range (m)',   color=GREEN_DIM, size='9pt')
        pli.setLabel('left',   'Azimuth (°)', color=GREEN_DIM, size='9pt')
        self.azimuth_img.setColorMap(self.cmap)
        vl.addWidget(self.azimuth_img)
        return grp

    # ─ Point Cloud
    def _make_point_cloud_panel(self):
        grp = QGroupBox("Plot List  —  Point Cloud")
        vl  = QVBoxLayout(grp)
        self.cloud_plot = pg.PlotWidget()
        self.cloud_plot.setLabel('bottom', 'Range (m)',    color=GREEN_DIM, size='9pt')
        self.cloud_plot.setLabel('left',   'Velocity (m/s)', color=GREEN_DIM, size='9pt')
        self.cloud_plot.showGrid(x=True, y=True, alpha=0.15)
        self.cloud_scatter = pg.ScatterPlotItem(
            size=8, pen=pg.mkPen(None), brush=pg.mkBrush(GREEN + "cc")
        )
        self.cloud_plot.addItem(self.cloud_scatter)
        # Zero-velocity line
        self.cloud_plot.addItem(pg.InfiniteLine(
            pos=0, angle=0,
            pen=pg.mkPen(color=CYAN, width=1, style=Qt.DashLine)
        ))
        vl.addWidget(self.cloud_plot)
        return grp

    # ─ Log panel
    def _make_log_panel(self):
        grp = QGroupBox("System Log")
        vl  = QVBoxLayout(grp)
        self.log = SystemLog()
        vl.addWidget(self.log)
        return grp

    # ─── SIGNALS ──────────────────────────────
    def _connect_signals(self):
        self.cfg_panel.radar_connect_requested.connect(self._on_radar_connect)
        self.cfg_panel.radar_disconnect_requested.connect(self._on_radar_disconnect)
        self.cfg_panel.waveform_changed.connect(self._on_wf_changed)

        self.track_panel.drone_connect_requested.connect(self._on_drone_connect)
        self.track_panel.drone_disconnect_requested.connect(self._on_drone_disconnect)
        self.track_panel.goto_requested.connect(self._on_goto)
        self.track_panel.estop_requested.connect(self._on_estop)
        self.track_panel.target_selected.connect(self._on_target_selected)

    # ─── FRAME UPDATE ─────────────────────────
    def _update_frame(self):
        wf = self._cur_wf
        max_r = float(wf["max_range"].replace(" m", ""))
        max_v = float(wf["max_velocity"].replace("±", "").replace(" m/s", ""))

        # Range profile
        sig, r_axis = self.sim.generate_range_profile(max_r)
        self.range_curve.setData(r_axis, sig)
        # Markers at peaks
        plots = self.sim.generate_plot_list(max_r, max_v)
        mx = [p["range"] for p in plots]
        my = [min(sig[int(p["range"] / max_r * len(sig)) - 1], 1.0) for p in plots]
        self.range_markers.setData(mx, my)

        # Doppler
        dmap = self.sim.generate_range_doppler(max_r, max_v)
        self.doppler_img.setImage(
            dmap.T, autoLevels=False, levels=(0, 1),
            xvals=np.linspace(0, max_r, dmap.shape[1]),
        )

        # Azimuth
        amap = self.sim.generate_range_azimuth(max_r)
        self.azimuth_img.setImage(
            amap.T, autoLevels=False, levels=(0, 1),
            xvals=np.linspace(0, max_r, amap.shape[1]),
        )

        # Point cloud
        self.cloud_scatter.setData(
            [p["range"] for p in plots],
            [p["vel"]   for p in plots]
        )

        # Tracks
        tracks = self.sim.generate_track_list(max_r)
        self.track_panel.update_tracks(tracks)

        # Simulated telemetry
        if self.track_panel.drone_connected:
            self.track_panel.update_telemetry(
                batt=max(0, 84 - self._frame_no * 0.001),
                alt=1.2 + 0.1 * np.sin(self._frame_no * 0.05),
                yaw=7.0 + 0.5 * np.sin(self._frame_no * 0.03),
            )

        self._frame_no += 1

    def _update_clock(self):
        self.clock_lbl.setText(datetime.now().strftime("%H:%M:%S"))

    # ─── HANDLERS ─────────────────────────────
    def _on_radar_connect(self, cfg, dat, cfg_file):
        self.log.log(f"Radar connecting → CFG:{cfg}  DAT:{dat}", "INFO")
        self.log.log(f"Loading config: {cfg_file}", "INFO")
        # TODO: open serial ports here
        self.log.log("Radar connected — streaming frames", "OK")

    def _on_radar_disconnect(self):
        self.log.log("Radar disconnected", "WARN")
        # TODO: close serial ports

    def _on_wf_changed(self, wf: dict):
        self._cur_wf = wf
        self.log.log(f"Waveform changed → {wf['cfg_file']}", "INFO")
        # Update plot axis ranges
        max_r = float(wf["max_range"].replace(" m", ""))
        max_v = float(wf["max_velocity"].replace("±", "").replace(" m/s", ""))
        self.range_plot.setXRange(0, max_r)
        self.cloud_plot.setXRange(0, max_r)
        self.cloud_plot.setYRange(-max_v, max_v)

    def _on_drone_connect(self, ip: str):
        self.log.log(f"Drone connecting → {ip}", "INFO")
        # TODO: djitellopy / MAVLink connect here
        self.log.log(f"Drone linked: {ip}", "OK")

    def _on_drone_disconnect(self):
        self.log.log("Drone disconnected", "WARN")

    def _on_target_selected(self, t: dict):
        self.log.log(
            f"Target selected: {t['tid']}  range={t['range']:.2f}m  "
            f"vel={t['vel']:+.2f}m/s  az={t['az']:+.1f}°",
            "OK"
        )

    def _on_goto(self, t: dict):
        self.log.log(
            f"Go-To command → {t['tid']}  [{t['range']:.2f}m, {t['az']:+.1f}°]", "WARN"
        )
        # TODO: send MAVLink / Tello SDK command

    def _on_estop(self):
        self.log.log("⚠ EMERGENCY STOP TRIGGERED", "ERR")
        # TODO: send emergency land/stop command immediately


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette base
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(6, 10, 6))
    palette.setColor(QPalette.WindowText,      QColor(0, 255, 65))
    palette.setColor(QPalette.Base,            QColor(11, 17, 11))
    palette.setColor(QPalette.AlternateBase,   QColor(15, 24, 15))
    palette.setColor(QPalette.Text,            QColor(200, 255, 200))
    palette.setColor(QPalette.Button,          QColor(11, 17, 11))
    palette.setColor(QPalette.ButtonText,      QColor(0, 255, 65))
    palette.setColor(QPalette.Highlight,       QColor(0, 255, 65, 60))
    palette.setColor(QPalette.HighlightedText, QColor(0, 255, 65))
    app.setPalette(palette)

    win = RadarDashboard()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
