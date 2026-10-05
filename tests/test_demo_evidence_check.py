from __future__ import annotations

import json
import shutil
from pathlib import Path

from tools.demo_evidence_check import check_demo_evidence, format_checks
from tools.sample_wound_smoke import run_smoke


REPO_ROOT = Path(__file__).resolve().parents[1]


def copy_required_demo_files(target: Path) -> None:
    dashboard_src = REPO_ROOT / "docs" / "dashboard" / "motion_camera_dashboard_mockup.html"
    validation_src = REPO_ROOT / "docs" / "validation" / "sample_wound_detector_smoke.md"
    logitech_src = REPO_ROOT / "docs" / "validation" / "logitech_calibration_manifest.md"
    readme_src = REPO_ROOT / "README.md"
    dashboard_dst = target / "docs" / "dashboard" / "motion_camera_dashboard_mockup.html"
    validation_dst = target / "docs" / "validation" / "sample_wound_detector_smoke.md"
    logitech_dst = target / "docs" / "validation" / "logitech_calibration_manifest.md"
    readme_dst = target / "README.md"
    dashboard_dst.parent.mkdir(parents=True)
    validation_dst.parent.mkdir(parents=True)
    shutil.copy2(dashboard_src, dashboard_dst)
    shutil.copy2(validation_src, validation_dst)
    shutil.copy2(logitech_src, logitech_dst)
    shutil.copy2(readme_src, readme_dst)


def test_demo_evidence_check_reports_present_artifacts(tmp_path: Path):
    copy_required_demo_files(tmp_path)
    run_smoke(tmp_path / "sample_outputs", write_images=True)

    checks = check_demo_evidence(tmp_path)
    formatted = format_checks(checks)

    assert all(check.ok for check in checks)
    assert "SUMMARY 12/12 evidence checks present" in formatted
    assert "Dashboard server command documented" in formatted
    assert "Logitech calibration manifest workflow documented" in formatted
    assert "Motion dry-run simulator documented" in formatted


def test_demo_evidence_check_reports_missing_sample_outputs(tmp_path: Path):
    copy_required_demo_files(tmp_path)

    checks = check_demo_evidence(tmp_path)
    by_name = {check.name: check for check in checks}

    assert by_name["Sample replay report passes"].ok is False
    assert by_name["Sample images available"].ok is False
    assert by_name["Sample detector UI present"].ok is True
    assert by_name["Camera selector UI present"].ok is True
    assert by_name["Motion dry-run simulator documented"].ok is True


def test_demo_evidence_json_shape(tmp_path: Path):
    copy_required_demo_files(tmp_path)
    run_smoke(tmp_path / "sample_outputs", write_images=True)

    checks = check_demo_evidence(tmp_path)
    payload = {"ok": all(check.ok for check in checks), "checks": [check.__dict__ for check in checks]}
    encoded = json.dumps(payload)

    assert '"ok": true' in encoded
    assert len(payload["checks"]) == 12
