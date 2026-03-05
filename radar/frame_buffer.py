"""
Rolling 5-frame history buffer.

Stores per-frame: detected point list, range profile vector,
range-doppler matrix, and range-azimuth heatmap matrix.
"""
from __future__ import annotations
from collections import deque
from typing import List, Optional
import numpy as np

from .data_types import DetectedPoint, RadarFrame

BUFFER_SIZE = 5


class FrameBuffer:
    def __init__(self, maxlen: int = BUFFER_SIZE) -> None:
        self._plots:      deque[List[DetectedPoint]] = deque(maxlen=maxlen)
        self._range_prof: deque[np.ndarray]          = deque(maxlen=maxlen)
        self._rd_map:     deque[np.ndarray]          = deque(maxlen=maxlen)
        self._ra_map:     deque[np.ndarray]          = deque(maxlen=maxlen)

    def push(self, frame: RadarFrame) -> None:
        """Append a new frame; oldest entry is dropped automatically when full."""
        self._plots.append(frame.detected_points)

        if frame.range_profile is not None:
            self._range_prof.append(frame.range_profile)

        if frame.range_doppler is not None:
            self._rd_map.append(frame.range_doppler)

        if frame.azimuth_heatmap is not None:
            self._ra_map.append(frame.azimuth_heatmap)

    def clear(self) -> None:
        self._plots.clear()
        self._range_prof.clear()
        self._rd_map.clear()
        self._ra_map.clear()

    # ------------------------------------------------------------------
    # Latest-frame accessors
    # ------------------------------------------------------------------

    @property
    def latest_plots(self) -> List[DetectedPoint]:
        return list(self._plots[-1]) if self._plots else []

    @property
    def latest_range_profile(self) -> Optional[np.ndarray]:
        return self._range_prof[-1] if self._range_prof else None

    @property
    def latest_rd_map(self) -> Optional[np.ndarray]:
        return self._rd_map[-1] if self._rd_map else None

    @property
    def latest_ra_map(self) -> Optional[np.ndarray]:
        return self._ra_map[-1] if self._ra_map else None

    # ------------------------------------------------------------------
    # Full history accessors
    # ------------------------------------------------------------------

    def all_plots(self) -> List[List[DetectedPoint]]:
        return list(self._plots)

    def all_range_profiles(self) -> List[np.ndarray]:
        return list(self._range_prof)

    def all_rd_maps(self) -> List[np.ndarray]:
        return list(self._rd_map)

    def all_ra_maps(self) -> List[np.ndarray]:
        return list(self._ra_map)

    def __len__(self) -> int:
        return len(self._plots)
