from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

REQUIRED_DISTANCE_BUCKETS = ("close", "working", "far")
SAFETY_NOTE = "Logitech depth labels are relative calibration metadata only; do not drive autonomous Z from them."


@dataclass(frozen=True)
class LogitechSample:
    bucket: str
    image: str
    distance_mm: float | None = None

    def validate(self) -> None:
        if self.bucket not in REQUIRED_DISTANCE_BUCKETS:
            raise ValueError(f"Unsupported sample bucket {self.bucket!r}; expected one of {', '.join(REQUIRED_DISTANCE_BUCKETS)}")
        if not self.image:
            raise ValueError("Sample image path/name is required")
        if self.distance_mm is not None and self.distance_mm <= 0:
            raise ValueError("Sample distance_mm must be positive when provided")


@dataclass(frozen=True)
class LogitechCalibrationManifest:
    camera_label: str
    device_id_hint: str
    width_px: int
    height_px: int
    fps: float
    samples: list[LogitechSample]
    safety_note: str = SAFETY_NOTE

    def validate(self) -> None:
        if not self.camera_label:
            raise ValueError("camera_label is required")
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("resolution must be positive")
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if not self.samples:
            raise ValueError("at least one calibration sample is required")
        for sample in self.samples:
            sample.validate()
        present = {sample.bucket for sample in self.samples}
        missing = set(REQUIRED_DISTANCE_BUCKETS) - present
        if missing:
            raise ValueError(f"missing required sample bucket(s): {', '.join(sorted(missing))}")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        payload = asdict(self)
        payload["required_buckets"] = list(REQUIRED_DISTANCE_BUCKETS)
        payload["resolution"] = {"width_px": self.width_px, "height_px": self.height_px}
        return payload

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")


def parse_sample(value: str) -> LogitechSample:
    parts = value.split(":")
    if len(parts) not in {2, 3}:
        raise argparse.ArgumentTypeError("sample must be bucket:image[:distance_mm]")
    bucket, image = parts[0], parts[1]
    distance_mm = None
    if len(parts) == 3 and parts[2]:
        try:
            distance_mm = float(parts[2])
        except ValueError as exc:
            raise argparse.ArgumentTypeError("distance_mm must be numeric") from exc
    sample = LogitechSample(bucket=bucket, image=image, distance_mm=distance_mm)
    try:
        sample.validate()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return sample


def build_manifest(args: argparse.Namespace) -> LogitechCalibrationManifest:
    return LogitechCalibrationManifest(
        camera_label=args.camera_label,
        device_id_hint=args.device_id_hint,
        width_px=args.width,
        height_px=args.height,
        fps=args.fps,
        samples=args.sample,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a Logitech camera calibration metadata manifest for AEGIS relative-depth evidence.")
    parser.add_argument("--camera-label", required=True, help="Browser/OpenCV camera label, e.g. Logitech BRIO")
    parser.add_argument("--device-id-hint", default="", help="Browser deviceId hint or OpenCV camera index note")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--sample", action="append", type=parse_sample, required=True, help="Calibration sample as bucket:image[:distance_mm]; buckets: close, working, far")
    parser.add_argument("--output", type=Path, default=Path("docs/validation/logitech_calibration_manifest.json"))
    args = parser.parse_args()

    manifest = build_manifest(args)
    manifest.write_json(args.output)
    print(f"logitech_calibration_manifest={args.output}")
    print(SAFETY_NOTE)


if __name__ == "__main__":
    main()
