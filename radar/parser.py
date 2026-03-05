"""
TLV binary frame parser for TI mmWave SDK (IWR6843ISK).

Frame layout:
  [8 bytes magic][4 bytes version][4 bytes totalPacketLen][4 bytes platform]
  [4 bytes frameNumber][4 bytes timeCpuCycles][4 bytes numDetectedObj]
  [4 bytes numTLVs][4 bytes subframeNumber]   → total header = 40 bytes

Then numTLVs blocks of:
  [4 bytes type][4 bytes length][<length> bytes payload]
"""
from __future__ import annotations
import struct
from typing import Optional, Tuple
import numpy as np

from .data_types import RadarFrame, DetectedPoint

MAGIC_WORD = b'\x02\x01\x04\x03\x06\x05\x08\x07'
HEADER_SIZE = 40
TLV_HEADER_SIZE = 8


class TLVParser:
    # TLV type constants
    TLV_DETECTED_POINTS = 1
    TLV_RANGE_PROFILE = 2
    TLV_AZIMUTH_HEATMAP = 4
    TLV_RANGE_DOPPLER = 5
    TLV_SIDE_INFO = 7
    TLV_ELEVATION_HEATMAP = 8

    def find_and_parse(self, buf: bytearray) -> Tuple[Optional[RadarFrame], int]:
        """
        Search buf for a valid frame.  Returns (frame, bytes_consumed) where
        bytes_consumed is how many bytes from the start of buf were used
        (including any leading garbage before the magic word).
        Returns (None, 0) if no complete frame is available yet.
        """
        idx = buf.find(MAGIC_WORD)
        if idx == -1:
            # No magic word found — discard all but last 7 bytes (could be partial magic)
            discard = max(0, len(buf) - 7)
            return None, discard

        if idx > 0:
            # Discard garbage before magic word
            return None, idx

        # Need at least a full header
        if len(buf) < HEADER_SIZE:
            return None, 0

        (version, total_len, platform, frame_num,
         cpu_cycles, num_objs, num_tlvs, subframe) = struct.unpack_from('<8I', buf, 8)

        if total_len > 65536 or total_len < HEADER_SIZE:
            # Corrupt header — skip past this magic word
            return None, len(MAGIC_WORD)

        if len(buf) < total_len:
            return None, 0  # wait for more data

        frame_bytes = bytes(buf[:total_len])
        frame = self._parse_frame(frame_bytes, frame_num, num_objs, num_tlvs)
        return frame, total_len

    def _parse_frame(self, data: bytes, frame_num: int,
                     num_objs: int, num_tlvs: int) -> RadarFrame:
        frame = RadarFrame(frame_number=frame_num, num_detected_obj=num_objs)
        offset = HEADER_SIZE
        side_info: list = []

        for _ in range(num_tlvs):
            if offset + TLV_HEADER_SIZE > len(data):
                break
            tlv_type, tlv_len = struct.unpack_from('<II', data, offset)
            offset += TLV_HEADER_SIZE
            payload = data[offset: offset + tlv_len]
            offset += tlv_len

            if tlv_type == self.TLV_DETECTED_POINTS:
                frame.detected_points = self._parse_detected_points(payload)

            elif tlv_type == self.TLV_RANGE_PROFILE:
                frame.range_profile = self._parse_range_profile(payload)

            elif tlv_type == self.TLV_AZIMUTH_HEATMAP:
                frame.azimuth_heatmap = self._parse_complex_heatmap(payload)

            elif tlv_type == self.TLV_RANGE_DOPPLER:
                frame.range_doppler = self._parse_range_doppler(payload)

            elif tlv_type == self.TLV_SIDE_INFO:
                side_info = self._parse_side_info(payload)

            elif tlv_type == self.TLV_ELEVATION_HEATMAP:
                frame.elevation_heatmap = self._parse_complex_heatmap(payload)

        # Merge side info (SNR, noise) into detected points
        for i, si in enumerate(side_info):
            if i < len(frame.detected_points):
                frame.detected_points[i].snr = si[0]
                frame.detected_points[i].noise = si[1]

        return frame

    # ------------------------------------------------------------------
    # TLV sub-parsers
    # ------------------------------------------------------------------

    def _parse_detected_points(self, payload: bytes) -> list[DetectedPoint]:
        point_size = 16  # 4 × float32
        points = []
        for i in range(0, len(payload) - point_size + 1, point_size):
            x, y, z, v = struct.unpack_from('<4f', payload, i)
            points.append(DetectedPoint(x=x, y=y, z=z, velocity=v))
        return points

    def _parse_range_profile(self, payload: bytes) -> np.ndarray:
        # uint16 Q9 format → divide by 512 to get linear magnitude
        count = len(payload) // 2
        raw = np.frombuffer(payload[:count * 2], dtype='<u2')
        return raw.astype(np.float32) / 512.0

    def _parse_range_doppler(self, payload: bytes) -> np.ndarray:
        # uint16 magnitude values; shape determined at display time
        count = len(payload) // 2
        raw = np.frombuffer(payload[:count * 2], dtype='<u2')
        # Keep as 1D here; MainWindow reshapes to (range_bins, doppler_bins)
        return raw.astype(np.float32)

    def _parse_complex_heatmap(self, payload: bytes) -> np.ndarray:
        # Interleaved int16 real/imag pairs
        count = len(payload) // 4  # 4 bytes per complex sample
        real = np.frombuffer(payload[:count * 4], dtype='<i2')[0::2].astype(np.float32)
        imag = np.frombuffer(payload[:count * 4], dtype='<i2')[1::2].astype(np.float32)
        return real + 1j * imag

    def _parse_side_info(self, payload: bytes) -> list[tuple[float, float]]:
        # int16 SNR, int16 noise per point
        result = []
        for i in range(0, len(payload) - 3, 4):
            snr, noise = struct.unpack_from('<hh', payload, i)
            result.append((float(snr), float(noise)))
        return result
