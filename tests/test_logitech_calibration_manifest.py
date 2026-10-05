from __future__ import annotations

import argparse
import json
import subprocess
import sys

import pytest

from wound_cv_model.logitech_calibration import LogitechCalibrationManifest, LogitechSample, SAFETY_NOTE, parse_sample


def test_logitech_calibration_manifest_records_required_metadata(tmp_path):
    manifest = LogitechCalibrationManifest(
        camera_label="Logitech C920",
        device_id_hint="browser-device-123",
        width_px=1280,
        height_px=720,
        fps=30.0,
        samples=[
            LogitechSample("close", "close.jpg", 120.0),
            LogitechSample("working", "working.jpg", 180.0),
            LogitechSample("far", "far.jpg", 260.0),
        ],
    )
    output = tmp_path / "manifest.json"

    manifest.write_json(output)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["camera_label"] == "Logitech C920"
    assert payload["device_id_hint"] == "browser-device-123"
    assert payload["resolution"] == {"width_px": 1280, "height_px": 720}
    assert payload["required_buckets"] == ["close", "working", "far"]
    assert [sample["bucket"] for sample in payload["samples"]] == ["close", "working", "far"]
    assert payload["safety_note"] == SAFETY_NOTE
    assert "do not drive autonomous Z" in payload["safety_note"]


def test_logitech_calibration_manifest_requires_all_distance_buckets():
    manifest = LogitechCalibrationManifest(
        camera_label="Logitech C920",
        device_id_hint="",
        width_px=1280,
        height_px=720,
        fps=30.0,
        samples=[LogitechSample("close", "close.jpg"), LogitechSample("far", "far.jpg")],
    )

    with pytest.raises(ValueError, match="missing required sample bucket"):
        manifest.to_dict()


@pytest.mark.parametrize("value", ["near:sample.jpg", "close:", "close:sample.jpg:-1"])
def test_parse_sample_rejects_bad_metadata(value: str):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_sample(value)


def test_logitech_calibration_cli_writes_manifest(tmp_path):
    output = tmp_path / "logitech_manifest.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "wound_cv_model.logitech_calibration",
            "--camera-label",
            "Logitech StreamCam",
            "--device-id-hint",
            "index-1",
            "--width",
            "1920",
            "--height",
            "1080",
            "--fps",
            "30",
            "--sample",
            "close:close.jpg:100",
            "--sample",
            "working:working.jpg:180",
            "--sample",
            "far:far.jpg:260",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "logitech_calibration_manifest=" in result.stdout
    assert payload["camera_label"] == "Logitech StreamCam"
    assert payload["resolution"] == {"width_px": 1920, "height_px": 1080}
    assert [sample["distance_mm"] for sample in payload["samples"]] == [100.0, 180.0, 260.0]
    assert payload["safety_note"] == SAFETY_NOTE
