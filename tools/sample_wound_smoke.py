#!/usr/bin/env python3
"""Generate and replay repeatable sample wound detector smoke cases.

This is intentionally synthetic. It gives the dashboard workflow a stable
positive/negative/multi-wound sanity check before live camera lighting is debugged.
Real pasted photos should still be captured as demo evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2  # type: ignore[import-not-found]
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from wound_cv_model.inference import HeuristicWoundDetector


@dataclass(frozen=True)
class SmokeCase:
    name: str
    expected_min_count: int
    expected_max_count: int
    builder: Callable[[], np.ndarray]


def blank_skin(width: int = 640, height: int = 420) -> np.ndarray:
    image = np.full((height, width, 3), (185, 190, 172), dtype=np.uint8)
    cv2.rectangle(image, (0, 0), (width, height), (176, 184, 166), -1)
    return image


def printed_wound_positive() -> np.ndarray:
    image = blank_skin()
    cv2.ellipse(image, (320, 210), (82, 45), -8, 0, 360, (92, 92, 214), -1)
    cv2.ellipse(image, (300, 202), (42, 25), -15, 0, 360, (115, 118, 232), -1)
    cv2.circle(image, (355, 225), 20, (80, 70, 185), -1)
    return image


def normal_skin_negative() -> np.ndarray:
    image = blank_skin()
    cv2.circle(image, (210, 160), 7, (132, 138, 125), -1)
    cv2.line(image, (120, 300), (520, 300), (150, 166, 194), 2)
    return image


def background_negative() -> np.ndarray:
    image = np.full((420, 640, 3), (83, 73, 62), dtype=np.uint8)
    cv2.rectangle(image, (60, 70), (580, 350), (111, 100, 88), -1)
    cv2.line(image, (60, 210), (580, 210), (136, 128, 118), 3)
    return image


def far_wound() -> np.ndarray:
    image = blank_skin()
    cv2.ellipse(image, (330, 205), (26, 15), 4, 0, 360, (88, 85, 215), -1)
    return image


def close_wound() -> np.ndarray:
    image = blank_skin()
    cv2.ellipse(image, (320, 210), (145, 88), 0, 0, 360, (80, 76, 220), -1)
    cv2.ellipse(image, (360, 230), (62, 34), -10, 0, 360, (98, 90, 235), -1)
    return image


def multi_wound() -> np.ndarray:
    image = blank_skin()
    cv2.ellipse(image, (225, 180), (58, 34), 12, 0, 360, (84, 82, 216), -1)
    cv2.ellipse(image, (430, 250), (72, 42), -18, 0, 360, (78, 74, 205), -1)
    return image


def elongated_abrasion() -> np.ndarray:
    image = blank_skin()
    cv2.ellipse(image, (340, 205), (54, 126), -26, 0, 360, (145, 154, 224), -1)
    cv2.ellipse(image, (332, 258), (42, 56), -26, 0, 360, (82, 70, 205), -1)
    return image


SMOKE_CASES: tuple[SmokeCase, ...] = (
    SmokeCase("printed_wound_positive", 1, 3, printed_wound_positive),
    SmokeCase("normal_skin_negative", 0, 0, normal_skin_negative),
    SmokeCase("background_negative", 0, 0, background_negative),
    SmokeCase("far_wound", 1, 2, far_wound),
    SmokeCase("close_wound", 1, 2, close_wound),
    SmokeCase("multi_wound", 2, 4, multi_wound),
    SmokeCase("elongated_abrasion", 1, 1, elongated_abrasion),
)


def detect_with_endpoint(image: np.ndarray, endpoint_url: str) -> dict[str, object]:
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("OpenCV failed to encode smoke image")
    request = urllib.request.Request(
        endpoint_url,
        data=encoded.tobytes(),
        method="POST",
        headers={"Content-Type": "image/jpeg"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def run_smoke(output_dir: Path, write_images: bool, endpoint_url: str | None = None) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir = output_dir / "images"
    if write_images:
        image_dir.mkdir(parents=True, exist_ok=True)

    detector = None if endpoint_url else HeuristicWoundDetector(min_area_px=120.0)
    cases: list[dict[str, object]] = []
    failures: list[str] = []

    for case in SMOKE_CASES:
        image = case.builder()
        payload: dict[str, object] | None = None
        if endpoint_url:
            payload = detect_with_endpoint(image, endpoint_url)
            detections = payload.get("detections", [])
        else:
            assert detector is not None
            detections = [detection.to_dict() for detection in detector.detect(image)]
        count = len(detections)
        passed = case.expected_min_count <= count <= case.expected_max_count
        if not passed:
            failures.append(
                f"{case.name}: expected {case.expected_min_count}-{case.expected_max_count} detections, got {count}"
            )
        if write_images:
            cv2.imwrite(str(image_dir / f"{case.name}.jpg"), image)
        cases.append(
            {
                "name": case.name,
                "expected_min_count": case.expected_min_count,
                "expected_max_count": case.expected_max_count,
                "count": count,
                "is_wound": count > 0,
                "passed": passed,
                "server_ok": payload.get("ok") if payload else None,
                "server_is_wound": payload.get("is_wound") if payload else None,
                "server_wound_count": payload.get("wound_count") if payload else None,
                "detections": detections,
            }
        )

    report = {
        "ok": not failures,
        "case_count": len(cases),
        "mode": "http_endpoint" if endpoint_url else "in_process_heuristic",
        "endpoint_url": endpoint_url,
        "failures": failures,
        "cases": cases,
        "depth_warning": "Relative monocular depth hints are smoke-test labels only; do not drive autonomous Z.",
    }
    (output_dir / "sample_wound_smoke_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic sample wound detector smoke cases")
    parser.add_argument("--output-dir", type=Path, default=Path("sample_outputs"), help="Directory for JSON report and optional images")
    parser.add_argument("--write-images", action="store_true", help="Write generated sample JPEGs for manual dashboard upload/paste checks")
    parser.add_argument(
        "--endpoint-url",
        help="Optional running dashboard endpoint, e.g. http://127.0.0.1:8766/cv-detect-frame. When set, smoke images replay through HTTP instead of the in-process heuristic detector.",
    )
    args = parser.parse_args()

    report = run_smoke(args.output_dir, args.write_images, endpoint_url=args.endpoint_url)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
