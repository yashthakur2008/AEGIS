from __future__ import annotations

from pathlib import Path


def dashboard_html() -> str:
    return (Path(__file__).resolve().parents[1] / "docs" / "dashboard" / "motion_camera_dashboard_mockup.html").read_text(encoding="utf-8")


def test_dashboard_exposes_operator_status_fields():
    html = dashboard_html()

    assert 'id="cameraSourceState"' in html
    assert 'id="detectorLatencyState"' in html
    assert 'id="detectorErrorState"' in html
    assert "function setDetectorStatus" in html
    assert "getVideoTracks" in html
    assert "responseAgeMs" in html


def test_dashboard_prominently_exposes_sample_detector_upload():
    html = dashboard_html()

    assert "Sample wound detector" in html
    assert 'id="sampleDropZone"' in html
    assert "Paste an image, drag/drop it here" in html
    assert 'id="attachImageButton"' in html
    assert "Attach / Analyze Wound Image" in html
    assert 'id="imageUpload"' in html
    assert 'accept="image/*"' in html
    assert 'id="sampleResultsBody"' in html
    assert "attachImageButton.addEventListener('click', () => imageUpload.click())" in html
    assert "imageUpload.addEventListener('change'" in html
    assert "window.addEventListener('paste'" in html
    assert "sampleDropZone.addEventListener('dragover'" in html
    assert "sampleDropZone.addEventListener('drop'" in html
    assert "function renderSampleResults" in html
    assert "wound_count=0, is_wound=false" in html
    assert "detectUploadedImage" in html
    assert "does not require live camera permission" in html


def test_dashboard_exposes_camera_device_selector():
    html = dashboard_html()

    assert 'id="cameraDeviceSelect"' in html
    assert 'id="refreshCameras"' in html
    assert "Refresh Cameras" in html
    assert "navigator.mediaDevices.enumerateDevices" in html
    assert "device.kind === 'videoinput'" in html
    assert "deviceId: { exact: selectedDeviceId }" in html
    assert "refreshCameras.addEventListener('click', refreshCameraDevices)" in html


def test_dashboard_exposes_operator_restart_help_panel():
    html = dashboard_html()

    assert 'id="operatorHelp"' in html
    assert "Operator restart / hard-refresh help" in html
    assert "python -m wound_cv_model.camera_server --host 127.0.0.1 --port 8766 --camera-index 0" in html
    assert "http://127.0.0.1:8766/dashboard" in html
    assert "Cmd+Shift+R" in html
    assert ".logs/wound_cv_dashboard.log" in html
    assert "/cv-status.json" in html
    assert "ok: true" in html


def test_dashboard_exposes_target_center_and_jog_suggestion():
    html = dashboard_html()

    assert 'id="jogSuggestionState"' in html
    assert "Suggested X/Y jog" in html
    assert "function drawTargetCrosshair" in html
    assert "function updateJogSuggestion" in html
    assert "target center, suggestion only" in html
    assert "suggestion only: X" in html
    assert "drawTargetCrosshair()" in html
    assert "updateJogSuggestion(detections[0], scaleX, scaleY)" in html


def test_dashboard_keeps_skin_prone_local_tracker_disabled():
    html = dashboard_html()

    assert "setInterval(detectLocalWoundCandidate, 90)" not in html
    assert "setInterval(queueBrowserFrameInference, 220)" in html
