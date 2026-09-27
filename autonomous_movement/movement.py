from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .calibration import XYCalibration


@dataclass(frozen=True)
class Detection:
    centroid_x_px: float
    centroid_y_px: float
    area_px2: float = 0.0
    confidence: float = 1.0


def load_detections(path: Path) -> list[Detection]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            Detection(
                centroid_x_px=float(row["centroid_x_px"]),
                centroid_y_px=float(row["centroid_y_px"]),
                area_px2=float(row.get("area_px2") or 0.0),
                confidence=float(row.get("confidence") or 1.0),
            )
            for row in reader
        ]


def detection_to_move_command(detection: Detection, calibration: XYCalibration, *, z_mm: float = 0.0) -> str:
    x_mm, y_mm = calibration.image_to_machine(detection.centroid_x_px, detection.centroid_y_px)
    return f"MOVE {x_mm:.3f} {y_mm:.3f} {z_mm:.3f}"


def plan_move_commands(detections: list[Detection], calibration: XYCalibration, *, z_mm: float = 0.0) -> list[str]:
    return [detection_to_move_command(detection, calibration, z_mm=z_mm) for detection in detections]
