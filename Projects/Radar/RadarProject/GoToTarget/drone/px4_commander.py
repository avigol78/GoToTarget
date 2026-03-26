"""
PX4 drone commander via MAVSDK (UDP SITL).

Phase 1 behaviour:
  - connect() opens the MAVSDK gRPC server over UDP
  - fly_to(target) arms, takes off, then issues a goto_location command
  - send_highest_score(targets) picks the target with the highest score
    and schedules fly_to() in the background asyncio thread

Coordinate conversion: radar → global NED approximation
  The radar gives relative coordinates centred on its own position.
  For SITL testing we offset from a fixed home lat/lon; for real flights
  you must supply the drone's GPS home and a heading.
"""
from __future__ import annotations
import asyncio
import threading
import math
from typing import List, Optional

from radar.data_types import Target

# Home position used for SITL testing (replace with actual GPS fix in production)
SITL_HOME_LAT = 47.397742    # degrees
SITL_HOME_LON =  8.545594    # degrees
SITL_HOME_ALT = 10.0         # metres AGL for goto altitude
EARTH_RADIUS  = 6_371_000.0  # metres


def _radar_to_latlon(
    home_lat: float, home_lon: float, north_m: float, east_m: float
) -> tuple[float, float]:
    """Offset (north_m, east_m) from home position → (lat, lon)."""
    d_lat = math.degrees(north_m / EARTH_RADIUS)
    d_lon = math.degrees(east_m / (EARTH_RADIUS * math.cos(math.radians(home_lat))))
    return home_lat + d_lat, home_lon + d_lon


class PX4Commander:
    def __init__(self, connection_string: str = "udp://:14540") -> None:
        self._connection_string = connection_string
        self._drone = None          # mavsdk.System instance
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._connected = False

    # ------------------------------------------------------------------
    # Public API (called from Qt main thread)
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the asyncio event loop in a background thread."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=3)
        self._connected = False

    def connect_async(self) -> None:
        """Schedule connect coroutine from Qt thread."""
        if self._loop is None:
            self.start()
        asyncio.run_coroutine_threadsafe(self._connect(), self._loop)

    def send_highest_score(self, targets: List[Target]) -> None:
        """Pick the highest-score target and fly to it."""
        if not targets or not self._connected or self._loop is None:
            return
        best = max(targets, key=lambda t: t.score)
        asyncio.run_coroutine_threadsafe(self._fly_to(best), self._loop)

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Async internals (run in background thread's event loop)
    # ------------------------------------------------------------------

    async def _connect(self) -> None:
        try:
            from mavsdk import System  # type: ignore
            self._drone = System()
            await self._drone.connect(system_address=self._connection_string)
            async for state in self._drone.core.connection_state():
                if state.is_connected:
                    self._connected = True
                    break
        except Exception as e:
            print(f"[PX4Commander] connect error: {e}")

    async def _fly_to(self, target: Target) -> None:
        if self._drone is None:
            return
        try:
            # Convert radar-relative coords to absolute lat/lon
            lat, lon = _radar_to_latlon(
                SITL_HOME_LAT, SITL_HOME_LON,
                north_m=target.x,
                east_m=target.y,
            )
            alt = SITL_HOME_ALT - target.z  # z up → AGL altitude

            print(f"[PX4Commander] arming...")
            await self._drone.action.arm()

            print(f"[PX4Commander] taking off...")
            await self._drone.action.takeoff()
            await asyncio.sleep(3)

            print(f"[PX4Commander] flying to ({lat:.6f}, {lon:.6f}, alt={alt:.1f} m)")
            await self._drone.action.goto_location(lat, lon, alt, float('nan'))

        except Exception as e:
            print(f"[PX4Commander] fly_to error: {e}")
