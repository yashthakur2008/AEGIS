from __future__ import annotations

import numpy as np
import cv2  # type: ignore[import-not-found]

from wound_cv_model import HeuristicWoundDetector, WoundDetection, detections_to_csv_rows, estimate_depth_hint
from wound_cv_model.evaluate import run_evaluation
from wound_cv_model.infer import run_inference
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


def test_heuristic_detector_expands_to_connected_pink_abrasion_extent():
    frame = np.zeros((260, 360, 3), dtype=np.uint8)
    frame[:] = (172, 190, 215)
    cv2.ellipse(frame, (210, 145), (42, 96), -24, 0, 360, (145, 155, 225), -1)
    cv2.ellipse(frame, (205, 182), (30, 44), -24, 0, 360, (82, 70, 205), -1)

    detections = HeuristicWoundDetector(min_area_px=100).detect(frame)

    assert detections
    detection = detections[0]
    assert detection.x_px <= 158
    assert detection.y_px <= 58
    assert detection.width_px >= 90
    assert detection.height_px >= 160


def test_heuristic_detector_keeps_separate_wounds_separate_while_expanding_extent():
    frame = np.zeros((260, 420, 3), dtype=np.uint8)
    frame[:] = (172, 190, 215)
    cv2.ellipse(frame, (130, 130), (42, 62), -8, 0, 360, (145, 155, 225), -1)
    cv2.ellipse(frame, (130, 145), (28, 34), -8, 0, 360, (82, 70, 205), -1)
    cv2.ellipse(frame, (300, 130), (38, 55), 12, 0, 360, (145, 155, 225), -1)
    cv2.ellipse(frame, (300, 145), (24, 30), 12, 0, 360, (82, 70, 205), -1)

    detections = HeuristicWoundDetector(min_area_px=100).detect(frame)

    assert len(detections) == 2
    assert all(detection.width_px < 120 for detection in detections)


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


def test_yolo_detection_expands_core_box_to_connected_abrasion_extent():
    class FakeTensor:
        def __init__(self, values):
            self.values = values

        def __getitem__(self, index):
            return self.values[index]

        def tolist(self):
            return self.values

    class FakeBox:
        xyxy = [FakeTensor([185, 145, 225, 220])]
        conf = [0.67]
        cls = [0]

    class FakeModel:
        def predict(self, frame, conf, iou, max_det, verbose):
            return [type("Result", (), {"names": {0: "wound"}, "boxes": [FakeBox()]})()]

    frame = np.zeros((260, 360, 3), dtype=np.uint8)
    frame[:] = (172, 190, 215)
    cv2.ellipse(frame, (210, 145), (42, 96), -24, 0, 360, (145, 155, 225), -1)
    cv2.ellipse(frame, (205, 182), (30, 44), -24, 0, 360, (82, 70, 205), -1)
    detector = YoloWoundDetector.__new__(YoloWoundDetector)
    detector.confidence = 0.55
    detector.model = FakeModel()

    detections = detector.detect(frame)

    assert len(detections) == 1
    detection = detections[0]
    assert detection.x_px <= 158
    assert detection.y_px <= 58
    assert detection.width_px >= 90
    assert detection.height_px >= 160


def test_run_inference_creates_nested_outputs(tmp_path):
    image_path = tmp_path / "input" / "wound.jpg"
    image_path.parent.mkdir()
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    frame[:] = (65, 80, 90)
    cv2.ellipse(frame, (80, 60), (24, 16), 0, 0, 360, (45, 55, 190), -1)
    cv2.imwrite(str(image_path), frame)

    output_csv = tmp_path / "nested" / "detections" / "wound.csv"
    annotated = tmp_path / "nested" / "images" / "wound_annotated.jpg"

    count = run_inference(image_path, output_csv, annotated)

    assert count >= 1
    assert output_csv.exists()
    assert annotated.exists()
    assert "centroid_x_px" in output_csv.read_text(encoding="utf-8")


def test_run_inference_reports_unreadable_image(tmp_path):
    missing_image = tmp_path / "missing.jpg"

    try:
        run_inference(missing_image, tmp_path / "out.csv", tmp_path / "out.jpg")
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected unreadable image error")

    assert str(missing_image) in message
    assert "Could not read image" in message


def test_run_evaluation_creates_report_and_rejects_empty_input(tmp_path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    frame[:] = (65, 80, 90)
    cv2.ellipse(frame, (80, 60), (24, 16), 0, 0, 360, (45, 55, 190), -1)
    cv2.imwrite(str(image_dir / "wound.png"), frame)

    output_dir = tmp_path / "nested" / "eval"
    result = run_evaluation(image_dir, output_dir)

    assert (output_dir / "report.json").exists()
    assert len(result["records"]) == 1
    assert result["records"][0]["count"] >= 1
    assert (output_dir / "wound_annotated.jpg").exists()

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    try:
        run_evaluation(empty_dir, tmp_path / "unused")
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected empty evaluation input error")

    assert str(empty_dir) in message
    assert "No readable image files" in message
