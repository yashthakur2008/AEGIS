from __future__ import annotations

from pathlib import Path


def test_dashboard_exposes_operator_status_fields():
    html = (Path(__file__).resolve().parents[1] / "docs" / "dashboard" / "motion_camera_dashboard_mockup.html").read_text(encoding="utf-8")

    assert 'id="cameraSourceState"' in html
    assert 'id="detectorLatencyState"' in html
    assert 'id="detectorErrorState"' in html
    assert "function setDetectorStatus" in html
    assert "getVideoTracks" in html
    assert "responseAgeMs" in html


def test_dashboard_keeps_skin_prone_local_tracker_disabled():
    html = (Path(__file__).resolve().parents[1] / "docs" / "dashboard" / "motion_camera_dashboard_mockup.html").read_text(encoding="utf-8")

    assert "setInterval(detectLocalWoundCandidate, 90)" not in html
    assert "setInterval(queueBrowserFrameInference, 220)" in html
