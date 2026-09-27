from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2  # type: ignore[import-not-found]

from .detection import detections_to_csv_rows
from .inference import build_detector, draw_detections


def main() -> None:
    parser = argparse.ArgumentParser(description="Run wound inference on one image and write planner-compatible detections CSV.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--weights", type=Path, help="Optional trained YOLO weights. If omitted, use OpenCV heuristic fallback.")
    parser.add_argument("--output-csv", type=Path, default=Path("wound_detections.csv"))
    parser.add_argument("--annotated", type=Path, default=Path("wound_annotated.jpg"))
    args = parser.parse_args()

    frame = cv2.imread(str(args.image))
    if frame is None:
        raise SystemExit(f"Could not read image: {args.image}")
    detector = build_detector(args.weights)
    detections = detector.detect(frame)

    rows = detections_to_csv_rows(detections)
    with args.output_csv.open("w", newline="") as handle:
        fieldnames = ["centroid_x_px", "centroid_y_px", "area_px2", "confidence", "label", "depth_hint", "z_offset_hint_mm"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    cv2.imwrite(str(args.annotated), draw_detections(frame, detections))
    print(f"wrote {len(detections)} detections to {args.output_csv}")


if __name__ == "__main__":
    main()
