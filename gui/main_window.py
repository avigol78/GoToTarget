"""
Main application window.

Layout (dockable panels):
  Toolbar  : [Config ▼] [Connect] [Disconnect] [Detector ▼] [Drone Connect] [Send Drone]  | FPS
  Central  : 3D Scatter plot
  Right    : Range-Doppler heatmap (top) + Range-Azimuth heatmap (bottom)
  Bottom   : Target list table
"""
from __future__ import annotations
import os
import time
from typing import List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QMainWindow, QToolBar, QComboBox, QPushButton, QLabel,
    QDockWidget, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QStatusBar, QMessageBox, QSizePolicy
)

from radar.connection import RadarConnection, ConfigError
from radar.reader import RadarReader
from radar.frame_buffer import FrameBuffer
from radar.data_types import RadarFrame, PlotPoint, Target
from processing.detector import TLVDetector, PlotDetector
from processing.tracker import FirstPlotTracker, Tracker
from drone.px4_commander import PX4Commander
from gui.scatter_3d import Scatter3DCanvas
from gui.heatmap_panel import HeatmapCanvas

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'configs')

WAVEFORMS = {
    'WF1 — Short dist, slow': 'WF1.cfg',
    'WF2 — Long dist, slow':  'WF2.cfg',
    'WF3 — Short dist, fast': 'WF3.cfg',
    'WF4 — Long dist, fast':  'WF4.cfg',
}

DETECTORS = {
    'TLV Detector (Phase 1)': TLVDetector,
}

# Nominal radar dimensions (updated dynamically from first real frame)
DEFAULT_RANGE_BINS   = 256
DEFAULT_DOPPLER_BINS = 16


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('IWR6843ISK Radar Dashboard')
        self.resize(1400, 860)

        # Core objects
        self._conn    = RadarConnection()
        self._reader: Optional[RadarReader] = None
        self._buffer  = FrameBuffer()
        self._detector: PlotDetector = TLVDetector()
        self._tracker:  Tracker      = FirstPlotTracker()
        self._commander = PX4Commander()

        # FPS tracking
        self._frame_times: List[float] = []

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._build_toolbar()
        self._build_central()
        self._build_heatmap_docks()
        self._build_target_dock()
        self._build_statusbar()

    def _build_toolbar(self) -> None:
        tb = QToolBar('Controls')
        tb.setMovable(False)
        self.addToolBar(tb)

        # Config file selector
        tb.addWidget(QLabel(' Config: '))
        self._cfg_combo = QComboBox()
        for label in WAVEFORMS:
            self._cfg_combo.addItem(label)
        self._cfg_combo.setFixedWidth(220)
        tb.addWidget(self._cfg_combo)

        tb.addSeparator()

        # Connect / Disconnect
        self._btn_connect = QPushButton('Connect')
        self._btn_connect.setStyleSheet('background:#2a6b2a; color:white;')
        self._btn_connect.clicked.connect(self._on_connect)
        tb.addWidget(self._btn_connect)

        self._btn_disconnect = QPushButton('Disconnect')
        self._btn_disconnect.setStyleSheet('background:#6b2a2a; color:white;')
        self._btn_disconnect.setEnabled(False)
        self._btn_disconnect.clicked.connect(self._on_disconnect)
        tb.addWidget(self._btn_disconnect)

        tb.addSeparator()

        # Detector selector
        tb.addWidget(QLabel(' Detector: '))
        self._det_combo = QComboBox()
        for label in DETECTORS:
            self._det_combo.addItem(label)
        self._det_combo.setFixedWidth(200)
        self._det_combo.currentTextChanged.connect(self._on_detector_changed)
        tb.addWidget(self._det_combo)

        tb.addSeparator()

        # Drone controls
        self._btn_drone_connect = QPushButton('Drone Connect')
        self._btn_drone_connect.setStyleSheet('background:#2a4a6b; color:white;')
        self._btn_drone_connect.clicked.connect(self._on_drone_connect)
        tb.addWidget(self._btn_drone_connect)

        self._btn_send_drone = QPushButton('Send Drone')
        self._btn_send_drone.setStyleSheet('background:#6b4a2a; color:white;')
        self._btn_send_drone.clicked.connect(self._on_send_drone)
        tb.addWidget(self._btn_send_drone)

        # Spacer + FPS label
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        self._fps_label = QLabel('FPS: --')
        self._fps_label.setStyleSheet('color:#aaaaaa; margin-right:8px;')
        tb.addWidget(self._fps_label)

    def _build_central(self) -> None:
        self._scatter = Scatter3DCanvas(self)
        self.setCentralWidget(self._scatter)

    def _build_heatmap_docks(self) -> None:
        # Range-Doppler
        self._rd_canvas = HeatmapCanvas(
            title='Range-Doppler', xlabel='Doppler bin', ylabel='Range bin')
        dock_rd = QDockWidget('Range-Doppler', self)
        dock_rd.setWidget(self._rd_canvas)
        dock_rd.setFeatures(QDockWidget.AllDockWidgetFeatures)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_rd)

        # Range-Azimuth
        self._ra_canvas = HeatmapCanvas(
            title='Range-Azimuth', xlabel='Antenna index', ylabel='Range bin')
        dock_ra = QDockWidget('Range-Azimuth', self)
        dock_ra.setWidget(self._ra_canvas)
        dock_ra.setFeatures(QDockWidget.AllDockWidgetFeatures)
        self.addDockWidget(Qt.RightDockWidgetArea, dock_ra)

    def _build_target_dock(self) -> None:
        columns = ['ID', 'X (m)', 'Y (m)', 'Z (m)', 'Vel (m/s)', 'Score']
        self._target_table = QTableWidget(0, len(columns))
        self._target_table.setHorizontalHeaderLabels(columns)
        self._target_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._target_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._target_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._target_table.setStyleSheet('background:#1e1e1e; color:white;')
        self._target_table.horizontalHeader().setStyleSheet('color:white;')

        dock = QDockWidget('Target List', self)
        dock.setWidget(self._target_table)
        dock.setFeatures(QDockWidget.AllDockWidgetFeatures)
        dock.setMaximumHeight(200)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

    def _build_statusbar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status_label = QLabel('● Disconnected')
        self._status_label.setStyleSheet('color:#ff6666;')
        self._status.addWidget(self._status_label)

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------

    def _on_connect(self) -> None:
        cfg_label = self._cfg_combo.currentText()
        cfg_file  = WAVEFORMS[cfg_label]
        cfg_path  = os.path.normpath(os.path.join(CONFIGS_DIR, cfg_file))

        try:
            self._conn.connect('/dev/ttyUSB0', '/dev/ttyUSB1')
            self._conn.send_config(cfg_path)
        except (ConnectionError, ConfigError, FileNotFoundError) as e:
            QMessageBox.critical(self, 'Connection Error', str(e))
            self._conn.disconnect()
            return

        # Start background reader
        self._reader = RadarReader(self._conn.get_data_serial())
        self._reader.frame_received.connect(self._on_frame)
        self._reader.error_occurred.connect(self._on_reader_error)
        self._reader.start()

        self._buffer.clear()
        self._btn_connect.setEnabled(False)
        self._btn_disconnect.setEnabled(True)
        self._set_status('● Connected — ' + cfg_label, '#66ff66')

    def _on_disconnect(self) -> None:
        if self._reader:
            self._reader.stop()
            self._reader = None
        self._conn.disconnect()
        self._btn_connect.setEnabled(True)
        self._btn_disconnect.setEnabled(False)
        self._set_status('● Disconnected', '#ff6666')

    def _on_detector_changed(self, label: str) -> None:
        cls = DETECTORS.get(label)
        if cls:
            self._detector = cls()

    def _on_drone_connect(self) -> None:
        self._commander.start()
        self._commander.connect_async()
        self._btn_drone_connect.setEnabled(False)
        self._btn_drone_connect.setText('Drone Connecting…')
        # Poll until connected (simple timer approach)
        timer = QTimer(self)
        timer.timeout.connect(lambda: self._check_drone_connected(timer))
        timer.start(500)

    def _check_drone_connected(self, timer: QTimer) -> None:
        if self._commander.is_connected:
            timer.stop()
            self._btn_drone_connect.setText('Drone Connected')
            self._btn_drone_connect.setStyleSheet('background:#2a6b2a; color:white;')

    def _on_send_drone(self) -> None:
        # Use the last known target list (stored in _last_targets)
        targets = getattr(self, '_last_targets', [])
        if not targets:
            QMessageBox.information(self, 'No Target', 'No targets available yet.')
            return
        self._commander.send_highest_score(targets)

    def _on_reader_error(self, msg: str) -> None:
        self._set_status(f'● Error: {msg}', '#ffaa00')

    # ------------------------------------------------------------------
    # Frame processing (called from Qt main thread via signal)
    # ------------------------------------------------------------------

    def _on_frame(self, frame: RadarFrame) -> None:
        # 1. Buffer
        self._buffer.push(frame)

        # 2. Detect
        plots: List[PlotPoint] = self._detector.detect(frame)

        # 3. Track
        targets: List[Target] = self._tracker.update(plots)
        self._last_targets = targets

        # 4. Update range-doppler heatmap (reshape 1D → 2D if needed)
        rd = self._buffer.latest_rd_map
        if rd is not None and rd.ndim == 1:
            # Try to reshape into (range_bins, doppler_bins)
            total = rd.size
            for doppler_bins in (128, 64, 32, 16, 8):
                if total % doppler_bins == 0:
                    rd = rd.reshape(-1, doppler_bins)
                    break
        self._rd_canvas.update_data(rd)

        # 5. Update azimuth heatmap
        ra = self._buffer.latest_ra_map
        if ra is not None:
            ra_mag = abs(ra)
            if ra_mag.ndim == 1:
                ra_mag = ra_mag[:, np.newaxis]
            self._ra_canvas.update_data(ra_mag)

        # 6. Update 3D scatter
        self._scatter.update_data(plots, targets)

        # 7. Update target table
        self._update_target_table(targets)

        # 8. FPS
        now = time.monotonic()
        self._frame_times.append(now)
        self._frame_times = [t for t in self._frame_times if now - t < 2.0]
        fps = len(self._frame_times) / 2.0
        self._fps_label.setText(f'FPS: {fps:.1f}')

    def _update_target_table(self, targets: List[Target]) -> None:
        self._target_table.setRowCount(len(targets))
        for row, t in enumerate(targets):
            for col, val in enumerate([t.target_id, t.x, t.y, t.z, t.velocity, t.score]):
                item = QTableWidgetItem(f'{val:.2f}' if isinstance(val, float) else str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self._target_table.setItem(row, col, item)

    def _set_status(self, text: str, color: str) -> None:
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f'color:{color};')

    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._on_disconnect()
        self._commander.stop()
        super().closeEvent(event)


# numpy is used inside _on_frame — import at top of file
import numpy as np  # noqa: E402 (placed here to keep it visible near usage)
