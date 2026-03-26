"""
2D heatmap canvas for range-doppler and range-azimuth maps.
"""
from __future__ import annotations
from typing import Optional

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.image import AxesImage


class HeatmapCanvas(FigureCanvasQTAgg):
    def __init__(self, title: str, xlabel: str, ylabel: str,
                 parent=None) -> None:
        fig = Figure(facecolor='#1e1e1e', tight_layout=True)
        super().__init__(fig)
        self.setParent(parent)

        self.ax = fig.add_subplot(111)
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='white', labelsize=7)
        self.ax.set_xlabel(xlabel, color='white', fontsize=8)
        self.ax.set_ylabel(ylabel, color='white', fontsize=8)
        self.ax.set_title(title, color='white', fontsize=9)
        self.ax.spines[:].set_color('#444444')

        self._img: Optional[AxesImage] = None
        self._cbar = None

    def update_data(self, data: Optional[np.ndarray]) -> None:
        if data is None or data.size == 0:
            return

        # Accept both 1D (will be shown as column) and 2D arrays
        arr = np.abs(data) if np.iscomplexobj(data) else data
        if arr.ndim == 1:
            arr = arr[:, np.newaxis]

        if self._img is None:
            self._img = self.ax.imshow(
                arr, aspect='auto', origin='lower',
                cmap='jet', interpolation='nearest'
            )
            self._cbar = self.figure.colorbar(self._img, ax=self.ax,
                                               fraction=0.046, pad=0.04)
            self._cbar.ax.tick_params(colors='white', labelsize=6)
        else:
            self._img.set_data(arr)
            self._img.set_clim(vmin=arr.min(), vmax=arr.max())

        self.draw_idle()
