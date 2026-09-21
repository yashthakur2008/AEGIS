from __future__ import annotations

import time
from typing import Protocol

from .planner import Waypoint


class SerialPort(Protocol):
    def write(self, data: bytes) -> int: ...
    def readline(self) -> bytes: ...


class AegisSerialClient:
    """Line-protocol client for the Arduino controller.

    The firmware currently supports HOME/MOVE/STOP/STATUS. PLASMA commands are
    optional and are sent only when enabled so motion-only validation remains the
    default safe behavior.
    """

    def __init__(self, port: SerialPort, *, enable_plasma: bool = False, response_timeout_s: float = 2.0):
        self.port = port
        self.enable_plasma = enable_plasma
        self.response_timeout_s = response_timeout_s

    def send_line(self, line: str) -> str:
        self.port.write((line.strip() + "\n").encode("ascii"))
        deadline = time.monotonic() + self.response_timeout_s
        while time.monotonic() < deadline:
            response = self.port.readline().decode("ascii", errors="replace").strip()
            if response:
                return response
        raise TimeoutError(f"No controller response for {line!r}")

    def home(self) -> str:
        return self.send_line("HOME")

    def stop(self) -> str:
        return self.send_line("STOP")

    def status(self) -> str:
        return self.send_line("STATUS")

    def execute_waypoint(self, waypoint: Waypoint) -> list[str]:
        responses = [self.send_line(waypoint.move_command())]
        if self.enable_plasma and waypoint.intensity > 0 and waypoint.dwell_ms > 0:
            responses.append(self.send_line(waypoint.plasma_command()))
        return responses
