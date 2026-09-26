from __future__ import annotations

import argparse
import http.server
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = REPO_ROOT / "docs" / "dashboard" / "motion_camera_dashboard_mockup.html"


class PixyMonCaptureError(RuntimeError):
    """Raised when the PixyMon preview window cannot be captured."""


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


class PixyDashboardHandler(http.server.SimpleHTTPRequestHandler):
    app_name = "PixyMon"

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
        if path == "/pixy-status.json":
            self._send_json({"ok": True, "source": self.app_name})
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
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_pixy_frame(self) -> None:
        try:
            body = capture_pixymon_frame(self.app_name)
        except PixyMonCaptureError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=503)
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(host: str, port: int, app_name: str) -> None:
    PixyDashboardHandler.app_name = app_name
    server = http.server.ThreadingHTTPServer((host, port), PixyDashboardHandler)
    print(f"Serving AEGIS dashboard at http://{host}:{port}/dashboard")
    print(f"Pixy source: visible {app_name} window via /pixy-frame.jpg")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the AEGIS dashboard with the PixyMon camera feed.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--app-name", default="PixyMon", help="macOS process/window name for PixyMon.")
    args = parser.parse_args()
    serve(args.host, args.port, args.app_name)


if __name__ == "__main__":
    main()
