"""
Plot detection layer.

Phase 1 — TLVDetector: converts the board's CFAR-detected points (TLV Type 1)
           directly into PlotPoints.
Phase 2 — CNNDetector: will derive plots from the range-doppler-azimuth cube.
"""
from __future__ import annotations
from typing import List
import numpy as np

from radar.data_types import RadarFrame, PlotPoint, RadarInput, Plot, Target

def local_mean(mat, i, j, cfar_window=6, guard=1):
    i0, i1 = max(i - cfar_window, 0), min(i + cfar_window + 1, mat.shape[0])
    j0, j1 = max(j - cfar_window, 0), min(j + cfar_window + 1, mat.shape[1])
    window = mat[i0:i1, j0:j1].copy()
    ci, cj = i - i0, j - j0
    window[max(ci - guard, 0):(ci + guard + 1),
           max(cj - guard, 0):(cj + guard + 1)] = np.nan

    return np.nanmean(window)

def calculate_snr(map_data, range_index, y_index):
    cut = map_data[range_index, y_index]
    cfar_window = local_mean(map_data, range_index, y_index, cfar_window=6, guard=1)
    return 20 * np.log10(cut/cfar_window + 1e-6)

def find_target(map_data, x_axis, y_axis, target_range):
    range_index = np.argmin(np.abs(x_axis - target_range))
    cfar_parameter_2d_db = 0.5  # threshold in dB; adjust based on noise floor and desired sensitivity
    snr_vector = []
    index_vector = []
    for y_index in range(len(y_axis)):
        target_snr = calculate_snr(map_data, range_index, y_index)
        if target_snr > cfar_parameter_2d_db:  # threshold in dB
            snr_vector.append(target_snr)
            index_vector.append(y_index)
    if snr_vector:
        best_index = index_vector[np.argmax(snr_vector)]
        return True, y_axis[best_index], np.max(snr_vector)
    return False, None, None


class PlotDetector:
    def detect(self, frame: RadarInput) -> List[Plot]:
        """Detect plots from the given radar frame."""
        raise NotImplementedError("PlotDetector is an abstract base class")


class TLVDetector(PlotDetector):
    """Phase 1 (default): pass TLV1 detected points through as plot data."""
    def detect(self, frame: RadarInput) -> List[Plot]:
        plot_list: List[Plot] = []
        for target_range in frame.range_detected_targets:
            is_target_rd, target_velocity, target_snr_rd = find_target(frame.range_doppler_map, frame.range_axis_rd, frame.velocity_axis, target_range)
            is_target_ra, target_azimuth, target_snr_ra = find_target(frame.range_azimuth_map, frame.range_axis_ra, frame.azimuth_axis, target_range)
            if is_target_rd and is_target_ra:
                plot_list.append(Plot(range=target_range, velocity=target_velocity, azimuth=target_azimuth, snr=target_snr_rd))
        return plot_list


class CNNDetector(PlotDetector):
    """Phase 2 (future): derive plots from the range-doppler-azimuth cube."""

    def detect(self, frame: RadarFrame) -> List[PlotPoint]:
        raise NotImplementedError("CNNDetector is not implemented yet")
