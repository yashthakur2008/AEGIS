from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a wound YOLO model from a YOLO-format dataset YAML.")
    parser.add_argument("data_yaml", type=Path, help="YOLO data.yaml with train/val paths and wound classes.")
    parser.add_argument("--model", default="yolo11n-seg.pt", help="Base YOLO model, e.g. yolo11n.pt or yolo11n-seg.pt.")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--project", default="runs/wound_cv")
    parser.add_argument("--name", default="wound_yolo")
    args = parser.parse_args()

    if not args.data_yaml.exists():
        raise SystemExit(f"Dataset YAML not found: {args.data_yaml}")
    try:
        from ultralytics import YOLO  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit("Ultralytics is required for training: python -m pip install -r wound_cv_model/requirements.txt") from exc

    model = YOLO(args.model)
    model.train(data=str(args.data_yaml), epochs=args.epochs, imgsz=args.imgsz, project=args.project, name=args.name)


if __name__ == "__main__":
    main()
