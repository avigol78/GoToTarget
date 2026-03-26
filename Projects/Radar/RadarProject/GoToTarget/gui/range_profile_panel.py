"""
Range profile line-plot canvas.

Draws two lines:
  green — range profile (signal magnitude)
  red   — noise profile (noise floor)

Data is in Q9 float format (already divided by 512 in the parser).
"""
from __future__ import annotations
from typing import Optional

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D


class RangeProfileCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None) -> None:
        fig = Figure(facecolor='#1e1e1e', tight_layout=True)
        super().__init__(fig)
        self.setParent(parent)

        self.ax = fig.add_subplot(111)
        self.ax.set_facecolor('#1e1e1e')
        self.ax.tick_params(colors='white', labelsize=7)
        self.ax.set_xlabel('Range bin', color='white', fontsize=8)
        self.ax.set_ylabel('Magnitude (Q9)', color='white', fontsize=8)
        self.ax.set_title('Range Profile', color='white', fontsize=9)
        self.ax.spines[:].set_color('#444444')

        self._line_range: Optional[Line2D] = None
        self._line_noise: Optional[Line2D] = None

    def update_data(self,
                    range_profile: Optional[np.ndarray],
                    noise_profile: Optional[np.ndarray] = None) -> None:
        if range_profile is None or range_profile.size == 0:
            return

        x = np.arange(len(range_profile))
        y_range = np.abs(range_profile)

        if self._line_range is None:
            self._line_range, = self.ax.plot(x, y_range, color='lime',
                                              linewidth=0.8, label='Range')
            self._line_noise, = self.ax.plot([], [], color='red',
                                              linewidth=0.8, label='Noise')
            self.ax.legend(loc='upper right', fontsize=7,
                           labelcolor='white',
                           facecolor='#2b2b2b', edgecolor='#444444')
        else:
            self._line_range.set_xdata(x)
            self._line_range.set_ydata(y_range)

        if noise_profile is not None and noise_profile.size > 0:
            xn = np.arange(len(noise_profile))
            self._line_noise.set_xdata(xn)
            self._line_noise.set_ydata(np.abs(noise_profile))

        self.ax.relim()
        self.ax.autoscale_view()
        self.draw_idle()
