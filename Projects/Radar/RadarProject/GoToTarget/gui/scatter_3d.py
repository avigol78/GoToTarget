"""
3D scatter plot widget.

Red scatter  = current-frame plot detections
Blue scatter = current tracked targets

Axes: X = forward (range), Y = lateral, Z = up
"""
from __future__ import annotations
from typing import List

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers 3d projection

from radar.data_types import PlotPoint, Target

# Axis limits (metres) — adjust to match your waveform range
AXIS_RANGE = 10.0


class Scatter3DCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None) -> None:
        fig = Figure(facecolor='#1e1e1e')
        super().__init__(fig)
        self.setParent(parent)

        self.ax: Axes3D = fig.add_subplot(111, projection='3d')
        self._style_axes()

        self._plot_scatter = None
        self._track_scatter = None

    def _style_axes(self) -> None:
        ax = self.ax
        ax.set_facecolor('#1e1e1e')
        ax.tick_params(colors='white', labelsize=7)
        for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
            pane.fill = False
            pane.set_edgecolor('#444444')
        ax.set_xlabel('X (m)', color='white', fontsize=8)
        ax.set_ylabel('Y (m)', color='white', fontsize=8)
        ax.set_zlabel('Z (m)', color='white', fontsize=8)
        ax.set_xlim(-AXIS_RANGE, AXIS_RANGE)
        ax.set_ylim(-AXIS_RANGE, AXIS_RANGE)
        ax.set_zlim(-1, AXIS_RANGE)
        ax.set_title('3D Point Cloud', color='white', fontsize=9)

    def update_data(self, plots: List[PlotPoint], targets: List[Target]) -> None:
        ax = self.ax

        # Remove previous artists
        if self._plot_scatter:
            self._plot_scatter.remove()
            self._plot_scatter = None
        if self._track_scatter:
            self._track_scatter.remove()
            self._track_scatter = None

        # Plot detections (red)
        if plots:
            xs = [p.x for p in plots]
            ys = [p.y for p in plots]
            zs = [p.z for p in plots]
            self._plot_scatter = ax.scatter(xs, ys, zs, c='red', s=20,
                                            label='Plots', depthshade=False)

        # Tracked targets (blue)
        if targets:
            xs = [t.x for t in targets]
            ys = [t.y for t in targets]
            zs = [t.z for t in targets]
            self._track_scatter = ax.scatter(xs, ys, zs, c='cyan', s=60,
                                             marker='^', label='Tracks',
                                             depthshade=False)

        self.draw_idle()
