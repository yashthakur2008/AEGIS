from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DryRunSerialPort:
    """In-memory Arduino line-protocol simulator for motion-only validation.

    Supports the firmware command shape used by AEGIS: HOME, MOVE, STOP,
    STATUS, and PLASMA. PLASMA is refused unless explicitly enabled so tests and
    demos stay motion-only by default.
    """

    allow_plasma: bool = False
    x_mm: float = 0.0
    y_mm: float = 0.0
    z_mm: float = 4.0
    homed: bool = False
    stopped: bool = False
    history: list[str] = field(default_factory=list)
    _pending_response: bytes = b""

    def write(self, data: bytes) -> int:
        line = data.decode("ascii", errors="replace").strip()
        self.history.append(line)
        self._pending_response = (self._handle_command(line) + "\n").encode("ascii")
        return len(data)

    def readline(self) -> bytes:
        response = self._pending_response
        self._pending_response = b""
        return response

    def _handle_command(self, line: str) -> str:
        parts = line.split()
        command = parts[0].upper() if parts else ""
        if command == "HOME" and len(parts) == 1:
            self.x_mm = 0.0
            self.y_mm = 0.0
            self.z_mm = 4.0
            self.homed = True
            self.stopped = False
            return "OK HOME X=0.000 Y=0.000 Z=4.000"
        if command == "STOP" and len(parts) == 1:
            self.stopped = True
            return "OK STOP"
        if command == "STATUS" and len(parts) == 1:
            return f"OK STATUS X={self.x_mm:.3f} Y={self.y_mm:.3f} Z={self.z_mm:.3f} HOMED={int(self.homed)} STOPPED={int(self.stopped)}"
        if command == "MOVE" and len(parts) == 4:
            if self.stopped:
                return "ERR STOPPED"
            try:
                self.x_mm, self.y_mm, self.z_mm = (float(parts[1]), float(parts[2]), float(parts[3]))
            except ValueError:
                return "ERR BAD_MOVE"
            return f"OK MOVE X={self.x_mm:.3f} Y={self.y_mm:.3f} Z={self.z_mm:.3f}"
        if command == "PLASMA":
            if not self.allow_plasma:
                return "ERR PLASMA_DISABLED"
            return "OK PLASMA"
        return "ERR UNKNOWN_COMMAND"
