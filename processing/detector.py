"""
Plot detection layer.

Phase 1 — TLVDetector: converts the board's CFAR-detected points (TLV Type 1)
           directly into PlotPoints.
Phase 2 — CNNDetector: will derive plots from the range-doppler-azimuth cube.
"""
from __future__ import annotations
from typing import List

from radar.data_types import RadarFrame, PlotPoint


class PlotDetector:
    def detect(self, frame: RadarFrame) -> List[PlotPoint]:
        raise NotImplementedError


class TLVDetector(PlotDetector):
    """Phase 1 (default): pass TLV1 detected points through as plot data."""

    def detect(self, frame: RadarFrame) -> List[PlotPoint]:
        return [
            PlotPoint(x=p.x, y=p.y, z=p.z, velocity=p.velocity)
            for p in frame.detected_points
        ]


class CNNDetector(PlotDetector):
    """Phase 2 (future): derive plots from the range-doppler-azimuth cube."""

    def detect(self, frame: RadarFrame) -> List[PlotPoint]:
        raise NotImplementedError("CNNDetector is not implemented yet")
