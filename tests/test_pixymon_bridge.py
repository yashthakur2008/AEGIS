import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from host.aegis_control.pixy2_direct import DirectPixySource, Pixy2DirectError
from host.aegis_control.pixymon_bridge import (
    PixyDashboardHandler,
    PixyFeedError,
    PixyMonCaptureError,
    PixyMonFrameSource,
    make_source,
    pixymon_window_bounds,
)


class FakePixySource:
    name = "fake Pixy source"
    mode = "fake-pixy"

    def capture_frame(self):
        return b"\xff\xd8fake-jpeg\xff\xd9"

    def capture_blocks(self):
        return [{"signature": 1, "x": 10, "y": 20}]


def test_pixymon_window_bounds_parses_osascript_output(monkeypatch):
    class Result:
        stdout = "10,20,640,480\n"

    monkeypatch.setattr("host.aegis_control.pixymon_bridge._run", lambda command: Result())

    assert pixymon_window_bounds("PixyMon") == (10, 20, 640, 480)


def test_pixymon_window_bounds_rejects_invalid_size(monkeypatch):
    class Result:
        stdout = "10,20,0,480\n"

    monkeypatch.setattr("host.aegis_control.pixymon_bridge._run", lambda command: Result())

    with pytest.raises(PixyMonCaptureError, match="invalid PixyMon window bounds"):
        pixymon_window_bounds("PixyMon")


def test_make_source_selects_pixymon_source():
    source = make_source("pixymon", "PixyMon")

    assert isinstance(source, PixyMonFrameSource)
    assert source.mode == "pixymon-window"


def test_direct_pixy_source_reports_missing_frame_api():
    class Backend:
        backend_name = "fake"

        def get_blocks(self):
            return []

        def get_frame_jpeg(self):
            raise Pixy2DirectError("raw frame unavailable")

    source = DirectPixySource(backend=Backend())

    with pytest.raises(Pixy2DirectError, match="raw frame unavailable"):
        source.capture_frame()


def test_pixy_dashboard_http_routes_disable_cache_and_allow_cors():
    class TestHandler(PixyDashboardHandler):
        frame_source = FakePixySource()

        def log_message(self, format, *args):  # noqa: A002, N802
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        with urllib.request.urlopen(f"{base_url}/dashboard", timeout=5) as response:
            dashboard = response.read().decode("utf-8")
            assert response.status == 200
            assert "no-store" in response.headers["Cache-Control"]
            assert response.headers["Access-Control-Allow-Origin"] == "*"
            assert "AEGIS" in dashboard

        with urllib.request.urlopen(f"{base_url}/pixy-frame.jpg", timeout=5) as response:
            body = response.read()
            assert response.status == 200
            assert response.headers["Content-Type"] == "image/jpeg"
            assert "no-store" in response.headers["Cache-Control"]
            assert response.headers["Access-Control-Allow-Origin"] == "*"
            assert body.startswith(b"\xff\xd8")

        with urllib.request.urlopen(f"{base_url}/pixy-status.json", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert response.headers["Access-Control-Allow-Origin"] == "*"
            assert payload["ok"] is True
            assert payload["mode"] == "fake-pixy"

        with urllib.request.urlopen(f"{base_url}/pixy-blocks.json", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert response.headers["Access-Control-Allow-Origin"] == "*"
            assert payload["blocks"] == [{"signature": 1, "x": 10, "y": 20}]
    finally:
        server.shutdown()
        server.server_close()
