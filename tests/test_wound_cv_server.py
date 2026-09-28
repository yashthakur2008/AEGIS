from __future__ import annotations

import numpy as np

from wound_cv_model.camera_server import CameraState
from wound_cv_model.detection import WoundDetection
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
    assert payload["count"] == 1
    assert payload["detections"][0]["centroid_x_px"] == 15
    assert "annotated_jpeg_base64" not in payload
