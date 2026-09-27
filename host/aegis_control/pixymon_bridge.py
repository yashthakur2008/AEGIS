from __future__ import annotations

import argparse
import http.server
import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .pixy2_direct import DirectPixySource, Pixy2DirectError

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = REPO_ROOT / "docs" / "dashboard" / "motion_camera_dashboard_mockup.html"


class PixyFeedError(RuntimeError):
    """Raised when the configured Pixy feed source cannot produce a frame."""


class PixyMonCaptureError(PixyFeedError):
    """Raised when the PixyMon preview window cannot be captured."""


class PixyFrameSource(Protocol):
    name: str
    mode: str

    def capture_frame(self) -> bytes:
        """Return a JPEG frame for the dashboard."""

    def capture_blocks(self) -> list[object]:
        """Return Pixy detection blocks when the source supports direct block access."""


def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def pixymon_window_bounds(app_name: str = "PixyMon") -> tuple[int, int, int, int]:
    """Return the front PixyMon window bounds as x, y, width, height on macOS."""
    script = f'''
    tell application "System Events"
      set targetProcesses to every process whose name contains "{app_name}"
      if (count of targetProcesses) is 0 then error "{app_name} is not running"
      tell item 1 of targetProcesses
        if (count of windows) is 0 then error "{app_name} has no visible window"
        set windowPosition to position of window 1
        set windowSize to size of window 1
        return (item 1 of windowPosition as text) & "," & (item 2 of windowPosition as text) & "," & (item 1 of windowSize as text) & "," & (item 2 of windowSize as text)
      end tell
    end tell
    '''
    try:
        result = _run(["osascript", "-e", script])
        x, y, width, height = [int(float(part.strip())) for part in result.stdout.strip().split(",")]
    except Exception as exc:  # pragma: no cover - platform/tool dependent
        raise PixyMonCaptureError(str(exc)) from exc
    if width <= 0 or height <= 0:
        raise PixyMonCaptureError(f"invalid {app_name} window bounds: {(x, y, width, height)}")
    return x, y, width, height


def capture_pixymon_frame(app_name: str = "PixyMon") -> bytes:
    """Capture the PixyMon preview window and return JPEG bytes."""
    x, y, width, height = pixymon_window_bounds(app_name)
    with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
        try:
            _run(["screencapture", "-x", "-t", "jpg", "-R", f"{x},{y},{width},{height}", image_file.name])
            return Path(image_file.name).read_bytes()
        except Exception as exc:  # pragma: no cover - platform/tool dependent
            raise PixyMonCaptureError(str(exc)) from exc


@dataclass
class PixyMonFrameSource:
    app_name: str = "PixyMon"
    name: str = "PixyMon window capture"
    mode: str = "pixymon-window"

    def capture_frame(self) -> bytes:
        return capture_pixymon_frame(self.app_name)

    def capture_blocks(self) -> list[object]:
        raise PixyFeedError("PixyMon screen-capture mode does not expose numeric Pixy blocks; use --source direct")


@dataclass
class UnavailablePixySource:
    name: str
    mode: str
    error: str

    def capture_frame(self) -> bytes:
        raise PixyFeedError(self.error)

    def capture_blocks(self) -> list[object]:
        raise PixyFeedError(self.error)


def make_source(source: str, app_name: str) -> PixyFrameSource:
    if source == "pixymon":
        return PixyMonFrameSource(app_name=app_name)
    if source == "direct":
        try:
            return DirectPixySource()
        except Pixy2DirectError as exc:
            return UnavailablePixySource(
                name="Direct Pixy2 USB unavailable",
                mode="direct-pixy2-usb-unavailable",
                error=str(exc),
            )
    raise ValueError(f"unknown Pixy source: {source}")


class PixyDashboardHandler(http.server.SimpleHTTPRequestHandler):
    frame_source: PixyFrameSource = PixyMonFrameSource()
    stream_delay_seconds = 0.2

    def log_message(self, format: str, *args: object) -> None:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} {format % args}")

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        path = self.path.split("?", 1)[0]
        if path in {"/", "/dashboard", "/dashboard.html"}:
            self._send_file(DASHBOARD_PATH, "text/html; charset=utf-8")
            return
        if path == "/pixy-frame.jpg":
            self._send_pixy_frame()
            return
        if path == "/pixy-stream.mjpg":
            self._send_pixy_stream()
            return
        if path == "/pixy-blocks.json":
            self._send_pixy_blocks()
            return
        if path == "/pixy-status.json":
            payload: dict[str, object] = {"ok": True, "source": self.frame_source.name, "mode": self.frame_source.mode}
            if isinstance(self.frame_source, UnavailablePixySource):
                payload = {**payload, "ok": False, "error": self.frame_source.error}
            self._send_json(payload)
            return
        self.send_error(404, "Not found")

    def _send_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _capture_or_error(self) -> bytes:
        try:
            return self.frame_source.capture_frame()
        except PixyFeedError:
            raise
        except Exception as exc:  # pragma: no cover - defensive platform boundary
            raise PixyFeedError(str(exc)) from exc

    def _send_pixy_frame(self) -> None:
        try:
            body = self._capture_or_error()
        except PixyFeedError as exc:
            self._send_json({"ok": False, "source": self.frame_source.name, "error": str(exc)}, status=503)
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_pixy_blocks(self) -> None:
        try:
            blocks = self.frame_source.capture_blocks()
            payload = {
                "ok": True,
                "source": self.frame_source.name,
                "mode": self.frame_source.mode,
                "blocks": [block.to_dict() if hasattr(block, "to_dict") else block for block in blocks],
            }
        except Exception as exc:
            self._send_json(
                {"ok": False, "source": self.frame_source.name, "mode": self.frame_source.mode, "error": str(exc)},
                status=503,
            )
            return
        self._send_json(payload)

    def _send_pixy_stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=pixyframe")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        while True:
            try:
                body = self._capture_or_error()
                self.wfile.write(b"--pixyframe\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
                self.wfile.write(body)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
                time.sleep(self.stream_delay_seconds)
            except (BrokenPipeError, ConnectionResetError):
                return
            except PixyFeedError as exc:
                print(f"Pixy feed error: {exc}")
                time.sleep(1.0)


def serve(host: str, port: int, source: PixyFrameSource, stream_fps: float) -> None:
    PixyDashboardHandler.frame_source = source
    PixyDashboardHandler.stream_delay_seconds = 1.0 / max(stream_fps, 0.1)
    server = http.server.ThreadingHTTPServer((host, port), PixyDashboardHandler)
    print(f"Serving AEGIS dashboard at http://{host}:{port}/dashboard")
    print(f"Pixy source: {source.name} ({source.mode})")
    print("Dashboard endpoints: /pixy-stream.mjpg, /pixy-frame.jpg, /pixy-status.json")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the AEGIS dashboard with a Pixy feed.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--source", choices=["pixymon", "direct"], default="pixymon")
    parser.add_argument("--app-name", default="PixyMon", help="macOS process/window name when --source pixymon is used.")
    parser.add_argument("--stream-fps", type=float, default=5.0, help="MJPEG dashboard stream refresh rate.")
    args = parser.parse_args()
    serve(args.host, args.port, make_source(args.source, args.app_name), args.stream_fps)


if __name__ == "__main__":
    main()
