from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


@dataclass
class DetectedPoint:
    x: float          # meters (forward)
    y: float          # meters (lateral)
    z: float          # meters (up)
    velocity: float   # m/s (radial doppler)
    snr: float = 0.0  # dB (from TLV7)
    noise: float = 0.0


@dataclass
class RadarFrame:
    frame_number: int
    num_detected_obj: int
    detected_points: List[DetectedPoint] = field(default_factory=list)
    range_profile: Optional[np.ndarray] = None        # shape (range_bins,), float Q9
    noise_profile: Optional[np.ndarray] = None        # shape (range_bins,), float Q9
    range_doppler: Optional[np.ndarray] = None        # 1D uint16 array; reshape at display time
    azimuth_heatmap: Optional[np.ndarray] = None      # shape (range_bins, virtual_ants), complex
    elevation_heatmap: Optional[np.ndarray] = None    # shape (range_bins, az_bins, el_bins), complex
    statistics: Optional[dict] = None                 # TLV6 performance counters
    temperature_stats: Optional[dict] = None          # TLV9 sensor temperatures


@dataclass
class PlotPoint:
    x: float
    y: float
    z: float
    velocity: float


@dataclass
class Target:
    target_id: int
    x: float
    y: float
    z: float
    velocity: float
    azimuth: float
    snr: float
    range: float
    is_detected: bool = False
    score: int = 1.0  # composite score; drives drone targeting


@dataclass
class Plot:
    snr: float
    range: float
    azimuth: float
    velocity: float


@dataclass
class RadarInput:
    range_doppler_map: np.ndarray | None = None
    range_axis_rd: np.ndarray | None = None
    velocity_axis: np.ndarray | None = None
    range_azimuth_map: np.ndarray | None = None
    range_axis_ra: np.ndarray | None = None
    azimuth_axis: np.ndarray | None = None
    range_detected_targets: np.ndarray | None = None