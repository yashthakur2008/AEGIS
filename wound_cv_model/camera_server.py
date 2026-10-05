from __future__ import annotations

import argparse
import http.server
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2  # type: ignore[import-not-found]
import numpy as np

from .detection import WoundDetection
from .inference import build_detector, draw_detections, encode_jpeg

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS = REPO_ROOT / "runs" / "wound_cv" / "aegis_wound_yolo_seg" / "weights" / "best.pt"
DASHBOARD_PATH = REPO_ROOT / "docs" / "dashboard" / "motion_camera_dashboard_mockup.html"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


@dataclass
class CameraState:
    camera_index: int = 0
    weights: Path | None = None
    detector: Any = field(init=False)
    capture: Any = field(default=None, init=False)
    camera_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    inference_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    last_detections: list[WoundDetection] = field(default_factory=list)
    last_error: str | None = None
    frames_served: int = 0

    def __post_init__(self) -> None:
        self.detector = build_detector(self.weights)

    def open(self) -> None:
        if self.capture is None:
            self.capture = cv2.VideoCapture(self.camera_index)
        if not self.capture.isOpened():
            self.last_error = f"Laptop camera index {self.camera_index} is not available"
            raise RuntimeError(self.last_error)

    def reopen(self) -> None:
        if self.capture is not None:
            self.capture.release()
        self.capture = cv2.VideoCapture(self.camera_index)
        if hasattr(self.capture, "set"):
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.open()

    def read_frame(self):
        self.open()
        ok = False
        frame = None
        for attempt in range(10):
            ok, frame = self.capture.read()
            if ok and frame is not None:
                return frame
            if attempt == 4:
                self.reopen()
            time.sleep(0.08)
        self.last_error = "Laptop camera did not return a frame"
        raise RuntimeError(self.last_error)

    def capture_annotated_jpeg(self) -> bytes:
        with self.camera_lock:
            frame = self.read_frame()
            detections = self.detector.detect(frame)
            self.last_detections = detections
            self.frames_served += 1
            self.last_error = None
            return encode_jpeg(draw_detections(frame, detections))

    def status(self) -> dict[str, object]:
        return {
            "ok": self.last_error is None,
            "mode": "laptop-opencv-cv",
            "source": f"OpenCV camera {self.camera_index}",
            "weights": str(self.weights) if self.weights else None,
            "frames_served": self.frames_served,
            "last_error": self.last_error,
            "warning": "Monocular laptop camera depth is a hint only; do not automate Z from this alone.",
        }

    def detections_json(self) -> dict[str, object]:
        detections = [detection.to_dict() for detection in self.last_detections]
        return {
            "ok": self.last_error is None,
            "mode": "laptop-opencv-cv",
            "is_wound": bool(detections),
            "wound_count": len(detections),
            "detections": detections,
            "count": len(detections),
            "depth_warning": "Relative monocular depth only; do not use for autonomous Z motion without calibration.",
        }

    def detect_uploaded_jpeg(self, body: bytes) -> dict[str, object]:
        with self.inference_lock:
            encoded = cv2.imdecode(np.frombuffer(body, dtype=np.uint8), cv2.IMREAD_COLOR)
            if encoded is None:
                self.last_error = "Uploaded browser frame could not be decoded"
                raise RuntimeError(self.last_error)
            detections = self.detector.detect(encoded)
            detection_payloads = [detection.to_dict() for detection in detections]
            self.last_detections = detections
            self.frames_served += 1
            self.last_error = None
            return {
                "ok": True,
                "mode": "browser-camera-trained-yolo",
                "is_wound": bool(detections),
                "wound_count": len(detections),
                "detections": detection_payloads,
                "count": len(detections),
                "image_width_px": int(encoded.shape[1]),
                "image_height_px": int(encoded.shape[0]),
                "depth_warning": "Relative monocular depth only; do not use for autonomous Z motion without calibration.",
            }


class WoundCvHandler(http.server.SimpleHTTPRequestHandler):
    camera_state: CameraState = CameraState()

    def log_message(self, format: str, *args: object) -> None:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} {format % args}")

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in {"/", "/dashboard", "/dashboard.html"}:
            self._send_file(DASHBOARD_PATH, "text/html; charset=utf-8")
            return
        if path == "/cv-frame.jpg":
            self._send_cv_frame()
            return
        if path == "/cv-detections.json":
            self._send_json(self.camera_state.detections_json())
            return
        if path == "/cv-status.json":
            self._send_json(self.camera_state.status())
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path != "/cv-detect-frame":
            self.send_error(404, "Not found")
            return
        try:
            content_length = self.headers.get("Content-Length", "0")
            try:
                length = int(content_length)
            except ValueError as exc:
                raise RuntimeError("Invalid Content-Length for browser frame upload") from exc
            if length <= 0:
                raise RuntimeError("No browser frame was uploaded")
            if length > MAX_UPLOAD_BYTES:
                self._send_json(
                    {
                        **self.camera_state.status(),
                        "ok": False,
                        "error": f"Uploaded browser frame is too large; limit is {MAX_UPLOAD_BYTES} bytes",
                    },
                    status=413,
                )
                return
            body = self.rfile.read(length)
            self._send_json(self.camera_state.detect_uploaded_jpeg(body))
        except Exception as exc:
            self._send_json({**self.camera_state.status(), "ok": False, "error": str(exc)}, status=503)

    def do_OPTIONS(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path != "/cv-detect-frame":
            self.send_error(404, "Not found")
            return
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def _send_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self._send_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")

    def _send_cv_frame(self) -> None:
        try:
            body = self.camera_state.capture_annotated_jpeg()
        except Exception as exc:
            self._send_json({**self.camera_state.status(), "ok": False, "error": str(exc)}, status=503)
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self._send_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(host: str, port: int, camera_index: int, weights: Path | None) -> None:
    WoundCvHandler.camera_state = CameraState(camera_index=camera_index, weights=weights)
    server = http.server.ThreadingHTTPServer((host, port), WoundCvHandler)
    print(f"Serving AEGIS wound CV dashboard at http://{host}:{port}/dashboard")
    print(f"CV endpoints: /cv-frame.jpg, /cv-detections.json, /cv-status.json")
    print("Depth warning: laptop-camera Z values are hints only until calibrated.")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve AEGIS dashboard with laptop-camera OpenCV wound detection.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--weights", type=Path, help="Optional YOLO weights. Defaults to runs/wound_cv/aegis_wound_yolo_seg/weights/best.pt when present.")
    args = parser.parse_args()
    weights = args.weights or (DEFAULT_WEIGHTS if DEFAULT_WEIGHTS.exists() else None)
    if weights:
        print(f"Using trained wound weights: {weights}")
    else:
        print("Using heuristic wound detector because no trained weights were provided or found.")
    serve(args.host, args.port, args.camera_index, weights)


if __name__ == "__main__":
    main()
