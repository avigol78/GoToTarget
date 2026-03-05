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
    range_profile: Optional[np.ndarray] = None        # shape (range_bins,), float
    range_doppler: Optional[np.ndarray] = None        # shape (range_bins, doppler_bins), uint16
    azimuth_heatmap: Optional[np.ndarray] = None      # shape (range_bins, virtual_ants), complex
    elevation_heatmap: Optional[np.ndarray] = None    # shape (range_bins, az_bins, el_bins), complex


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
    score: float = 1.0  # composite score; drives drone targeting
