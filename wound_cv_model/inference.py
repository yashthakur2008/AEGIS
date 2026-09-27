from __future__ import annotations

from pathlib import Path
from typing import Iterable

import cv2  # type: ignore[import-not-found]
import numpy as np

from .depth import estimate_depth_hint
from .detection import WoundDetection


class HeuristicWoundDetector:
    """OpenCV fallback detector for development before YOLO weights exist."""

    def __init__(self, min_area_px: float = 250.0) -> None:
        self.min_area_px = min_area_px

    def detect(self, frame_bgr: np.ndarray) -> list[WoundDetection]:
        if frame_bgr.size == 0:
            return []
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        lower_red_1 = np.array([0, 35, 35])
        upper_red_1 = np.array([18, 255, 255])
        lower_red_2 = np.array([160, 35, 35])
        upper_red_2 = np.array([179, 255, 255])
        mask = cv2.inRange(hsv, lower_red_1, upper_red_1) | cv2.inRange(hsv, lower_red_2, upper_red_2)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        frame_area = float(frame_bgr.shape[0] * frame_bgr.shape[1])
        detections: list[WoundDetection] = []
        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area < self.min_area_px:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            roi_mask = mask[y : y + h, x : x + w]
            redness_score = float(np.count_nonzero(roi_mask)) / max(float(w * h), 1.0)
            confidence = max(0.25, min(0.95, 0.35 + redness_score * 0.5 + min(area / frame_area * 6.0, 0.1)))
            detections.append(
                WoundDetection(
                    label="wound_candidate",
                    confidence=confidence,
                    x_px=float(x),
                    y_px=float(y),
                    width_px=float(w),
                    height_px=float(h),
                    area_px2=area,
                    redness_score=redness_score,
                    depth=estimate_depth_hint(area / frame_area, redness_score),
                )
            )
        return sorted(detections, key=lambda d: d.area_px2, reverse=True)


class YoloWoundDetector:
    def __init__(self, weights: Path, confidence: float = 0.55) -> None:
        try:
            from ultralytics import YOLO  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("Ultralytics is required for YOLO inference: python -m pip install ultralytics") from exc
        self.model = YOLO(str(weights))
        self.confidence = confidence

    def detect(self, frame_bgr: np.ndarray) -> list[WoundDetection]:
        results = self.model.predict(frame_bgr, conf=self.confidence, iou=0.45, max_det=5, verbose=False)
        detections: list[WoundDetection] = []
        frame_area = float(frame_bgr.shape[0] * frame_bgr.shape[1])
        for result in results:
            names = getattr(result, "names", {}) or {}
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
                conf = float(box.conf[0]) if getattr(box, "conf", None) is not None else 1.0
                cls = int(box.cls[0]) if getattr(box, "cls", None) is not None else 0
                width = max(0.0, x2 - x1)
                height = max(0.0, y2 - y1)
                area = width * height
                if not self._looks_like_wound_region(frame_bgr, x1, y1, x2, y2, area / frame_area, conf):
                    continue
                label = str(names.get(cls, "wound"))
                detections.append(
                    WoundDetection(
                        label=label,
                        confidence=conf,
                        x_px=x1,
                        y_px=y1,
                        width_px=width,
                        height_px=height,
                        area_px2=area,
                        redness_score=0.0,
                        depth=estimate_depth_hint(area / frame_area, 0.0),
                    )
                )
        return sorted(detections, key=lambda d: d.confidence, reverse=True)

    def _looks_like_wound_region(self, frame_bgr: np.ndarray, x1: float, y1: float, x2: float, y2: float, area_ratio: float, confidence: float) -> bool:
        height, width = frame_bgr.shape[:2]
        box_w = max(1.0, x2 - x1)
        box_h = max(1.0, y2 - y1)
        aspect = max(box_w / box_h, box_h / box_w)
        touches_edge = x1 <= 2 or y1 <= 2 or x2 >= width - 2 or y2 >= height - 2
        if confidence < self.confidence or area_ratio < 0.0007 or area_ratio > 0.22 or aspect > 5.0:
            return False
        if touches_edge and confidence < 0.8:
            return False

        x1_i, y1_i = max(0, int(x1)), max(0, int(y1))
        x2_i, y2_i = min(width, int(x2)), min(height, int(y2))
        roi = frame_bgr[y1_i:y2_i, x1_i:x2_i]
        if roi.size == 0:
            return False

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        hue = hsv[:, :, 0]
        red_or_pink = ((hue <= 18) | (hue >= 160)) & (saturation >= 35) & (value >= 45)
        red_ratio = float(np.count_nonzero(red_or_pink)) / max(float(roi.shape[0] * roi.shape[1]), 1.0)
        dark_ratio = float(np.count_nonzero(value < 45)) / max(float(roi.shape[0] * roi.shape[1]), 1.0)
        low_sat_ratio = float(np.count_nonzero(saturation < 25)) / max(float(roi.shape[0] * roi.shape[1]), 1.0)

        # Hair and shadows are usually dark or desaturated. The detector can still
        # keep very confident model hits, but weak face/background boxes need a
        # measurable red/pink wound-colored component.
        if (dark_ratio > 0.45 or low_sat_ratio > 0.65) and confidence < 0.82:
            return False
        if red_ratio < 0.015 and confidence < 0.75:
            return False
        return True


def build_detector(weights: Path | None = None):
    return YoloWoundDetector(weights) if weights else HeuristicWoundDetector()


def draw_detections(frame_bgr: np.ndarray, detections: Iterable[WoundDetection]) -> np.ndarray:
    annotated = frame_bgr.copy()
    for detection in detections:
        x1 = int(round(detection.x_px))
        y1 = int(round(detection.y_px))
        x2 = int(round(detection.x_px + detection.width_px))
        y2 = int(round(detection.y_px + detection.height_px))
        color = (0, 215, 255) if not detection.depth or detection.depth.depth_hint != "deep_risk" else (0, 0, 255)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"{detection.label} {detection.confidence:.2f}"
        if detection.depth:
            label += f" z:{detection.depth.depth_hint}"
        cv2.putText(annotated, label, (x1, max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        cv2.drawMarker(annotated, (int(detection.centroid_x_px), int(detection.centroid_y_px)), color, cv2.MARKER_CROSS, 18, 2)
    return annotated


def encode_jpeg(frame_bgr: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".jpg", frame_bgr)
    if not ok:
        raise RuntimeError("OpenCV failed to encode frame as JPEG")
    return buffer.tobytes()
