"""
Tracking layer.

Phase 1 — FirstPlotTracker: returns the first plot from the current frame
           as a single target with score = 1.0.

Phase 3 (future): Hungarian data association + Kalman filter state estimation
                  + classification features + composite scoring.
"""
from __future__ import annotations
from typing import List

from radar.data_types import PlotPoint, Target


class Tracker:
    def update(self, plots: List[PlotPoint]) -> List[Target]:
        raise NotImplementedError


class FirstPlotTracker(Tracker):
    """Phase 1: always returns the first available plot as the sole target."""

    def update(self, plots: List[PlotPoint]) -> List[Target]:
        if not plots:
            return []
        p = plots[0]
        return [Target(target_id=0, x=p.x, y=p.y, z=p.z,
                       velocity=p.velocity, score=1.0)]
