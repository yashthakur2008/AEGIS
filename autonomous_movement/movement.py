from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .calibration import XYCalibration

REQUIRED_DETECTION_FIELDS = ("centroid_x_px", "centroid_y_px")


@dataclass(frozen=True)
class Detection:
    centroid_x_px: float
    centroid_y_px: float
    area_px2: float = 0.0
    confidence: float = 1.0


def load_detections(path: Path) -> list[Detection]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_fields = [field for field in REQUIRED_DETECTION_FIELDS if field not in fieldnames]
        if missing_fields:
            raise ValueError(f"{path}: missing required detection CSV column(s): {', '.join(missing_fields)}")

        detections: list[Detection] = []
        for line_number, row in enumerate(reader, start=2):
            try:
                detections.append(
                    Detection(
                        centroid_x_px=float(row["centroid_x_px"]),
                        centroid_y_px=float(row["centroid_y_px"]),
                        area_px2=float(row.get("area_px2") or 0.0),
                        confidence=float(row.get("confidence") or 1.0),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path}: invalid numeric detection value on CSV line {line_number}: "
                    "centroid_x_px, centroid_y_px, area_px2, and confidence must be numbers"
                ) from exc
        return detections


def detection_to_move_command(detection: Detection, calibration: XYCalibration, *, z_mm: float = 0.0) -> str:
    x_mm, y_mm = calibration.image_to_machine(detection.centroid_x_px, detection.centroid_y_px)
    return f"MOVE {x_mm:.3f} {y_mm:.3f} {z_mm:.3f}"


def plan_move_commands(detections: list[Detection], calibration: XYCalibration, *, z_mm: float = 0.0) -> list[str]:
    return [detection_to_move_command(detection, calibration, z_mm=z_mm) for detection in detections]
