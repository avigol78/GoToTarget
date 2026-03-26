"""
Tracking layer.

Phase 1 — FirstPlotTracker: returns the first plot from the current frame
           as a single target with score = 1.0.

Phase 3 (future): Hungarian data association + Kalman filter state estimation
                  + classification features + composite scoring.
"""
from __future__ import annotations
from typing import List
import numpy as np

from radar.data_types import PlotPoint, Target, Plot

def update_target_state(target: Target, plot: Plot) -> None:
    """Update the target's state based on the matched plot. Implement as needed."""
    target.x = plot.range * np.cos(np.deg2rad(plot.azimuth))
    target.y = plot.range * np.sin(np.deg2rad(plot.azimuth))
    target.z = 0  # Assuming flat ground; adjust if elevation data is available
    target.velocity = plot.velocity
    target.azimuth = plot.azimuth
    target.range = plot.range
    target.snr = plot.snr

def _is_match(target: Target, plot: Plot, azimuth_res, velocity_res, range_res) -> bool:
    """Determine if the given plot matches the target based on proximity and velocity."""
    range_threshold = 3 * range_res  #  3 range bins; 
    velocity_threshold = 3 * velocity_res  # 3 velocity bins;   
    azimuth_threshold = 3 * azimuth_res  # 3 azimuth bins;

    range_diff = abs(target.range - plot.range)
    velocity_diff = abs(target.velocity - plot.velocity)
    azimuth_diff = abs(target.azimuth - plot.azimuth)

    return (range_diff < range_threshold and
            velocity_diff < velocity_threshold and
            azimuth_diff < azimuth_threshold)

class Tracker:
    """Update the tracker with the latest detected plots and return the current targets."""
    def update(self, plots: List[Plot], last_targets: List[Target], azimuth_res, velocity_res, range_res) -> List[Target]:
        for target in last_targets:
            target.is_detected = False  # reset detection status; will be updated if matched to a plot
            for plot in plots:
                if _is_match(target, plot, azimuth_res, velocity_res, range_res):
                    target.is_detected = True
                    target.score = min(target.score + 1, 10)  # simple scoring: +1 for each detection; adjust as needed
                    update_target_state(last_targets, plot)  # update target state based on matched plot; implement as needed
                    break
            if not target.is_detected:
                target.score = max(target.score - 1, 0)  # decay score if not detected; adjust as needed
        return last_targets


class FirstPlotTracker(Tracker):
    """Update the tracker with the latest detected plots and return the current targets."""
    def update(self, plots: List[Plot], last_targets: List[Target], azimuth_res, velocity_res, range_res) -> List[Target]:
        for target in last_targets:
            target.is_detected = False  # reset detection status; will be updated if matched to a plot
        for plot in plots:
            isAssociated = False
            for target in last_targets:
                if _is_match(target, plot, azimuth_res, velocity_res, range_res):
                    if not target.is_detected:
                        target.is_detected = True
                        isAssociated = True
                        target.score = min(target.score + 1, 10)  # simple scoring: +1 for each detection; adjust as needed
                        update_target_state(target, plot)  # update target state based on matched plot; implement as needed
                    elif (plot.snr > target.snr):  # If the plot has a higher SNR than the current target, update the target with the new plot's information
                        update_target_state(target, plot)  # update target state based on matched plot; implement as needed
                        break
            if not isAssociated:
                new_target = Target(
                    target_id = len(last_targets) + 1,  # simple ID assignment; adjust as needed 
                    x=plot.range * np.cos(np.deg2rad(plot.azimuth)),
                    y=plot.range * np.sin(np.deg2rad(plot.azimuth)),
                    z=0,  # Assuming flat ground; adjust if elevation data is available
                    velocity=plot.velocity,
                    azimuth=plot.azimuth,
                    range=plot.range,
                    snr=plot.snr,
                    score=1.0,
                    is_detected=True
                )
                last_targets.append(new_target)
        for target in last_targets:
            if not target.is_detected:
                target.score = max(target.score - 1, 0)  # decay score if not detected; adjust as needed
        return last_targets

