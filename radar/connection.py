"""
Serial connection manager for IWR6843ISK.

CLI port  (/dev/ttyUSB0): 115200 baud — sends config commands, receives "Done"
Data port (/dev/ttyUSB1): 921600 baud — receives binary TLV frames
"""
from __future__ import annotations
import time
import serial
from typing import Optional


class ConfigError(Exception):
    pass


class RadarConnection:
    CLI_BAUD = 115200
    DATA_BAUD = 921600
    CMD_TIMEOUT = 1.0    # seconds to wait for "Done" per command
    READ_TIMEOUT = 0.1   # serial read timeout

    def __init__(self) -> None:
        self._cli: Optional[serial.Serial] = None
        self._data: Optional[serial.Serial] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self, cli_port: str, data_port: str) -> bool:
        """Open both serial ports. Returns True on success."""
        try:
            self._cli = serial.Serial(
                cli_port, baudrate=self.CLI_BAUD,
                bytesize=8, parity='N', stopbits=1,
                timeout=self.READ_TIMEOUT
            )
            self._data = serial.Serial(
                data_port, baudrate=self.DATA_BAUD,
                bytesize=8, parity='N', stopbits=1,
                timeout=self.READ_TIMEOUT
            )
            return True
        except serial.SerialException as e:
            self.disconnect()
            raise ConnectionError(str(e)) from e

    def disconnect(self) -> None:
        """Close both ports (safe to call even if not connected)."""
        for port in (self._cli, self._data):
            if port and port.is_open:
                try:
                    port.close()
                except Exception:
                    pass
        self._cli = None
        self._data = None

    @property
    def is_connected(self) -> bool:
        return (self._cli is not None and self._cli.is_open and
                self._data is not None and self._data.is_open)

    def get_data_serial(self) -> serial.Serial:
        if self._data is None or not self._data.is_open:
            raise RuntimeError("Data port is not open")
        return self._data

    # ------------------------------------------------------------------
    # Config file sending
    # ------------------------------------------------------------------

    def send_config(self, cfg_path: str) -> bool:
        """
        Send every command in cfg_path to the CLI port line by line.
        Waits for 'Done' response after each line.
        Raises ConfigError if the board rejects a command.
        Returns True when all commands are accepted.
        """
        if self._cli is None or not self._cli.is_open:
            raise RuntimeError("CLI port is not open")

        self._cli.reset_input_buffer()

        with open(cfg_path, 'r') as fh:
            lines = fh.readlines()

        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith('%'):
                continue

            self._cli.write((line + '\n').encode('ascii'))
            self._cli.flush()

            if not self._wait_for_done():
                raise ConfigError(f"Board rejected command: {line!r}")

        return True

    def _wait_for_done(self) -> bool:
        """
        Read response lines from CLI port until 'Done' is seen or timeout.
        Returns True if 'Done' received, False on timeout.
        """
        deadline = time.monotonic() + self.CMD_TIMEOUT
        response = b''
        while time.monotonic() < deadline:
            chunk = self._cli.read(self._cli.in_waiting or 1)
            if chunk:
                response += chunk
                if b'Done' in response or b'done' in response:
                    return True
                if b'Error' in response or b'error' in response:
                    return False
        return False
