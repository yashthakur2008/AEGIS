from __future__ import annotations

import numpy as np
import cv2  # type: ignore[import-not-found]

from wound_cv_model import HeuristicWoundDetector, WoundDetection, detections_to_csv_rows, estimate_depth_hint
from wound_cv_model.inference import YoloWoundDetector, draw_detections, encode_jpeg


def test_wound_detection_serializes_planner_fields():
    depth = estimate_depth_hint(area_ratio=0.03, redness_score=0.7)
    detection = WoundDetection(
        label="abrasion",
        confidence=0.82,
        x_px=10,
        y_px=20,
        width_px=30,
        height_px=40,
        area_px2=1200,
        redness_score=0.7,
        depth=depth,
    )

    payload = detection.to_dict()
    rows = detections_to_csv_rows([detection])

    assert payload["centroid_x_px"] == 25
    assert payload["centroid_y_px"] == 40
    assert payload["depth_hint"] in {"surface", "shallow", "moderate", "deep_risk"}
    assert rows == [
        {
            "centroid_x_px": 25,
            "centroid_y_px": 40,
            "area_px2": 1200,
            "confidence": 0.82,
            "label": "abrasion",
            "depth_hint": depth.depth_hint,
            "z_offset_hint_mm": depth.z_offset_hint_mm,
        }
    ]


def test_depth_hint_is_conservative_and_monotonic():
    low = estimate_depth_hint(area_ratio=0.001, redness_score=0.05)
    high = estimate_depth_hint(area_ratio=0.09, redness_score=1.0)

    assert low.depth_hint == "surface"
    assert low.z_offset_hint_mm == 0.0
    assert high.depth_hint == "deep_risk"
    assert high.z_offset_hint_mm < low.z_offset_hint_mm
    assert "Monocular" in low.note


def test_heuristic_detector_finds_red_wound_candidate():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[:] = (65, 80, 90)
    cv2.ellipse(frame, (160, 120), (35, 22), 0, 0, 360, (45, 55, 190), -1)

    detections = HeuristicWoundDetector(min_area_px=100).detect(frame)

    assert detections
    detection = detections[0]
    assert detection.label == "wound_candidate"
    assert 120 <= detection.centroid_x_px <= 200
    assert 90 <= detection.centroid_y_px <= 150
    assert detection.depth is not None


def test_draw_detections_encodes_jpeg():
    frame = np.zeros((80, 100, 3), dtype=np.uint8)
    detection = WoundDetection("wound", 0.9, 10, 12, 20, 18, 360, depth=estimate_depth_hint(0.05, 0.8))

    annotated = draw_detections(frame, [detection])
    jpeg = encode_jpeg(annotated)

    assert annotated.shape == frame.shape
    assert jpeg.startswith(b"\xff\xd8")


def test_yolo_region_filter_rejects_hair_like_false_positive():
    detector = YoloWoundDetector.__new__(YoloWoundDetector)
    detector.confidence = 0.55
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[:] = (35, 35, 35)
    for offset in range(0, 90, 8):
        cv2.line(frame, (70 + offset, 40), (35 + offset, 210), (5, 5, 5), 3)

    assert not detector._looks_like_wound_region(frame, 30, 35, 175, 215, 0.18, 0.7)


def test_yolo_region_filter_keeps_red_wound_like_candidate():
    detector = YoloWoundDetector.__new__(YoloWoundDetector)
    detector.confidence = 0.55
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[:] = (85, 95, 110)
    cv2.ellipse(frame, (160, 120), (38, 24), 0, 0, 360, (55, 65, 195), -1)

    assert detector._looks_like_wound_region(frame, 118, 92, 202, 148, 0.06, 0.72)
