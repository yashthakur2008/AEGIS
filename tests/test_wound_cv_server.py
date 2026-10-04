from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np

from wound_cv_model.camera_server import CameraState, WoundCvHandler
from wound_cv_model.detection import DepthEstimate, WoundDetection
from wound_cv_model.inference import encode_jpeg


class FakeCapture:
    def __init__(self, frame):
        self.frame = frame

    def isOpened(self):
        return True

    def read(self):
        return True, self.frame.copy()


class FakeDetector:
    def detect(self, frame):
        return [WoundDetection("wound", 0.8, 5, 6, 20, 10, 200)]


class MultiWoundDetector:
    def detect(self, frame):
        return [
            WoundDetection("wound", 0.91, 5, 6, 20, 10, 200, depth=DepthEstimate("shallow", -0.25, 0.4, "relative only")),
            WoundDetection("wound", 0.74, 40, 30, 18, 16, 288, depth=DepthEstimate("moderate", -0.6, 0.45, "relative only")),
        ]


class EmptyDetector:
    def detect(self, frame):
        return []


def test_camera_state_serves_annotated_frame_and_detection_json():
    state = CameraState(camera_index=99)
    state.capture = FakeCapture(np.zeros((60, 80, 3), dtype=np.uint8))
    state.detector = FakeDetector()

    frame = state.capture_annotated_jpeg()
    payload = state.detections_json()
    status = state.status()

    assert frame.startswith(b"\xff\xd8")
    assert payload["count"] == 1
    assert payload["detections"][0]["centroid_x_px"] == 15
    assert status["mode"] == "laptop-opencv-cv"
    assert "Monocular" in status["warning"]


def test_camera_state_reports_unavailable_camera():
    class ClosedCapture:
        def isOpened(self):
            return False

    state = CameraState(camera_index=123)
    state.capture = ClosedCapture()

    try:
        state.capture_annotated_jpeg()
    except RuntimeError as exc:
        assert "not available" in str(exc)
    else:
        raise AssertionError("expected unavailable camera error")

    assert state.status()["ok"] is False


def test_browser_uploaded_frame_returns_lightweight_detection_payload():
    state = CameraState(camera_index=99)
    state.detector = FakeDetector()
    body = encode_jpeg(np.zeros((60, 80, 3), dtype=np.uint8))

    payload = state.detect_uploaded_jpeg(body)

    assert payload["ok"] is True
    assert payload["is_wound"] is True
    assert payload["wound_count"] == 1
    assert payload["count"] == 1
    assert payload["detections"][0]["centroid_x_px"] == 15
    assert payload["image_width_px"] == 80
    assert payload["image_height_px"] == 60
    assert "Relative monocular depth" in payload["depth_warning"]
    assert "annotated_jpeg_base64" not in payload


def test_uploaded_image_reports_multiple_wounds_and_relative_depth():
    state = CameraState(camera_index=99)
    state.detector = MultiWoundDetector()
    body = encode_jpeg(np.zeros((90, 120, 3), dtype=np.uint8))

    payload = state.detect_uploaded_jpeg(body)

    assert payload["is_wound"] is True
    assert payload["wound_count"] == 2
    assert payload["count"] == 2
    assert [detection["depth_hint"] for detection in payload["detections"]] == ["shallow", "moderate"]
    assert payload["detections"][1]["centroid_x_px"] == 49


def test_uploaded_image_reports_not_wound_when_no_detections():
    state = CameraState(camera_index=99)
    state.detector = EmptyDetector()
    body = encode_jpeg(np.zeros((60, 80, 3), dtype=np.uint8))

    payload = state.detect_uploaded_jpeg(body)

    assert payload["ok"] is True
    assert payload["is_wound"] is False
    assert payload["wound_count"] == 0
    assert payload["detections"] == []


def test_http_upload_endpoint_reports_multiple_wounds_and_no_wound():
    state = CameraState(camera_index=99)
    state.detector = MultiWoundDetector()

    class TestHandler(WoundCvHandler):
        camera_state = state

        def log_message(self, format, *args):  # noqa: A002, N802
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/cv-detect-frame"
    body = encode_jpeg(np.zeros((90, 120, 3), dtype=np.uint8))

    try:
        request = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "image/jpeg"})
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        assert payload["ok"] is True
        assert payload["is_wound"] is True
        assert payload["wound_count"] == 2
        assert [detection["depth_hint"] for detection in payload["detections"]] == ["shallow", "moderate"]

        state.detector = EmptyDetector()
        request = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "image/jpeg"})
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        assert payload["ok"] is True
        assert payload["is_wound"] is False
        assert payload["wound_count"] == 0
        assert payload["detections"] == []
    finally:
        server.shutdown()
        server.server_close()


def test_dashboard_html_responses_disable_browser_cache():
    source = (Path(__file__).resolve().parents[1] / "wound_cv_model" / "camera_server.py").read_text(encoding="utf-8")

    assert 'send_header("Cache-Control", "no-store, max-age=0")' in source
