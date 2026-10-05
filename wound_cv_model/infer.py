from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2  # type: ignore[import-not-found]

from .detection import detections_to_csv_rows
from .inference import build_detector, draw_detections

DETECTION_CSV_FIELDS = ["centroid_x_px", "centroid_y_px", "area_px2", "confidence", "label", "depth_hint", "z_offset_hint_mm"]


def run_inference(image: Path, output_csv: Path, annotated: Path, weights: Path | None = None) -> int:
    frame = cv2.imread(str(image))
    if frame is None:
        raise ValueError(f"Could not read image: {image}")
    detector = build_detector(weights)
    detections = detector.detect(frame)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    annotated.parent.mkdir(parents=True, exist_ok=True)

    rows = detections_to_csv_rows(detections)
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DETECTION_CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    if not cv2.imwrite(str(annotated), draw_detections(frame, detections)):
        raise ValueError(f"Could not write annotated image: {annotated}")
    return len(detections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run wound inference on one image and write planner-compatible detections CSV.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--weights", type=Path, help="Optional trained YOLO weights. If omitted, use OpenCV heuristic fallback.")
    parser.add_argument("--output-csv", type=Path, default=Path("wound_detections.csv"))
    parser.add_argument("--annotated", type=Path, default=Path("wound_annotated.jpg"))
    args = parser.parse_args()

    try:
        count = run_inference(args.image, args.output_csv, args.annotated, weights=args.weights)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"wrote {count} detections to {args.output_csv}")


if __name__ == "__main__":
    main()
