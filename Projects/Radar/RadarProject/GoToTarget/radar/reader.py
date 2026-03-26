"""
Background QThread that continuously reads binary data from the radar data port,
finds complete TLV frames, and emits them via Qt signals.
"""
from __future__ import annotations
import serial
from PyQt5.QtCore import QThread, pyqtSignal

from .parser import TLVParser
from .data_types import RadarFrame

READ_CHUNK = 4096  # bytes per serial read call


class RadarReader(QThread):
    frame_received = pyqtSignal(RadarFrame)
    error_occurred = pyqtSignal(str)

    def __init__(self, ser: serial.Serial) -> None:
        super().__init__()
        self._ser = ser
        self._parser = TLVParser()
        self._running = False

    def run(self) -> None:
        self._running = True
        buf = bytearray()

        while self._running:
            try:
                chunk = self._ser.read(READ_CHUNK)
            except serial.SerialException as e:
                self.error_occurred.emit(str(e))
                break

            if not chunk:
                continue

            buf.extend(chunk)

            # Try to extract as many complete frames as possible from buf
            while True:
                frame, consumed = self._parser.find_and_parse(buf)
                if consumed > 0:
                    del buf[:consumed]
                if frame is not None:
                    self.frame_received.emit(frame)
                else:
                    break  # need more data

    def stop(self) -> None:
        self._running = False
        self.wait(2000)  # wait up to 2 s for thread to finish
