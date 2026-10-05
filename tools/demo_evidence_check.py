#!/usr/bin/env python3
"""Check local evidence artifacts for the AEGIS demo readiness checklist.

This is intentionally conservative: it only marks evidence present when a
file or static dashboard affordance exists locally. Live hardware/browser rows
remain manual evidence and are reported as MISSING until the operator captures
logs, screenshots, or notes.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class EvidenceCheck:
    phase: str
    name: str
    ok: bool
    evidence: str
    detail: str


def _exists(path: Path) -> bool:
    return path.exists()


def _contains(path: Path, text: str) -> bool:
    return path.exists() and text in path.read_text(encoding="utf-8")


def _json_ok(path: Path, predicate: Callable[[dict[str, object]], bool]) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return predicate(payload)


def check_demo_evidence(repo_root: Path) -> list[EvidenceCheck]:
    dashboard = repo_root / "docs" / "dashboard" / "motion_camera_dashboard_mockup.html"
    sample_report = repo_root / "sample_outputs" / "sample_wound_smoke_report.json"
    sample_images = repo_root / "sample_outputs" / "images"
    validation_doc = repo_root / "docs" / "validation" / "sample_wound_detector_smoke.md"

    checks = [
        EvidenceCheck(
            "Phase 0",
            "Dashboard server command documented",
            _contains(dashboard, "python -m wound_cv_model.camera_server"),
            str(dashboard.relative_to(repo_root)),
            "Operator restart panel includes local dashboard server command.",
        ),
        EvidenceCheck(
            "Phase 0",
            "Detector status fields present",
            all(_contains(dashboard, marker) for marker in ["cameraSourceState", "detectorLatencyState", "detectorErrorState"]),
            str(dashboard.relative_to(repo_root)),
            "Dashboard exposes camera source, latency, and last detector error fields.",
        ),
        EvidenceCheck(
            "Phase 1",
            "YOLO-only local tracker guard",
            not _contains(dashboard, "setInterval(detectLocalWoundCandidate, 90)"),
            str(dashboard.relative_to(repo_root)),
            "Skin-prone local color tracker interval is absent.",
        ),
        EvidenceCheck(
            "Phase 1",
            "Relative depth wording present",
            _contains(dashboard, "relative/monocular depth") or _contains(dashboard, "monocular depth"),
            str(dashboard.relative_to(repo_root)),
            "Dashboard warns depth is relative/monocular only.",
        ),
        EvidenceCheck(
            "Phase 2",
            "Sample detector UI present",
            all(_contains(dashboard, marker) for marker in ["sampleDropZone", "Attach / Analyze Wound Image", "sampleResultsBody"]),
            str(dashboard.relative_to(repo_root)),
            "Dashboard has paste/drop/file sample detector panel and result table.",
        ),
        EvidenceCheck(
            "Phase 2",
            "Sample replay report passes",
            _json_ok(sample_report, lambda payload: payload.get("ok") is True and int(payload.get("case_count", 0)) >= 6),
            str(sample_report.relative_to(repo_root)),
            "Smoke report exists, is valid JSON, and records passing sample cases.",
        ),
        EvidenceCheck(
            "Phase 2",
            "Sample images available",
            sample_images.exists() and len(list(sample_images.glob("*.jpg"))) >= 6,
            str(sample_images.relative_to(repo_root)),
            "At least six generated sample images exist for manual paste/drop replay.",
        ),
        EvidenceCheck(
            "Phase 2",
            "HTTP replay instructions documented",
            _contains(validation_doc, "--endpoint-url") and _contains(validation_doc, "/cv-detect-frame"),
            str(validation_doc.relative_to(repo_root)),
            "Validation doc explains server endpoint replay mode.",
        ),
    ]
    return checks


def format_checks(checks: list[EvidenceCheck]) -> str:
    lines: list[str] = []
    for check in checks:
        mark = "PASS" if check.ok else "MISSING"
        lines.append(f"{mark} {check.phase}: {check.name} [{check.evidence}] - {check.detail}")
    passed = sum(1 for check in checks if check.ok)
    lines.append(f"SUMMARY {passed}/{len(checks)} evidence checks present")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local AEGIS demo evidence artifacts for phases 0-2.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of text")
    args = parser.parse_args()

    checks = check_demo_evidence(args.repo_root.resolve())
    if args.json:
        print(json.dumps({"ok": all(check.ok for check in checks), "checks": [asdict(check) for check in checks]}, indent=2))
    else:
        print(format_checks(checks))
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
