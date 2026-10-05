from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2  # type: ignore[import-not-found]

from .inference import build_detector, draw_detections


def image_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    return sorted(p for p in path.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"})


def run_evaluation(input_path: Path, output_dir: Path, weights: Path | None = None) -> dict[str, object]:
    paths = image_paths(input_path)
    if not paths:
        raise ValueError(f"No readable image files found under: {input_path}")

    detector = build_detector(weights)
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for path in paths:
        frame = cv2.imread(str(path))
        if frame is None:
            records.append({"image": str(path), "error": "unreadable"})
            continue
        detections = detector.detect(frame)
        annotated = draw_detections(frame, detections)
        out_path = output_dir / f"{path.stem}_annotated.jpg"
        if not cv2.imwrite(str(out_path), annotated):
            records.append({"image": str(path), "error": f"could not write annotated image: {out_path}"})
            continue
        records.append({"image": str(path), "annotated": str(out_path), "count": len(detections), "detections": [d.to_dict() for d in detections]})

    report = {"images": records}
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return {"report_path": report_path, "records": records}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate wound detector on an image/folder and save annotated outputs + JSON report.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--weights", type=Path, help="Optional YOLO weights. If omitted, use heuristic detector.")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/wound_eval"))
    args = parser.parse_args()
    try:
        result = run_evaluation(args.input, args.output_dir, weights=args.weights)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    records = result["records"]
    report_path = result["report_path"]
    detected = sum(1 for record in records if record.get("count", 0) > 0)
    print(f"evaluated={len(records)} detected_images={detected} report={report_path}")


if __name__ == "__main__":
    main()
